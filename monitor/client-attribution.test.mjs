import test from 'node:test';
import assert from 'node:assert/strict';
import {newLaunches, clientSources} from './client-attribution.mjs';

test('never carries task identities across server processes or malformed records', () => {
  const records = [
    '{partial',
    JSON.stringify({serverPid:10,taskId:7,client:'Pi Agent'}),
    JSON.stringify({serverPid:20,taskId:7,client:'Hermes Agent'}),
    JSON.stringify({serverPid:20,taskId:8,client:'Claude Code'}),
  ].join('\n');
  assert.deepEqual([...clientSources(records,20)],[[7,'Hermes Agent'],[8,'Claude Code']]);
  assert.equal(clientSources(records,null).size,0);
});

test('distinguishes multiple launched tasks from repeated progress for one task', () => {
  const first = '01.01.001.001 I slot launch_slot_: id  0 | task 7 | processing task';
  const progress = '01.02.001.001 I slot print_timing: id 0 | task 8 | n_gen = 100';
  assert.deepEqual(newLaunches(first+'\n'+progress+'\n'+first),[7]);
  assert.deepEqual(newLaunches(first+'\n'+first.replace('task 7','task 9')),[7,9]);
  assert.deepEqual(newLaunches(progress),[]);
});
