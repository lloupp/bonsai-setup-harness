#!/usr/bin/env bash
# Prepara o Bonsai no Linux x64: baixa o runtime oficial PrismML (Ubuntu x64) e os modelos que faltarem,
# conferindo SHA256. Uso: ./linux/setup-linux.sh [--com-2b]
set -euo pipefail
source "$(dirname "$0")/common.sh"
need curl curl; need sha256sum coreutils; need tar tar
WITH_2B=0; [[ "${1:-}" == "--com-2b" ]] && WITH_2B=1
mkdir -p "$BASE/models" "$BIN_LINUX" "$BASE/logs"
if [[ ! -x "$BIN_LINUX/llama-server" ]]; then
  echo "Baixando runtime $RUNTIME_ASSET ..."
  digest="$RUNTIME_SHA256"
  tmp="$BIN_LINUX/$RUNTIME_ASSET"
  if [[ -f "$tmp" ]] && echo "$digest  $tmp" | sha256sum -c --status -; then echo "Usando $RUNTIME_ASSET ja presente (offline)."
  else curl -fL --retry 3 -o "$tmp" "https://github.com/PrismML-Eng/llama.cpp/releases/download/$RUNTIME_TAG/$RUNTIME_ASSET"; fi
  echo "$digest  $tmp" | sha256sum -c -
  # Pendrives FAT/exFAT nao aceitam symlinks: extrai e substitui cada link pelo arquivo real.
  tar -xzf "$tmp" -C "$BIN_LINUX" 2>/dev/null || true
  for _pass in 1 2 3; do  # links encadeados (libx.so -> libx.so.0 -> libx.so.0.21.0)
    tar -tvzf "$tmp" | awk '$1 ~ /^l/ {print $(NF-2) "|" $NF}' | while IFS='|' read -r link target; do
      dst="$BIN_LINUX/$link"; src="$(dirname "$dst")/$target"
      if [[ ! -e "$dst" && -e "$src" ]]; then cp -L "$src" "$dst"; fi
    done
  done
  # o pacote pode trazer uma subpasta (ex.: build/bin); normaliza para bin-linux/
  srv=$(find "$BIN_LINUX" -name llama-server -type f | head -1)
  if [[ -n "$srv" && "$(dirname "$srv")" != "$BIN_LINUX" ]]; then cp -a "$(dirname "$srv")"/. "$BIN_LINUX"/; fi
  chmod +x "$BIN_LINUX"/llama-* 2>/dev/null || true
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
LD_LIBRARY_PATH="$BIN_LINUX" "$BIN_LINUX/llama-server" --version 2>&1 | tail -2
echo "Pronto. Inicie com: ./linux/iniciar-bonsai.sh"
