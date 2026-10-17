#!/usr/bin/env bash
# Encerra somente o llama-server iniciado por iniciar-bonsai.sh.
source "$(dirname "$0")/common.sh"
f="$BASE/logs/server.pid"
[[ -f $f ]] || { echo "Nenhum PID salvo."; exit 0; }
pid=$(cat "$f")
if [[ -r /proc/$pid/exe && "$(readlink /proc/$pid/exe)" == *llama-server* ]]; then
  kill "$pid" && echo "Bonsai encerrado."
else
  echo "PID $pid nao pertence ao llama-server; nada foi encerrado."
fi
rm -f "$f"
