"""Run speculative vs baseline on the same prompt and print comparison."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from shared.config import DEFAULT_BLOCK_SIZE, DEFAULT_MAX_NEW_TOKENS, DEFAULT_VERIFIER_URL


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare speculative vs baseline")
    parser.add_argument("--verifier", default=DEFAULT_VERIFIER_URL)
    parser.add_argument("--prompt", default="Explain speculative decoding in one short paragraph.")
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--block-size", type=int, default=DEFAULT_BLOCK_SIZE)
    args = parser.parse_args()

    print(">>> Running baseline (verifier autoregressive)...")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "bench" / "baseline.py"),
            "--verifier",
            args.verifier,
            "--prompt",
            args.prompt,
            "--max-new-tokens",
            str(args.max_new_tokens),
        ],
        check=True,
        cwd=str(ROOT),
    )

    print("\n>>> Running speculative (draft + verify)...")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "draft" / "client.py"),
            "--verifier",
            args.verifier,
            "--prompt",
            args.prompt,
            "--max-new-tokens",
            str(args.max_new_tokens),
            "--block-size",
            str(args.block_size),
            "--skip-wait",
        ],
        check=True,
        cwd=str(ROOT),
    )


if __name__ == "__main__":
    main()
