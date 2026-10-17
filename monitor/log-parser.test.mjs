import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseLogs, elapsedSeconds} from './log-parser.mjs';

test('extracts timing and final occupancy with reused cache', () => {
  const tasks = parseLogs([
    '1.00.000.000 I slot launch_slot_: id 0 | task 12 | processing task, is_child = 0',
    '1.01.000.000 I slot print_timing: id 0 | task 12 | prompt eval time = 1000.00 ms / 50 tokens ( 20.00 ms per token, 50.00 tokens per second)',
    '1.03.000.000 I slot print_timing: id 0 | task 12 | eval time = 2000.00 ms / 31 tokens ( 66.67 ms per token, 15.00 tokens per second)',
    '1.03.000.000 I slot print_timing: id 0 | task 12 | total time = 3000.00 ms / 81 tokens',
    '1.03.001.000 I slot release: id 0 | task 12 | stop processing: n_tokens = 1080, truncated = 0'
  ]);
  assert.equal(tasks.length, 1);
  assert.equal(tasks[0].promptTokens, 50);
  assert.equal(tasks[0].outputTokens, 31);
  assert.equal(tasks[0].generationTps, 15);
  assert.equal(tasks[0].contextTokens, 1080); // Occupancy is not just newly processed tokens.
  assert.equal(tasks[0].completed, true);
});
test('keeps live speeds separate from completed request speeds', () => {
  const [task] = parseLogs([
    '0.01.000.000 I slot launch_slot_: id 0 | task 4 | processing task, is_child = 0',
    '0.03.000.000 I slot print_timing: id 0 | task 4 | prompt processing, n_tokens = 256, progress = 0.50, t = 2.00 s / 128.00 tokens per second',
    '0.10.000.000 I slot print_timing: id 0 | task 4 | n_gen = 100, tg = 14.10 t/s, tg_3s = 13.50 t/s'
  ]);
  assert.equal(task.liveTps, 13.5);
  assert.equal(task.livePromptTps, 128);
  assert.equal(task.progress, 0.5);
  assert.equal(task.completed, undefined);
  assert.equal(task.outputTokens, undefined);
});
test('records cancellations and parses elapsed time', () => {
  const [task] = parseLogs(['1.00.000.000 I slot launch_slot_: id 0 | task 7 | processing task, is_child = 0', '1.01.000.000 W srv stop: cancel task, id_task = 7', '1.01.001.000 I slot release: id 0 | task 7 | stop processing: n_tokens = 256, truncated = 0']);
  assert.equal(task.cancelled, true);
  assert.equal(elapsedSeconds('22.45.465.723 I text'), 1365.465723);
});
