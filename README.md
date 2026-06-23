# Speculative Decoding — Two-Laptop Setup

Draft model on **Windows** (`192.168.50.2`), verifier on **Fedora** (`192.168.50.1`) over direct Ethernet.

```
Windows (draft)  ──Ethernet──►  Fedora (verifier)
     │                               │
  Wi‑Fi (internet)              Wi‑Fi (internet)
```

## Models

| Role | Model | Machine |
|------|-------|---------|
| Draft | `Qwen/Qwen2.5-0.5B-Instruct` (4-bit) | Windows |
| Verifier | `Qwen/Qwen2.5-1.5B-Instruct` (4-bit) | Fedora |

---

## Fedora setup (verifier) — do this first

### 1. One-time install

```bash
cd ~/Documents/CODING/AI/SpeculativeDecoding
bash scripts/setup_fedora.sh
```

This activates the `aisehack` conda env and installs PyTorch (CUDA), transformers, bitsandbytes, FastAPI, etc.

### 2. Open firewall for Windows

```bash
bash scripts/setup_firewall.sh
```

Allows TCP port `8000` from `192.168.50.2` only.

### 3. Start the verifier server

```bash
bash scripts/start_verifier.sh
```

First run downloads ~1GB model weights from Hugging Face. Wait until you see:

```
Verifier model ready.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Quick local test (on Fedora)

In another terminal:

```bash
conda activate aisehack
cd ~/Documents/CODING/AI/SpeculativeDecoding
curl http://127.0.0.1:8000/health
```

Expected: `{"status":"ok","model":"Qwen/Qwen2.5-1.5B-Instruct","device":"cuda"}`

---

## Windows setup (draft client) — detailed steps

Copy the **entire `SpeculativeDecoding` folder** to Windows (USB drive, `scp`, Git clone, or zip). Same project layout as Fedora.

### 1. Install Miniconda / Anaconda (if not installed)

Download from https://docs.anaconda.com/miniconda/ and install. Open **Anaconda Prompt** or PowerShell.

### 2. Create the `aisehack` conda environment

```powershell
conda create -n aisehack python=3.11 -y
conda activate aisehack
```

### 3. Install PyTorch with CUDA

Check your NVIDIA driver supports CUDA 12.x, then:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

If CUDA install fails, try CPU-only (slower draft, but works for demo):

```powershell
pip install torch
```

### 4. Install project dependencies

```powershell
cd C:\path\to\SpeculativeDecoding
pip install -r requirements.txt
```

### 5. Hugging Face login (optional but recommended)

If model download is slow or gated:

```powershell
pip install huggingface_hub
huggingface-cli login
```

Models used are public; login is optional.

### 6. Confirm GPU (optional)

```powershell
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"
```

### 7. Confirm network to Fedora

With Ethernet configured as `192.168.50.2` and Fedora server running:

```powershell
ping 192.168.50.1
curl http://192.168.50.1:8000/health
```

PowerShell `curl` is an alias for `Invoke-WebRequest`. Alternative:

```powershell
Invoke-RestMethod http://192.168.50.1:8000/health
```

### 8. Run speculative decoding

```powershell
conda activate aisehack
cd C:\path\to\SpeculativeDecoding

python draft/client.py `
  --verifier http://192.168.50.1:8000 `
  --prompt "Explain speculative decoding in one short paragraph." `
  --max-new-tokens 128 `
  --block-size 4
```

First run downloads the 0.5B draft model (~400MB). Output includes per-block stats and a summary with acceptance rate and tok/s.

### 9. Run baseline comparison (optional)

From Windows, baseline hits Fedora verifier one token at a time (no draft model loaded):

```powershell
python bench/baseline.py --verifier http://192.168.50.1:8000
```

Or run both back-to-back:

```powershell
python bench/compare.py --verifier http://192.168.50.1:8000
```

> **Note:** `compare.py` loads the draft model for the speculative half. Baseline only needs network + tokenizer.

---

## API reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Server + model status |
| `/verify` | POST | Verify K draft tokens, return accepted count + next token |
| `/next_token` | POST | Single autoregressive step (baseline) |

### POST /verify

```json
{
  "prompt_ids": [151644, 8948, ...],
  "draft_ids": [1234, 5678, 9012, 3456]
}
```

Response:

```json
{
  "accepted": 3,
  "next_token": 7890,
  "verify_ms": 45.2
}
```

---

## Blog metrics to capture

The client prints per block:

```
block=1 K=4 accepted=3 draft_ms=12.0 network_ms=2.1 verify_ms=45.0
```

And a summary:

- **Acceptance rate** — `total_accepted / total_drafted`
- **Throughput** — tok/s
- **Avg draft / network / verify ms** — per block

Compare speculative summary vs `bench/baseline.py` for speedup (may be &lt; 1x on two laptops — document honestly).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Windows can't reach `/health` | Fedora firewall: `bash scripts/setup_firewall.sh` |
| `CUDA out of memory` | Close other GPU apps; keep `--max-new-tokens 64` |
| Windows RAM tight (8GB) | Close other apps before loading draft model |
| Slow first run | Models downloading from Hugging Face — normal |
| Acceptance rate very low | Draft/verifier mismatch — both must be Qwen2.5 same family |
| Connection timeout | Ensure Fedora `start_verifier.sh` is running |

---

## Project layout

```
SpeculativeDecoding/
├── shared/           # config + API schemas
├── verifier/         # Fedora: model + FastAPI server
├── draft/            # Windows: draft model + client loop
├── bench/            # baseline + compare scripts
├── scripts/          # Fedora setup/start helpers
└── requirements.txt
```
