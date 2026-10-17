# Funcoes e versoes fixas compartilhadas pelos scripts Linux.
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_TAG="prism-b10777-e3de715"
RUNTIME_ASSET="llama-${RUNTIME_TAG}-bin-ubuntu-x64.tar.gz"
BIN_LINUX="$BASE/bin-linux"
RUNTIME_SHA256="3f97b6fbec0065fede2be92f05df531c1050636fc2613e1ba0d975249df19713"  # digest oficial do release
HF="https://huggingface.co/prism-ml"
# arquivo|repo|sha256 (conferidos com a API do Hugging Face em 17/10/2026)
MODELS=(
  "Ternary-Bonsai-2-4B-PQ2_0.gguf|Ternary-Bonsai-2-4B-gguf|d406b1e912c0d2a4c124ad10bf38a76ae662fdc4d24b176451403dc7b7f30409"
  "Ternary-Bonsai-2-4B-mmproj-Q8_0.gguf|Ternary-Bonsai-2-4B-gguf|db939d5f9b7014137810205e91d05e5f54afd72b0b3af9d33bd7d82f7906a55d"
  "Ternary-Bonsai-2-2B-PQ2_0.gguf|Ternary-Bonsai-2-2B-gguf|d5f01a4ecaf49239653308ee732ad1a0c5f802c0ddb997549fc7b694c8b45928"
  "Ternary-Bonsai-2-2B-mmproj-Q8_0.gguf|Ternary-Bonsai-2-2B-gguf|ac9934e8d7966d0d62442c202ec8fdad99a045dea79366c1a4a246a46f5c0533"
)
health() { curl -fsS -m 2 "http://127.0.0.1:${1:-8080}/health" 2>/dev/null | grep -q '"ok"'; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "Falta o programa '$1'. Instale-o (ex.: sudo apt install $2)." >&2; exit 1; }; }
