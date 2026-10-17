// Proxy de diagnostico: grava cada corpo POST /v1/messages (sem cabecalhos) e repassa ao adaptador 8082.
// Uso: node capture-proxy.mjs <pasta-saida>   (escuta em 127.0.0.1:8084)
import http from 'node:http';
import {writeFileSync, mkdirSync} from 'node:fs';
const out = process.argv[2]; mkdirSync(out, {recursive: true});
let n = 0;
http.createServer(async (req, res) => {
  const chunks = []; for await (const c of req) chunks.push(c);
  const body = Buffer.concat(chunks);
  if (req.method === 'POST' && req.url.startsWith('/v1/messages') && !req.url.includes('count_tokens')) writeFileSync(`${out}/req-${String(++n).padStart(2, '0')}.json`, body);
  const r = await fetch('http://127.0.0.1:8082' + req.url, {method: req.method, headers: {'content-type': 'application/json', 'anthropic-version': req.headers['anthropic-version'] || '2023-06-01'}, body: req.method === 'POST' ? body : undefined});
  res.writeHead(r.status, {'content-type': r.headers.get('content-type') || 'application/json'});
  for await (const c of r.body) res.write(Buffer.from(c));
  res.end();
}).listen(8084, '127.0.0.1', () => console.log('captura em 8084'));
