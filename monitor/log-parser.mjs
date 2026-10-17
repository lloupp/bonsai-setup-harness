export function elapsedSeconds(line) {
  const match = line.match(/^(\d+)\.(\d+)\.(\d+)\.(\d+)/);
  return match ? Number(match[1]) * 60 + Number(match[2]) + Number(match[3]) / 1000 + Number(match[4]) / 1e6 : null;
}

export function parseLogs(lines) {
  const tasks = new Map();
  for (const line of lines) {
    const cancelled = line.match(/cancel task, id_task\s*=\s*(\d+)/);
    if (cancelled) {
      const id = Number(cancelled[1]);
      if (!tasks.has(id)) tasks.set(id, {id, partial: true});
      tasks.get(id).cancelled = true;
    }
    const marker = line.match(/\bid\s+(\d+)\s*\|\s*task\s+(\d+)\s*\|/);
    if (!marker) continue;
    const id = Number(marker[2]);
    if (!tasks.has(id)) tasks.set(id, {id, slot: Number(marker[1]), partial: true});
    const task = tasks.get(id);
    const elapsed = elapsedSeconds(line);
    if (line.includes('launch_slot_')) Object.assign(task, {start: elapsed, partial: false});
    let match;
    if ((match = line.match(/prompt eval time\s*=\s*([\d.]+) ms\s*\/\s*(\d+) tokens.*?([\d.]+) tokens per second/))) {
      Object.assign(task, {promptMs: Number(match[1]), promptTokens: Number(match[2]), promptTps: Number(match[3])});
    } else if ((match = line.match(/\|\s*eval time\s*=\s*([\d.]+) ms\s*\/\s*(\d+) tokens.*?([\d.]+) tokens per second/))) {
      Object.assign(task, {generationMs: Number(match[1]), outputTokens: Number(match[2]), generationTps: Number(match[3])});
    }
    if ((match = line.match(/total time\s*=\s*([\d.]+) ms/))) task.totalMs = Number(match[1]);
    if ((match = line.match(/n_gen\s*=\s*(\d+),\s*tg\s*=\s*([\d.]+) t\/s,\s*tg_3s\s*=\s*([\d.]+) t\/s/))) {
      Object.assign(task, {liveOutputTokens: Number(match[1]), liveTps: Number(match[3]), liveLogTime: elapsed});
    }
    if ((match = line.match(/prompt processing, n_tokens\s*=\s*(\d+), progress\s*=\s*([\d.]+), t\s*=\s*([\d.]+) s\s*\/\s*([\d.]+) tokens per second/))) {
      Object.assign(task, {processedTokens: Number(match[1]), progress: Number(match[2]), livePromptTps: Number(match[4])});
    }
    if ((match = line.match(/stop processing: n_tokens\s*=\s*(\d+), truncated\s*=\s*(\d+)/))) {
      Object.assign(task, {end: elapsed, contextTokens: Number(match[1]), truncated: Number(match[2]) > 0, completed: true});
    }
  }
  return [...tasks.values()].sort((a, b) => a.id - b.id);
}
