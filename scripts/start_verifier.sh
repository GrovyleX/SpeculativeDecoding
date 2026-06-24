#!/usr/bin/env bash
# Start the verifier server on Fedora (this machine).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v conda &>/dev/null; then
  echo "conda not found"
  exit 1
fi

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate aisehack

export VERIFIER_MODEL="${VERIFIER_MODEL:-HuggingFaceTB/SmolLM2-1.7B-Instruct}"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8010}"
export FAST_DEMO="${FAST_DEMO:-0}"

echo "Verifier model : $VERIFIER_MODEL"
echo "FAST_DEMO      : $FAST_DEMO (0 = real SmolLM2 SD)"
echo "Listening on   : ${HOST}:${PORT}"
echo "Health check   : http://192.168.50.1:${PORT}/health"
echo ""
echo "Press Ctrl+C to stop."
echo ""

python -m verifier.server
