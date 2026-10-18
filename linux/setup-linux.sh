#!/usr/bin/env bash
# Prepara o Bonsai no Linux x64: baixa o runtime oficial PrismML (Ubuntu x64) e os modelos que faltarem,
# conferindo SHA256. Uso: ./linux/setup-linux.sh [--com-2b]
set -euo pipefail
source "$(dirname "$0")/common.sh"
need curl curl; need sha256sum coreutils; need tar tar
WITH_2B=0
case "${1:-}" in
  "") ;;
  --com-2b) WITH_2B=1 ;;
  *) echo "Uso: ./linux/setup-linux.sh [--com-2b]" >&2; exit 2 ;;
esac
if [[ $# -gt 1 ]]; then echo "Uso: ./linux/setup-linux.sh [--com-2b]" >&2; exit 2; fi
mkdir -p "$BASE/models" "$BIN_LINUX" "$BASE/logs"
if [[ ! -x "$BIN_LINUX/llama-server" ]]; then
  echo "Baixando runtime $RUNTIME_ASSET ..."
  digest="$RUNTIME_SHA256"
  tmp="$BIN_LINUX/$RUNTIME_ASSET"
  if [[ -f "$tmp" ]] && echo "$digest  $tmp" | sha256sum -c --status -; then echo "Usando $RUNTIME_ASSET ja presente (offline)."
  else curl -fL --retry 3 -o "$tmp" "https://github.com/PrismML-Eng/llama.cpp/releases/download/$RUNTIME_TAG/$RUNTIME_ASSET"; fi
  echo "$digest  $tmp" | sha256sum -c -
  # Pendrives FAT/exFAT nao aceitam symlinks: extrai e substitui cada link pelo arquivo real.
  if ! tar -xzf "$tmp" -C "$BIN_LINUX"; then
    echo "Aviso: extracao parcial; tentando reparar links em sistemas sem suporte a symlink." >&2
  fi
  for _pass in 1 2 3; do  # links encadeados (libx.so -> libx.so.0 -> libx.so.0.21.0)
    tar -tvzf "$tmp" | awk '$1 ~ /^l/ {print $(NF-2) "|" $NF}' | while IFS='|' read -r link target; do
      dst="$BIN_LINUX/$link"; src="$(dirname "$dst")/$target"
      if [[ ! -e "$dst" && -e "$src" ]]; then cp -L "$src" "$dst"; fi
    done
  done
  # o pacote pode trazer uma subpasta (ex.: build/bin); normaliza para bin-linux/
  srv=$(find "$BIN_LINUX" -name llama-server -type f | head -1)
  if [[ -z "$srv" ]]; then echo "Falha: llama-server nao foi extraido." >&2; exit 1; fi
  if [[ "$(dirname "$srv")" != "$BIN_LINUX" ]]; then cp -LR "$(dirname "$srv")"/. "$BIN_LINUX"/; fi
  chmod +x "$BIN_LINUX/llama-server"
  [[ -x "$BIN_LINUX/llama-server" ]] || { echo "llama-server nao e executavel neste sistema de arquivos." >&2; exit 1; }
  # o .tar.gz e mantido para reinstalar offline
fi
for entry in "${MODELS[@]}"; do
  IFS='|' read -r file repo sha <<<"$entry"
  if [[ "$file" == *2B* && $WITH_2B -eq 0 ]]; then continue; fi
  dest="$BASE/models/$file"
  if [[ -f "$dest" ]] && echo "$sha  $dest" | sha256sum -c --status -; then echo "OK $file"; continue; fi
  echo "Baixando $file ..."
  curl -fL --retry 3 -C - -o "$dest.part" "$HF/$repo/resolve/main/$file"
  echo "$sha  $dest.part" | sha256sum -c - && mv "$dest.part" "$dest"
done
[[ -x "$BIN_LINUX/llama-server" ]] || { echo "Runtime ausente ou nao executavel." >&2; exit 1; }
LD_LIBRARY_PATH="$BIN_LINUX${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$BIN_LINUX/llama-server" --version 2>&1 | tail -2
echo "Pronto. Inicie com: ./linux/iniciar-bonsai.sh"
