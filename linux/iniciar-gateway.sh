#!/usr/bin/env bash
# Gateway de identificacao de programas (127.0.0.1:8083) usado por Pi, Hermes e Claude Code.
source "$(dirname "$0")/common.sh"
need node nodejs
if curl -fsS -m 2 http://127.0.0.1:8083/health 2>/dev/null | grep -q bonsai-client-gateway; then echo "Gateway ja ativo."; exit 0; fi
mkdir -p "$BASE/logs"
nohup node "$BASE/monitor/gateway.mjs" >"$BASE/logs/gateway.out.log" 2>"$BASE/logs/gateway.err.log" &
echo $! > "$BASE/logs/gateway.pid"
sleep 1
echo "Gateway em http://127.0.0.1:8083"
