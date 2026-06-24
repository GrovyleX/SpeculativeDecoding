"""Shared defaults for draft/verifier models and generation."""

import os

# Real speculative decoding: SmolLM2 family (360M draft → 1.7B verifier)
VERIFIER_MODEL = os.getenv("VERIFIER_MODEL", "HuggingFaceTB/SmolLM2-1.7B-Instruct")
DRAFT_MODEL_SMALL = "HuggingFaceTB/SmolLM2-360M-Instruct"

# FAST_DEMO=1: same model draft+verifier (demo only, ~100% acceptance)
# FAST_DEMO=0 (default): honest SmolLM2-360M draft vs SmolLM2-1.7B verifier
FAST_DEMO = os.getenv("FAST_DEMO", "0") == "1"
DRAFT_MODEL = os.getenv(
    "DRAFT_MODEL",
    VERIFIER_MODEL if FAST_DEMO else DRAFT_MODEL_SMALL,
)

DEFAULT_VERIFIER_URL = "http://192.168.50.1:8010"
DEFAULT_BLOCK_SIZE = int(os.getenv("BLOCK_SIZE", "8" if FAST_DEMO else "2"))
DEFAULT_MAX_NEW_TOKENS = 128
DEFAULT_PORT = 8010

# Legacy Qwen pair (set FAST_DEMO=0 and env vars to reproduce old experiments)
QWEN_VERIFIER = "Qwen/Qwen2.5-1.5B-Instruct"
QWEN_DRAFT = "Qwen/Qwen2.5-0.5B-Instruct"
