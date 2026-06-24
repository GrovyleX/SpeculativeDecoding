# Speculative Decoding — Two-Laptop Setup

Draft model on **Windows** (`192.168.50.2`), verifier on **Fedora** (`192.168.50.1`) over direct Ethernet.

```
Windows (draft)  ──Ethernet──►  Fedora (verifier)
     │                               │
  Wi‑Fi (internet)              Wi‑Fi (internet)
```

## Models (real speculative decoding)

| Role | Model | Machine |
|------|-------|---------|
| Draft | `HuggingFaceTB/SmolLM2-360M-Instruct` (4-bit) | Windows |
| Verifier | `HuggingFaceTB/SmolLM2-1.7B-Instruct` (4-bit) | Fedora |

Same tokenizer family, different sizes — honest draft/target pair (not same-model cheat).

Set `FAST_DEMO=1` only for demo mode (same model on both sides, ~100% acceptance).

---

## Fedora setup (verifier) — do this first

### 1. One-time install

```bash
cd ~/Documents/CODING/AI/SpeculativeDecoding
bash scripts/setup_fedora.sh
```

### 2. Open firewall for Windows

```bash
bash scripts/setup_firewall.sh 192.168.50.2 8010
```

### 3. Start the verifier server

```bash
bash scripts/start_verifier.sh
```

Wait until you see:

```
Verifier model ready.
INFO:     Uvicorn running on http://0.0.0.0:8010
```

### 4. Quick local test

```bash
curl http://127.0.0.1:8010/health
```

Expected: `"model":"HuggingFaceTB/SmolLM2-1.7B-Instruct"`, `"fast_demo":false`

---

## Windows setup (draft client)

Uses **system Python** + local `.venv` (no conda).

### 1. One-time setup

```powershell
cd G:\SpeculativeDecoding_Kavin
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

Pull latest code from GitHub first if you cloned earlier.

### 2. Confirm network

```powershell
Invoke-RestMethod http://192.168.50.1:8010/health
```

### 3. Run speculative decoding

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_draft.ps1
```

Defaults: `FAST_DEMO=0`, `K=2`, `max-new-tokens=64`, draft=`SmolLM2-360M`.

### 4. Baseline comparison

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_baseline.ps1 --max-new-tokens 64
.\.venv\Scripts\python.exe bench\compare.py --verifier http://192.168.50.1:8010 --max-new-tokens 64 --block-size 2
```

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `FAST_DEMO` | `0` | `1` = same model demo; `0` = real SmolLM2 pair |
| `VERIFIER_MODEL` | `SmolLM2-1.7B-Instruct` | Fedora target model |
| `DRAFT_MODEL` | `SmolLM2-360M-Instruct` | Windows draft model |
| `BLOCK_SIZE` | `2` | Draft tokens per block (try 2 or 4) |

Legacy Qwen pair:

```bash
export VERIFIER_MODEL="Qwen/Qwen2.5-1.5B-Instruct"
export DRAFT_MODEL="Qwen/Qwen2.5-0.5B-Instruct"
export FAST_DEMO=0
```

---

## API (session-based + KV cache)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Server status |
| `/session/start` | POST | Start session with `prompt_ids` |
| `/verify` | POST | Verify draft block (`session_id`, `draft_ids`) |
| `/next_token` | POST | Baseline single step |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Windows can't reach `/health` | `bash scripts/setup_firewall.sh 192.168.50.2 8010` |
| Use port **8010** not 8000 | Port 8000 may be another local app |
| Low acceptance | Normal for real SD; try `--block-size 2` |
| CUDA OOM on Windows | Close other apps; 360M draft is ~400MB in 4-bit |
| `fast_demo: true` in health | Set `FAST_DEMO=0` and restart verifier |

---

## Project layout

```
SpeculativeDecoding/
├── shared/           # config + API schemas
├── verifier/         # Fedora: SmolLM2-1.7B server
├── draft/            # Windows: SmolLM2-360M client
├── bench/            # baseline + compare
└── scripts/
```
