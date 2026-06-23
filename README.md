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

## Windows setup (draft client)

Uses **system Python 3** + a local `.venv` in this folder (no conda).

### 1. One-time setup

From `G:\SpeculativeDecoding_Kavin`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

This creates `.venv\` here and installs PyTorch (CUDA) + project deps.

### 2. Confirm network to Fedora

Ethernet should be `192.168.50.2`. Fedora verifier must be running.

```powershell
ping 192.168.50.1
Invoke-RestMethod http://192.168.50.1:8000/health
```

### 3. Run speculative decoding

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_draft.ps1
```

Or manually:

```powershell
cd G:\SpeculativeDecoding_Kavin
.\.venv\Scripts\python.exe draft\client.py --verifier http://192.168.50.1:8000
```

### 4. Baseline comparison (optional)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_baseline.ps1
.\.venv\Scripts\python.exe bench\compare.py --verifier http://192.168.50.1:8000
```

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
