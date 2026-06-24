"""Shared defaults for draft/verifier models and generation."""

import os

VERIFIER_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DRAFT_MODEL_SMALL = "Qwen/Qwen2.5-0.5B-Instruct"

# FAST_DEMO=1 (default): same model draft+verifier → ~100% greedy acceptance + KV cache speedups
# FAST_DEMO=0: honest 0.5B draft vs 1.5B verifier comparison
FAST_DEMO = os.getenv("FAST_DEMO", "1") == "1"
DRAFT_MODEL = VERIFIER_MODEL if FAST_DEMO else DRAFT_MODEL_SMALL

DEFAULT_VERIFIER_URL = "http://192.168.50.1:8010"
DEFAULT_BLOCK_SIZE = 8 if FAST_DEMO else 4
DEFAULT_MAX_NEW_TOKENS = 128
DEFAULT_PORT = 8010
