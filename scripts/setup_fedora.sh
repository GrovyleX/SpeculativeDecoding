#!/usr/bin/env bash
# One-time setup on Fedora: install Python deps into aisehack conda env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate aisehack

echo "Installing PyTorch with CUDA ..."
pip install torch --index-url https://download.pytorch.org/whl/cu124

echo "Installing project requirements ..."
pip install -r requirements.txt

echo ""
echo "Verifying imports ..."
python - <<'PY'
import torch
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
print("torch", torch.__version__, "cuda:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0))
PY

echo ""
echo "Done. Run: bash scripts/start_verifier.sh"
