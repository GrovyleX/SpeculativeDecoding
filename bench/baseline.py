"""Baseline autoregressive decoding via verifier /next_token (no draft model)."""

import argparse
import sys
import time
from pathlib import Path

import requests
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import DEFAULT_MAX_NEW_TOKENS, DEFAULT_VERIFIER_URL, VERIFIER_MODEL
from shared.protocol import NextTokenRequest, SessionStartRequest


def encode_prompt(tokenizer: AutoTokenizer, prompt: str) -> list[int]:
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    return tokenizer.encode(text, add_special_tokens=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline decoding via verifier only")
    parser.add_argument("--verifier", default=DEFAULT_VERIFIER_URL)
    parser.add_argument("--prompt", default="Explain speculative decoding in one short paragraph.")
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(VERIFIER_MODEL)
    output_ids = encode_prompt(tokenizer, args.prompt)
    start_len = len(output_ids)
    total_verify_ms = 0.0
    t_start = time.perf_counter()

    http = requests.Session()
    base = args.verifier.rstrip("/")
    session_resp = http.post(
        f"{base}/session/start",
        json=SessionStartRequest(prompt_ids=output_ids).model_dump(),
        timeout=120,
    )
    session_resp.raise_for_status()
    session_id = session_resp.json()["session_id"]

    while len(output_ids) - start_len < args.max_new_tokens:
        req = NextTokenRequest(session_id=session_id)
        resp = http.post(
            f"{base}/next_token",
            json=req.model_dump(),
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        total_verify_ms += data["verify_ms"]
        output_ids.append(data["next_token"])
        if tokenizer.eos_token_id == data["next_token"]:
            break

    elapsed = time.perf_counter() - t_start
    tokens = len(output_ids) - start_len
    tps = tokens / elapsed if elapsed > 0 else 0.0

    print("\n=== Generated text (baseline) ===")
    print(tokenizer.decode(output_ids, skip_special_tokens=True))
    print("\n=== Baseline summary ===")
    print(f"Tokens generated : {tokens}")
    print(f"Total time       : {elapsed:.2f}s")
    print(f"Throughput       : {tps:.2f} tok/s")
    print(f"Total verify ms  : {total_verify_ms:.1f}")


if __name__ == "__main__":
    main()
