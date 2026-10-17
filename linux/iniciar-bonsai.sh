#!/usr/bin/env bash
# Inicia o servidor Bonsai (mesmos perfis do iniciar-bonsai.ps1).
# Uso: ./linux/iniciar-bonsai.sh [--perfil otimizado|original] [--modelo 4B|2B] [--contexto N] [--sem-visao] [--porta 8080]
set -euo pipefail
source "$(dirname "$0")/common.sh"
PERFIL=otimizado; MODELO=4B; CTX=""; VISAO=1; PORTA=8080; CACHE_RAM=2048
while [[ $# -gt 0 ]]; do
  case "$1" in
    --perfil) PERFIL=$2; shift 2;; --modelo) MODELO=$2; shift 2;; --contexto) CTX=$2; shift 2;;
    --sem-visao) VISAO=0; shift;; --porta) PORTA=$2; shift 2;; --cache-ram) CACHE_RAM=$2; shift 2;;
    *) echo "Opcao desconhecida: $1" >&2; exit 2;;
  esac
done
[[ -x "$BIN_LINUX/llama-server" ]] || { echo "Execute ./linux/setup-linux.sh antes." >&2; exit 1; }
if health "$PORTA"; then echo "Bonsai ja esta rodando em http://127.0.0.1:$PORTA"; exit 0; fi
model_id="bonsai-2-$(echo "$MODELO" | tr 'A-Z' 'a-z')"
if [[ $PERFIL == original ]]; then CTX=${CTX:-262144}; KV=q4_0; EXTRA=(); else CTX=${CTX:-65536}; KV=f16; EXTRA=(--cache-ram "$CACHE_RAM"); fi
# Threads: 6 (geracao) e 8 (prompt) foram os melhores valores no i5-14500T. Em outra CPU ajuste
# BONSAI_THREADS / BONSAI_THREADS_BATCH (medir com bin-linux/llama-bench).
T=${BONSAI_THREADS:-6}; TB=${BONSAI_THREADS_BATCH:-8}
ARGS=(-m "$BASE/models/Ternary-Bonsai-2-$MODELO-PQ2_0.gguf" --host 127.0.0.1 --port "$PORTA" --alias "$model_id"
  -ngl 0 -c "$CTX" -np 1 -t "$T" -tb "$TB" -b 256 -ub 128 --cache-type-k "$KV" --cache-type-v "$KV" -fa on --jinja
  --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64
  --reasoning-budget 0 "${EXTRA[@]}")
if [[ $VISAO -eq 1 ]]; then ARGS+=(--mmproj "$BASE/models/Ternary-Bonsai-2-$MODELO-mmproj-Q8_0.gguf"); fi
mkdir -p "$BASE/logs"
LD_LIBRARY_PATH="$BIN_LINUX" nohup "$BIN_LINUX/llama-server" "${ARGS[@]}" >"$BASE/logs/server.out.log" 2>"$BASE/logs/server.err.log" &
echo $! > "$BASE/logs/server.pid"
for _ in $(seq 1 180); do
  if health "$PORTA"; then echo "Bonsai 2 $MODELO pronto: http://127.0.0.1:$PORTA (perfil $PERFIL, contexto $CTX, KV $KV)"; exit 0; fi
  kill -0 "$(cat "$BASE/logs/server.pid")" 2>/dev/null || { echo "Falha ao iniciar; veja logs/server.err.log" >&2; exit 1; }
  sleep 1
done
echo "Demorou mais de 3 minutos; veja logs/server.err.log" >&2; exit 1
