import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let finished = false;
const snapshots = [];
const generation = fetch('http://127.0.0.1:8080/v1/chat/completions', {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({model: 'bonsai-2-4b', messages: [{role: 'user', content: 'Escreva uma lista detalhada de dez maneiras de organizar melhor uma semana de trabalho.'}], max_tokens: 250, chat_template_kwargs: {enable_thinking: false}}),
  signal: AbortSignal.timeout(180000)
}).then(async response => { assert.equal(response.status, 200); return response.json(); }).finally(() => { finished = true; });
while (!finished) {
  const response = await fetch('http://127.0.0.1:8090/api/state');
  const state = await response.json();
  if (state.active) {
    assert.equal(state.contextFree + state.contextUsed, state.contextTotal);
    assert.ok(state.responseRemaining == null || state.responseRemaining >= 0);
    snapshots.push({at: state.at, task: state.taskId, decoded: state.decoded, free: state.contextFree, generationTps: state.generationTps});
  }
  await sleep(1000);
}
const result = await generation;
assert.ok(snapshots.some(s => s.decoded > 0), 'No live output counter observed');
assert.ok(snapshots.some(s => s.generationTps > 0), 'No live generation rate observed');
assert.ok(new Set(snapshots.map(s => s.free)).size > 1, 'Context remaining did not update');
const report = {ok: true, liveSamples: snapshots.length, snapshots, actualTimings: result.timings};
await writeFile(new URL('../logs/monitor-validacao.json', import.meta.url), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ok: true, liveSamples: snapshots.length, measuredTps: result.timings?.predicted_per_second}));
