#!/usr/bin/env bash
# Inicia o servidor Bonsai (mesmos perfis do iniciar-bonsai.ps1).
# Uso: ./linux/iniciar-bonsai.sh [--perfil otimizado|original] [--modelo 4B|2B] [--contexto N] [--sem-visao] [--somente-local] [--porta 8080]
set -euo pipefail
source "$(dirname "$0")/common.sh"
PERFIL=otimizado; MODELO=4B; CTX=""; VISAO=1; PORTA=8080; CACHE_RAM=2048; SOMENTE_LOCAL=0
while [[ $# -gt 0 ]]; do
  if [[ "$1" != "--sem-visao" && "$1" != "--somente-local" && $# -lt 2 ]]; then echo "Valor ausente para $1" >&2; exit 2; fi
  case "$1" in
    --perfil) PERFIL=$2; shift 2;; --modelo) MODELO=$2; shift 2;; --contexto) CTX=$2; shift 2;;
    --sem-visao) VISAO=0; shift;; --somente-local) SOMENTE_LOCAL=1; shift;; --porta) PORTA=$2; shift 2;; --cache-ram) CACHE_RAM=$2; shift 2;;
    *) echo "Opcao desconhecida: $1" >&2; exit 2;;
  esac
done
case "$PERFIL" in otimizado|original) ;; *) echo "Perfil invalido: $PERFIL" >&2; exit 2;; esac
case "$MODELO" in 4B|2B) ;; *) echo "Modelo invalido: $MODELO (use 4B ou 2B)" >&2; exit 2;; esac
if [[ ! "$PORTA" =~ ^[0-9]+$ ]] || (( 10#$PORTA < 1 || 10#$PORTA > 65535 )); then
  echo "Porta invalida: $PORTA" >&2; exit 2
fi
if [[ -n "$CTX" ]] && { [[ ! "$CTX" =~ ^[0-9]+$ ]] || (( 10#$CTX < 1 || 10#$CTX > 262144 )); }; then
  echo "Contexto invalido: $CTX" >&2; exit 2
fi
if [[ ! "$CACHE_RAM" =~ ^[0-9]+$ ]] || (( 10#$CACHE_RAM < 1 )); then
  echo "Cache RAM invalido: $CACHE_RAM" >&2; exit 2
fi
BIND_HOST=0.0.0.0
if [[ $SOMENTE_LOCAL -eq 1 ]]; then BIND_HOST=127.0.0.1; fi
[[ -x "$BIN_LINUX/llama-server" ]] || { echo "Execute ./linux/setup-linux.sh antes." >&2; exit 1; }
model_id="bonsai-2-$(echo "$MODELO" | tr 'A-Z' 'a-z')"
if health "$PORTA"; then
  if curl -fsS -m 2 "http://127.0.0.1:$PORTA/v1/models" | grep -Eq "\"id\"[[:space:]]*:[[:space:]]*\"$model_id\""; then
    config_file="$BASE/logs/server-config.json"
    if [[ ! -f "$config_file" ]] || ! grep -Fq "\"listenHost\":\"$BIND_HOST\"" "$config_file"; then
      echo "Bonsai ja ativo, mas modo de rede nao corresponde (ou e desconhecido). Execute ./linux/parar-bonsai.sh e reinicie." >&2
      exit 1
    fi
    echo "Bonsai $MODELO ja esta rodando em http://127.0.0.1:$PORTA (escuta $BIND_HOST)."
    exit 0
  fi
  echo "Porta $PORTA ja esta ocupada por um servidor com outro modelo." >&2
  exit 1
fi
if [[ $PERFIL == original ]]; then CTX=${CTX:-262144}; KV=q4_0; EXTRA=(); else CTX=${CTX:-65536}; KV=f16; EXTRA=(--cache-ram "$CACHE_RAM"); fi
# Threads: 6 (geracao) e 8 (prompt) foram os melhores valores no i5-14500T. Em outra CPU ajuste
# BONSAI_THREADS / BONSAI_THREADS_BATCH (medir com bin-linux/llama-bench).
T=${BONSAI_THREADS:-6}; TB=${BONSAI_THREADS_BATCH:-8}
for value in "$T" "$TB"; do
  if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then echo "Numero de threads invalido: $value" >&2; exit 2; fi
done
model_file="$BASE/models/Ternary-Bonsai-2-$MODELO-PQ2_0.gguf"
[[ -f "$model_file" ]] || { echo "Modelo ausente: $model_file. Execute setup-linux.sh (com --com-2b para 2B)." >&2; exit 1; }
if [[ "$VISAO" -eq 1 ]]; then
  mmproj="$BASE/models/Ternary-Bonsai-2-$MODELO-mmproj-Q8_0.gguf"
  [[ -f "$mmproj" ]] || { echo "Projetor de visao ausente: $mmproj. Use --sem-visao ou execute o setup." >&2; exit 1; }
fi
ARGS=(-m "$model_file" --host "$BIND_HOST" --port "$PORTA" --alias "$model_id"
  -ngl 0 -c "$CTX" -np 1 -t "$T" -tb "$TB" -b 256 -ub 128 --cache-type-k "$KV" --cache-type-v "$KV" -fa on --jinja
  --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64
  --reasoning-budget 0 "${EXTRA[@]}")
if [[ $VISAO -eq 1 ]]; then ARGS+=(--mmproj "$mmproj"); fi
mkdir -p "$BASE/logs"
LD_LIBRARY_PATH="$BIN_LINUX${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" nohup "$BIN_LINUX/llama-server" "${ARGS[@]}" >"$BASE/logs/server.out.log" 2>"$BASE/logs/server.err.log" &
echo $! > "$BASE/logs/server.pid"
printf '{"pid":%s,"model":"%s","listenHost":"%s","backend":"CPU","context":%s,"contextCache":"%s","perfil":"%s"}\n' \
  "$!" "$model_id" "$BIND_HOST" "$CTX" "$KV" "$PERFIL" > "$BASE/logs/server-config.json"
for _ in $(seq 1 180); do
  if health "$PORTA"; then
    echo "Bonsai 2 $MODELO pronto: http://127.0.0.1:$PORTA (perfil $PERFIL, contexto $CTX, KV $KV, escuta $BIND_HOST)"
    if [[ $SOMENTE_LOCAL -eq 0 ]]; then
      echo "AVISO: API sem autenticacao em todas as interfaces IPv4. Restrinja a porta $PORTA a sua LAN no firewall. Nao publique na Internet." >&2
      echo "Em outro PC: http://<IP-DO-SERVIDOR>:$PORTA/v1"
    fi
    exit 0
  fi
  kill -0 "$(cat "$BASE/logs/server.pid")" 2>/dev/null || { echo "Falha ao iniciar; veja logs/server.err.log" >&2; exit 1; }
  sleep 1
done
echo "Demorou mais de 3 minutos; veja logs/server.err.log" >&2; exit 1
