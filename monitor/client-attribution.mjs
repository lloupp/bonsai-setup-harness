export function newLaunches(text) {
  return [...new Set([...text.matchAll(/launch_slot_[^\n]*?\bid\s+\d+\s*\|\s*task\s+(\d+)\s*\|/g)].map(match => Number(match[1])))];
}

export function clientSources(text, serverPid) {
  const sources = new Map();
  if (!Number.isInteger(serverPid) || serverPid <= 0) return sources;
  for (const line of text.split('\n')) {
    try {
      const record = JSON.parse(line);
      if (record.serverPid === serverPid && Number.isInteger(record.taskId) && typeof record.client === 'string') sources.set(record.taskId, record.client);
    } catch {}
  }
  return sources;
}
