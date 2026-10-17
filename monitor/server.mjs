import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {readFile, open, stat} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {parseLogs} from './log-parser.mjs';
import {clientSources} from './client-attribution.mjs';

const exec = promisify(execFile);
const directory = path.dirname(fileURLToPath(import.meta.url));
const workspace = path.dirname(directory);
const port = Number(process.env.BONSAI_MONITOR_PORT || 8090);
const upstream = 'http://127.0.0.1:8080';
const MAX_LOG_BYTES = 3 * 1024 * 1024;
let processInfo = null, previousProcess = null, processError = null, processBusy = false;
let props = null, propsAt = 0, history = [], tokenSamples = [], state = null, collecting = false;
let runtimeConfig = null;

async function get(endpoint) {
  const response = await fetch(upstream + endpoint, {signal: AbortSignal.timeout(1800)});
  if (!response.ok) throw new Error(`${endpoint}: HTTP ${response.status}`);
  return response.json();
}
async function logs() {
  const file = path.join(workspace, 'logs/server.err.log');
  try {
    const info = await stat(file);
    const start = Math.max(0, info.size - MAX_LOG_BYTES);
    const handle = await open(file, 'r');
    let buffer;
    try {
      buffer = Buffer.alloc(info.size - start);
      await handle.read(buffer, 0, buffer.length, start);
    } finally { await handle.close(); }
    const text = buffer.toString('utf8');
    const lines = text.split(/\r?\n/).filter(Boolean);
    if (start > 0) lines.shift();
    return {lines, limited: start > 0, bytes: info.size};
  } catch (error) { return {lines: [], limited: false, bytes: 0, error: error.code || error.message}; }
}
async function sampleProcess() {
  if (processBusy) return;
  processBusy = true;
  try {
    const pid = Number((await readFile(path.join(workspace, 'logs/server.pid'), 'utf8')).trim());
    if (!Number.isSafeInteger(pid) || pid < 1) throw new Error('PID inválido');
    const result = await exec('powershell.exe', ['-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.join(directory, 'sample-process.ps1'), '-ServerPid', String(pid)], {windowsHide: true, timeout: 5000, maxBuffer: 100000});
    const sample = JSON.parse(result.stdout.replace(/^\uFEFF/, '').trim());
    if (sample) {
      const same = previousProcess?.pid === sample.pid && previousProcess?.startedAt === sample.startedAt;
      const wall = same ? (sample.sampledAt - previousProcess.sampledAt) / 1000 : 0;
      sample.cpuPercent = wall > 0 ? Math.max(0, Math.min(100, (sample.cpuSeconds - previousProcess.cpuSeconds) / wall / os.cpus().length * 100)) : null;
      previousProcess = sample;
    } else previousProcess = null;
    processInfo = sample;
    processError = null;
  } catch (error) { processInfo = null; processError = error.message; }
  finally { processBusy = false; }
}
function deltaRate(samples, key) {
  const last = samples.at(-1);
  const first = samples.find(s => last.at - s.at <= 6000);
  if (!first || first === last || last.at - first.at < 700) return null;
  return Math.max(0, (last[key] - first[key]) / ((last.at - first.at) / 1000));
}
async function collect() {
  if (collecting) return;
  collecting = true;
  try {
    const now = Date.now();
    try {
      const config = JSON.parse((await readFile(path.join(workspace, 'logs/server-config.json'), 'utf8')).replace(/^\uFEFF/, ''));
      runtimeConfig = config.pid === processInfo?.pid ? config : null;
    } catch { runtimeConfig = null; }
    const results = await Promise.allSettled([get('/health'), get('/slots'), logs(), (!props || now - propsAt > 15000) ? get('/props') : Promise.resolve(props)]);
    const health = results[0].status === 'fulfilled' ? results[0].value : null;
    const online = health?.status === 'ok';
    const slots = online && results[1].status === 'fulfilled' && Array.isArray(results[1].value) ? results[1].value : [];
    const log = results[2].status === 'fulfilled' ? results[2].value : {lines: [], error: 'Falha ao ler logs'};
    if (results[3].status === 'fulfilled') { props = results[3].value; if (now - propsAt > 15000) propsAt = now; }
    const tasks = parseLogs(log.lines);
    try {
      const text = await readFile(path.join(workspace, 'logs/client-requests.jsonl'), 'utf8');
      const sources = clientSources(text.slice(-3 * 1024 * 1024), processInfo?.pid);
      for (const task of tasks) task.client = sources.get(task.id) || null;
    } catch {}
    const slot = slots.find(s => s.is_processing) || slots[0] || null;
    const active = Boolean(slot?.is_processing);
    const next = slot?.next_token?.[0];
    const task = active ? tasks.find(t => t.id === slot.id_task) : null;
    const decoded = active ? (next?.n_decoded ?? task?.liveOutputTokens ?? 0) : 0;
    const processed = active ? (slot.n_prompt_tokens_processed ?? 0) : 0;
    if (!active || tokenSamples.at(-1)?.task !== slot.id_task) tokenSamples = [];
    if (active) tokenSamples.push({at: now, task: slot.id_task, decoded, processed});
    tokenSamples = tokenSamples.filter(s => now - s.at < 9000);
    const phase = !online ? (health?.status === 'loading model' ? 'Carregando' : 'Offline') : !active ? 'Em espera' : decoded > 0 ? 'Gerando resposta' : 'Lendo entrada';
    const generationTps = active && decoded > 0 ? (deltaRate(tokenSamples, 'decoded') ?? task?.liveTps ?? null) : null;
    const promptTps = active && decoded === 0 ? (task?.livePromptTps ?? deltaRate(tokenSamples, 'processed')) : null;
    const contextTotal = slot?.n_ctx ?? props?.default_generation_settings?.n_ctx ?? null;
    // n_prompt_tokens is the occupied context, including generated tokens on this runtime.
    const contextUsed = slot ? Number(slot.n_prompt_tokens ?? 0) : null;
    const contextFree = contextTotal != null && contextUsed != null ? Math.max(0, contextTotal - contextUsed) : null;
    const completed = tasks.filter(t => t.completed && t.totalMs != null);
    const last = completed.at(-1) || null;
    const totalPrompt = completed.reduce((n, t) => n + (t.promptTokens || 0), 0);
    const totalOutput = completed.reduce((n, t) => n + (t.outputTokens || 0), 0);
    const generationMs = completed.reduce((n, t) => n + (t.generationMs || 0), 0);
    const weightedGeneration = completed.reduce((n, t) => n + (t.generationTps || 0) * (t.generationMs || 0), 0);
    const memory = {total: os.totalmem(), free: os.freemem(), process: processInfo, error: processError, cpuCount: os.cpus().length, cpuName: os.cpus()[0]?.model};
    history.push({at: now, generationTps, promptTps, contextUsed, cpuPercent: processInfo?.cpuPercent ?? null, processBytes: processInfo?.workingSet ?? null});
    history = history.slice(-180);
    const params = slot?.params || props?.default_generation_settings?.params || {};
    state = {
      at: now, online, phase, serverUrl: upstream, monitorPid: process.pid,
      connectionError: !online ? (results[0].reason?.message || health?.status || 'Servidor indisponível') : null,
      model: props ? {alias: props.model_alias, format: props.model_ftype, path: props.model_path, modalities: props.modalities} : null,
      active, taskId: active ? slot.id_task : null, contextTotal, contextUsed, contextFree,
      contextSource: slot ? 'Ocupação do slot informada por /slots; inclui cache e resposta.' : 'Sem dados atuais do slot.',
      decoded, processed, cached: active ? slot.n_prompt_tokens_cache ?? null : null,
      responseRemaining: active && next?.n_remain >= 0 ? next.n_remain : null,
      responseLimit: active && params.n_predict > 0 ? params.n_predict : null,
      promptProgress: active && !decoded ? task?.progress ?? null : null,
      generationTps, promptTps,
      speedSource: 'Diferença dos contadores de /slots em até 6 s; leitura da entrada também usa as medições dos logs.',
      totals: {completed: completed.length, promptTokens: totalPrompt, outputTokens: totalOutput, averageGenerationTps: generationMs > 0 ? weightedGeneration / generationMs : null, partial: log.limited},
      last, requests: tasks.slice(-35).reverse(), slots: slots.map(s => ({id: s.id, active: s.is_processing, context: s.n_ctx, used: s.n_prompt_tokens, task: s.id_task})),
      memory, uptimeSeconds: online && processInfo?.startedAt ? Math.max(0, (now - Date.parse(processInfo.startedAt)) / 1000) : null,
      sampling: {temperature: params.temperature, topP: params.top_p, topK: params.top_k, minP: params.min_p, presencePenalty: params.presence_penalty, repeatPenalty: params.repeat_penalty},
      runtime: runtimeConfig ? {...runtimeConfig, configurationSource: 'Parâmetros registrados pelo iniciador para este PID; amostragem lida da API.'} : {backend: null, contextCache: null, cpuThreads: null, configurationSource: 'Sem registro de inicialização para o PID atual.'},
      logs: log.lines.slice(-450), logBytes: log.bytes, logLimited: log.limited, logError: log.error ?? null, history
    };
  } finally { collecting = false; }
}
const staticFiles = new Map([['/', ['index.html', 'text/html; charset=utf-8']], ['/app.js', ['app.js', 'text/javascript; charset=utf-8']], ['/style.css', ['style.css', 'text/css; charset=utf-8']]]);
const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, `http://127.0.0.1:${port}`);
  const host = request.headers.host?.toLowerCase();
  if (![`127.0.0.1:${port}`, `localhost:${port}`].includes(host)) { response.writeHead(403).end(); return; }
  response.setHeader('X-Content-Type-Options', 'nosniff');
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'self'");
  if (request.method !== 'GET') { response.writeHead(405).end(); return; }
  if (url.pathname === '/api/state') {
    response.setHeader('Content-Type', 'application/json; charset=utf-8');
    response.end(JSON.stringify(state || {at: Date.now(), online: false, phase: 'Conectando', logs: [], history: []})); return;
  }
  if (url.pathname === '/api/logs') {
    response.setHeader('Content-Type', 'text/plain; charset=utf-8');
    response.setHeader('Content-Disposition', 'attachment; filename="bonsai-logs.txt"');
    response.end((await logs()).lines.join('\n')); return;
  }
  const file = staticFiles.get(url.pathname);
  if (!file) { response.writeHead(404).end('Página não encontrada'); return; }
  try { response.setHeader('Content-Type', file[1]); response.end(await readFile(path.join(directory, 'dist', file[0]))); }
  catch { response.writeHead(500).end('Falha ao carregar painel'); }
});
await sampleProcess();
await collect();
setInterval(() => sampleProcess().catch(() => {}), 4000).unref();
setInterval(() => collect().catch(error => { console.error(error.message); }), 1000).unref();
server.listen(port, '127.0.0.1', () => console.log(`Painel Bonsai: http://127.0.0.1:${port}`));
