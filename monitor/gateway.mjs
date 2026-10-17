import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {readFile, stat, open, appendFile} from 'node:fs/promises';
import {once} from 'node:events';
import {newLaunches} from './client-attribution.mjs';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const upstream = 'http://127.0.0.1:8080';
const port = 8083;
const clients = new Map([['pi','Pi Agent'],['claude','Claude Code'],['hermes','Hermes Agent'],['deepseek','DeepSeek'],['outro','Outro aplicativo']]);
const logPath = path.join(root, 'logs/server.err.log');
const recordPath = path.join(root, 'logs/client-requests.jsonl');

async function logPosition() {
  const info = await stat(logPath);
  return {size: info.size, birthtimeMs: info.birthtimeMs};
}
async function launchesSince(position) {
  if (!position) return [];
  const info = await stat(logPath);
  if (info.birthtimeMs !== position.birthtimeMs || info.size < position.size || info.size - position.size > 1024 * 1024) return [];
  const handle = await open(logPath, 'r');
  try {
    const buffer = Buffer.alloc(info.size - position.size);
    await handle.read(buffer, 0, buffer.length, position.size);
    return newLaunches(buffer.toString('utf8'));
  } finally { await handle.close(); }
}
const server = http.createServer(async (request, response) => {
  if (![`localhost:${port}`,`127.0.0.1:${port}`].includes(request.headers.host)) { response.writeHead(403).end(); return; }
  const url = new URL(request.url, `http://127.0.0.1:${port}`);
  if (request.method === 'GET' && url.pathname === '/health') {
    response.writeHead(200, {'Content-Type':'application/json'}).end(JSON.stringify({service:'bonsai-client-gateway',pid:process.pid})); return;
  }
  const match = url.pathname.match(/^\/([a-z]+)(\/v1\/(?:chat\/completions|messages(?:\/count_tokens)?|models(?:\/[^/]+)?))$/);
  if (!match || !clients.has(match[1]) || !['GET','POST'].includes(request.method)) { response.writeHead(404).end(); return; }
  const client = clients.get(match[1]);
  const generation = request.method === 'POST' && ['/v1/messages','/v1/chat/completions'].includes(match[2]);
  const controller = new AbortController();
  response.on('close', () => { if (!response.writableEnded) controller.abort(); });
  let position = null, correlated = false;
  const record = {client, at: Date.now(), route: match[2]};
  async function correlate() {
    if (!generation || correlated) return;
    correlated = true;
    // Match only an unambiguous new server task in this request's interval.
    // Concurrent/direct calls with multiple launches are left unidentified.
    try {
      const launches = await launchesSince(position);
      const serverPid = Number((await readFile(path.join(root,'logs/server.pid'),'utf8')).trim());
      if (launches.length === 1 && serverPid > 0) {
        await appendFile(recordPath, JSON.stringify({...record,taskId:launches[0],serverPid,source:'gateway'})+'\n');
      }
    } catch (error) { console.error(`Origem indisponivel: ${error.message}`); }
  }
  try {
    let body;
    if (request.method === 'POST') {
      const chunks = []; let size = 0;
      for await (const chunk of request) { size += chunk.length; if (size > 32 * 1024 * 1024) { response.writeHead(413).end(); return; } chunks.push(chunk); }
      body = Buffer.concat(chunks);
    }
    if (generation) { try { position = await logPosition(); } catch {} }
    const headers = {'Content-Type':request.headers['content-type'] || 'application/json'};
    if (request.headers['anthropic-version']) headers['anthropic-version'] = request.headers['anthropic-version'];
    const result = await fetch(upstream + match[2] + url.search, {method:request.method,headers,body,signal:controller.signal});
    response.writeHead(result.status, {'Content-Type':result.headers.get('content-type') || 'application/json','Cache-Control':'no-store','X-Bonsai-Client':match[1]});
    let first = true;
    for await (const chunk of result.body) {
      if (first && result.ok) { first = false; await correlate(); }
      if (!response.write(Buffer.from(chunk))) await once(response,'drain',{signal:controller.signal});
    }
    response.end();
  } catch (error) {
    if (response.destroyed) return;
    if (!response.headersSent) response.writeHead(502,{'Content-Type':'application/json'});
    response.end(JSON.stringify({error:{message:`Gateway Bonsai: ${error.message}`}}));
  }
});
server.listen(port,'127.0.0.1',()=>console.log(`Gateway identificado: http://127.0.0.1:${port}`));
