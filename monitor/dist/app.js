const $ = id => document.getElementById(id);
const number = (value, digits = 0) => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('pt-BR', {maximumFractionDigits: digits, minimumFractionDigits: digits});
const gib = value => value == null ? '—' : number(value / 1024 ** 3, 1);
const put = (id, value) => { $(id).textContent = value; };
const width = (id, value) => { $(id).style.width = `${Math.max(0, Math.min(100, value || 0))}%`; };
let current = null, paused = false, selectedSeries = 'generationTps', lastLogSignature = '';

function duration(seconds) {
  if (seconds == null) return '—';
  if (seconds < 60) return `${number(seconds, 1)} s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor(seconds % 3600 / 60)}m`;
}
function renderLogs(force = false) {
  if (!current) return;
  const query = $('log-search').value.toLocaleLowerCase('pt-BR');
  const level = $('log-level').value;
  const lines = (current.logs || []).filter(line => {
    if (query && !line.toLocaleLowerCase('pt-BR').includes(query)) return false;
    if (level === 'warnings' && !/\s[WE]\s/.test(line)) return false;
    if (level === 'timing' && !/print_timing|stop processing|n_ctx_slot/.test(line)) return false;
    return true;
  });
  const signature = lines.join('\n');
  if (!force && signature === lastLogSignature) return;
  lastLogSignature = signature;
  const container = $('logs');
  const oldScroll = container.scrollTop;
  const fragment = document.createDocumentFragment();
  if (!lines.length) {
    const empty = document.createElement('div'); empty.className = 'logs-empty'; empty.textContent = query || level !== 'all' ? 'Nenhum log corresponde ao filtro.' : 'Ainda não há logs disponíveis.'; fragment.append(empty);
  }
  for (const line of lines) {
    const row = document.createElement('div');
    row.className = 'log-line' + (/\sE\s/.test(line) ? ' error' : /\sW\s/.test(line) ? ' warning' : /print_timing/.test(line) ? ' timing' : '');
    const match = line.match(/^(\d+\.\d+\.\d+\.\d+)(.*)$/);
    if (match) { const stamp = document.createElement('span'); stamp.className = 'timestamp'; stamp.textContent = match[1]; row.append(stamp, document.createTextNode(match[2])); }
    else row.textContent = line;
    fragment.append(row);
  }
  container.replaceChildren(fragment);
  if ($('follow').checked) container.scrollTop = container.scrollHeight;
  else container.scrollTop = oldScroll;
  put('log-count', number(lines.length));
}
function renderRequests(data) {
  const tbody = $('requests');
  const rows = document.createDocumentFragment();
  for (const request of data.requests || []) {
    const row = document.createElement('tr');
    const active = data.active && request.id === data.taskId;
    const values = [`#${request.id}`, request.client || 'Não identificado', active ? 'Em andamento' : request.cancelled ? 'Cancelada' : request.completed ? 'Concluída' : 'Sem conclusão', number(request.promptTokens ?? request.processedTokens), number(request.outputTokens ?? request.liveOutputTokens), request.promptTps == null ? '—' : `${number(request.promptTps, 1)} t/s`, (request.generationTps ?? request.liveTps) == null ? '—' : `${number(request.generationTps ?? request.liveTps, 1)} t/s`, request.totalMs == null ? '—' : duration(request.totalMs / 1000)];
    values.forEach((value, index) => {
      const cell = document.createElement('td');
      if (index === 2) { const badge = document.createElement('span'); badge.className = `task-state ${active ? 'pending' : request.completed ? '' : 'dim'}`; badge.textContent = value; cell.append(badge); }
      else cell.textContent = value;
      row.append(cell);
    });
    rows.append(row);
  }
  if (!(data.requests || []).length) { const row = document.createElement('tr'); const cell = document.createElement('td'); cell.colSpan = 8; cell.textContent = 'As requisições aparecerão aqui quando o modelo começar a trabalhar.'; row.append(cell); rows.append(row); }
  tbody.replaceChildren(rows);
  put('task-count', number(data.requests?.length || 0));
}
function drawChart() {
  if (!current) return;
  const canvas = $('speed-chart'), ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect(), ratio = window.devicePixelRatio || 1;
  if (!rect.width || !rect.height) return;
  canvas.width = rect.width * ratio; canvas.height = rect.height * ratio; ctx.scale(ratio, ratio);
  const w = rect.width, h = rect.height, left = 31, right = w - 9, top = 12, bottom = h - 24;
  const samples = current.history || [], valid = samples.filter(p => p[selectedSeries] != null);
  $('chart-empty').hidden = valid.length > 0;
  const max = Math.max(20, Math.ceil(Math.max(0, ...valid.map(p => p[selectedSeries])) * 1.15 / 10) * 10);
  ctx.font = '9px Consolas, monospace'; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) { const y = bottom - i / 4 * (bottom - top); ctx.strokeStyle = '#29332d'; ctx.setLineDash([3, 5]); ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = '#698071'; ctx.textAlign = 'right'; ctx.fillText(number(max * i / 4), left - 8, y + 3); }
  ctx.textAlign = 'center'; ctx.fillStyle = '#698071';
  for (let i = 0; i <= 3; i++) { const x = left + i / 3 * (right - left); ctx.fillText(i === 3 ? 'agora' : `−${3 - i} min`, Math.max(left + 5, Math.min(right - 6, x)), h - 3); }
  const begin = current.at - 180000;
  const points = samples.map(sample => ({x: left + (sample.at - begin) / 180000 * (right - left), y: sample[selectedSeries] == null ? null : bottom - Math.min(sample[selectedSeries], max) / max * (bottom - top)}));
  const segments = []; let segment = [];
  for (const point of points) { if (point.y == null) { if (segment.length) segments.push(segment); segment = []; } else segment.push(point); }
  if (segment.length) segments.push(segment);
  const color = selectedSeries === 'generationTps' ? '#b6ef88' : '#8bbdcc';
  const fill = ctx.createLinearGradient(0, top, 0, bottom); fill.addColorStop(0, selectedSeries === 'generationTps' ? '#b6ef882a' : '#8bbdcc2a'); fill.addColorStop(1, '#b6ef8800');
  for (const group of segments) {
    ctx.beginPath(); ctx.moveTo(group[0].x, bottom); for (const point of group) ctx.lineTo(point.x, point.y); ctx.lineTo(group.at(-1).x, bottom); ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
    ctx.beginPath(); ctx.moveTo(group[0].x, group[0].y); for (const point of group.slice(1)) ctx.lineTo(point.x, point.y); ctx.strokeStyle = color; ctx.lineWidth = 1.8; ctx.stroke();
  }
  const latest = points.at(-1);
  if (latest?.y != null) { ctx.beginPath(); ctx.arc(latest.x, latest.y, 3, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); }
  canvas.setAttribute('aria-label', `${selectedSeries === 'generationTps' ? 'Geração' : 'Leitura de entrada'}: ${valid.length} medições nos últimos três minutos. Última velocidade: ${number(valid.at(-1)?.[selectedSeries], 1)} tokens por segundo.`);
}
function render(data) {
  current = data;
  const online = data.online, last = data.last;
  const status = $('status'); status.replaceChildren(); const dot = document.createElement('span'); dot.className = 'dot'; status.append(dot, document.createTextNode(paused ? 'Visualização pausada' : data.phase)); status.classList.toggle('offline', !online);
  put('updated', `Leitura ${new Date(data.at).toLocaleTimeString('pt-BR')}`);
  $('notice').hidden = online && !data.logError;
  put('notice', !online ? `O modelo não está disponível. ${data.connectionError || ''} O painel continuará tentando conectar.` : `Não foi possível ler os logs: ${data.logError}`);
  put('model', data.model?.alias?.replace(/^bonsai-2-(\d)b$/i, (_, n) => `Bonsai 2 · ${n}B`) || 'Modelo indisponível');
  put('format', data.model?.format || 'Aguardando informações do servidor');
  const modelId = data.model?.alias || 'bonsai-2-4b';
  put('model-id', modelId);
  put('python-example', `from openai import OpenAI\n\nclient = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="local")\nresponse = client.chat.completions.create(\n    model=${JSON.stringify(modelId)},\n    messages=[{"role": "user", "content": "Olá! Responda em português."}],\n    max_tokens=512,\n    extra_body={"chat_template_kwargs": {"enable_thinking": False}},\n)\nprint(response.choices[0].message.content)`);
  put('backend', data.runtime?.backend || '—'); put('context-cap', `${number(data.contextTotal)} tokens`); put('uptime', duration(data.uptimeSeconds));
  put('gen-speed', number(data.active ? data.generationTps : last?.generationTps, 1));
  put('gen-caption', data.active ? data.decoded > 0 ? 'Geração agora · janela de até 6 s' : 'Preparando a entrada' : last ? 'Última requisição concluída' : 'Sem geração concluída');
  put('prompt-speed', number(data.active && !data.decoded ? data.promptTps : last?.promptTps, 1));
  put('prompt-caption', data.active && !data.decoded ? 'Leitura da entrada em andamento' : last ? 'Última leitura concluída' : 'Sem entrada processada');
  put('processed', data.active ? `${number(data.processed)} tokens processados` : last ? `${number(last.promptTokens)} novos tokens lidos` : '— tokens processados');
  put('output-tokens', number(data.active ? data.decoded : last?.outputTokens)); put('output-caption', data.active ? `Na requisição #${data.taskId}` : 'Na última requisição concluída');
  put('output-total', `${number(data.totals?.outputTokens)} acumulados nos logs`);
  const memory = data.memory || {}, process = memory.process;
  put('model-memory', gib(process?.workingSet)); put('system-memory', `RAM disponível: ${gib(memory.free)} GiB`);
  width('ram-bar', memory.total ? (memory.total - memory.free) / memory.total * 100 : 0);
  put('context-free', number(online ? data.contextFree : null)); put('context-used', number(online ? data.contextUsed : null));
  const contextPercent = online && data.contextTotal && data.contextUsed != null ? data.contextUsed / data.contextTotal * 100 : null;
  put('context-percent', contextPercent == null ? '—%' : `${number(contextPercent, 1)}%`); width('context-bar', contextPercent);
  put('slot-label', data.slots?.length ? `SLOT ${data.slots.find(s => s.active)?.id ?? data.slots[0].id}` : 'SEM SLOT');
  put('response-left', data.active ? number(data.responseRemaining) : 'Sem resposta ativa'); put('cache-tokens', data.active ? number(data.cached) : '—');
  put('cpu', process?.cpuPercent == null ? '—' : `${number(process.cpuPercent, 1)}%`); width('cpu-bar', process?.cpuPercent);
  put('cpu-name', `${memory.cpuName || 'CPU indisponível'} · ${number(memory.cpuCount)} threads lógicas`);
  put('ram-system', memory.total ? `${gib(memory.total - memory.free)} / ${gib(memory.total)} GiB` : '—'); put('private-memory', process ? `${gib(process.privateBytes)} GiB` : '—'); put('pid', process?.pid || '—');
  put('request-count', `${number(data.totals?.completed)} concluídas`); put('input-total', number(data.totals?.promptTokens)); put('generated-total', number(data.totals?.outputTokens)); put('average-speed', number(data.totals?.averageGenerationTps, 1));
  const params = data.sampling || {};
  put('sampling', `Temp ${number(params.temperature, 1)}  /  Top-p ${number(params.topP, 2)}  /  Top-k ${number(params.topK)}  /  Presença ${number(params.presencePenalty, 1)}  /  ${data.runtime?.cpuThreads || '—'} threads de geração  /  Cache ${data.runtime?.contextCache || '—'}`);
  put('log-source', `Fonte: server.err.log · ${number((data.logBytes || 0) / 1024, 1)} KiB${data.logLimited ? ' · totais parciais (últimos 3 MiB)' : ''}`);
  put('config-info', process ? 'CPU: fração da capacidade total da máquina. RAM: conjunto residente.' : 'Métricas do processo indisponíveis; contexto e logs continuam sendo lidos.');
  renderLogs(); renderRequests(data); drawChart();
}
async function poll() {
  if (!paused) {
    try {
      const response = await fetch('/api/state', {signal: AbortSignal.timeout(5000), cache: 'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
    } catch (error) { $('notice').hidden = false; put('notice', `Conexão com o painel interrompida. Últimos dados preservados; tentando novamente. ${error.message}`); }
  }
  setTimeout(poll, 1000);
}
$('pause').addEventListener('click', () => { paused = !paused; document.body.classList.toggle('paused', paused); $('pause').setAttribute('aria-pressed', String(paused)); put('pause', paused ? 'Retomar atualização' : 'Pausar atualização'); if (current) render(current); });
for (const input of ['log-search', 'log-level']) $(input).addEventListener('input', () => renderLogs(true));
$('follow').addEventListener('change', () => { if ($('follow').checked) $('logs').scrollTop = $('logs').scrollHeight; });
for (const tab of ['logs', 'requests']) $(`${tab}-tab`).addEventListener('click', () => {
  for (const item of ['logs', 'requests']) { const active = item === tab; $(`${item}-tab`).classList.toggle('active', active); $(`${item}-tab`).setAttribute('aria-selected', String(active)); $(`${item}-view`).hidden = !active; }
  $('log-controls').hidden = tab !== 'logs';
});
for (const button of document.querySelectorAll('[data-series]')) button.addEventListener('click', () => {
  selectedSeries = button.dataset.series;
  for (const item of document.querySelectorAll('[data-series]')) { const active = item === button; item.classList.toggle('selected', active); item.setAttribute('aria-pressed', String(active)); }
  put('chart-legend', selectedSeries === 'generationTps' ? 'Tokens gerados por segundo' : 'Tokens de entrada lidos por segundo'); drawChart();
});
new ResizeObserver(drawChart).observe($('speed-chart'));
let copyTimer;
for (const button of document.querySelectorAll('[data-copy-id]')) button.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText($(button.dataset.copyId).textContent);
    put('copy-feedback', 'Copiado para a área de transferência.');
  } catch {
    put('copy-feedback', 'O navegador não permitiu copiar. Selecione e copie o texto do campo.');
  }
  clearTimeout(copyTimer); copyTimer = setTimeout(() => put('copy-feedback', ''), 3500);
});
poll();
