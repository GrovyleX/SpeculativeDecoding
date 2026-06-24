"""Speculative decoding client — run on Windows (draft machine)."""

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from draft.model import DraftModel
from shared.config import DEFAULT_BLOCK_SIZE, DEFAULT_MAX_NEW_TOKENS, DEFAULT_VERIFIER_URL, FAST_DEMO
from shared.protocol import SessionStartRequest, VerifyRequest, VerifyResponse


@dataclass
class RunStats:
    blocks: int = 0
    total_accepted: int = 0
    total_drafted: int = 0
    total_draft_ms: float = 0.0
    total_network_ms: float = 0.0
    total_verify_ms: float = 0.0
    tokens_generated: int = 0
    block_log: list[str] = field(default_factory=list)

    @property
    def acceptance_rate(self) -> float:
        if self.total_drafted == 0:
            return 0.0
        return self.total_accepted / self.total_drafted

    def summary(self, elapsed_s: float) -> str:
        tps = self.tokens_generated / elapsed_s if elapsed_s > 0 else 0.0
        mode = "FAST_DEMO (same model)" if FAST_DEMO else "honest (0.5B draft)"
        lines = [
            "",
            "=== Speculative run summary ===",
            f"Mode             : {mode}",
            f"Tokens generated : {self.tokens_generated}",
            f"Total time       : {elapsed_s:.2f}s",
            f"Throughput       : {tps:.2f} tok/s",
            f"Blocks           : {self.blocks}",
            f"Acceptance rate  : {self.acceptance_rate:.1%} "
            f"({self.total_accepted}/{self.total_drafted} draft tokens)",
            f"Avg draft ms     : {self.total_draft_ms / max(self.blocks, 1):.1f}",
            f"Avg network ms   : {self.total_network_ms / max(self.blocks, 1):.1f}",
            f"Avg verify ms    : {self.total_verify_ms / max(self.blocks, 1):.1f}",
        ]
        return "\n".join(lines)


def wait_for_verifier(http: requests.Session, url: str, timeout_s: float = 300.0) -> None:
    deadline = time.time() + timeout_s
    health_url = f"{url.rstrip('/')}/health"
    print(f"Waiting for verifier at {health_url} ...")
    while time.time() < deadline:
        try:
            resp = http.get(health_url, timeout=5)
            if resp.status_code == 200:
                info = resp.json()
                print(
                    f"Verifier ready: {info['model']} on {info['device']} "
                    f"(fast_demo={info.get('fast_demo', '?')})"
                )
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError(f"Verifier not reachable at {url} after {timeout_s}s")


def start_session(http: requests.Session, verifier_url: str, prompt_ids: list[int]) -> str:
    resp = http.post(
        f"{verifier_url.rstrip('/')}/session/start",
        json=SessionStartRequest(prompt_ids=prompt_ids).model_dump(),
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["session_id"]


def speculative_generate(
    draft: DraftModel,
    http: requests.Session,
    verifier_url: str,
    prompt: str,
    max_new_tokens: int,
    block_size: int,
) -> tuple[list[int], RunStats, float]:
    output_ids = draft.encode_prompt(prompt)
    start_len = len(output_ids)
    stats = RunStats()
    t_start = time.perf_counter()

    session_id = start_session(http, verifier_url, output_ids)

    while len(output_ids) - start_len < max_new_tokens:
        draft_ids, draft_ms = draft.draft_tokens(output_ids, block_size)
        stats.total_draft_ms += draft_ms

        req = VerifyRequest(session_id=session_id, draft_ids=draft_ids)
        t_net = time.perf_counter()
        resp = http.post(
            f"{verifier_url.rstrip('/')}/verify",
            json=req.model_dump(),
            timeout=120,
        )
        resp.raise_for_status()
        network_ms = (time.perf_counter() - t_net) * 1000

        result = VerifyResponse(**resp.json())
        stats.blocks += 1
        stats.total_accepted += result.accepted
        stats.total_drafted += len(draft_ids)
        stats.total_network_ms += network_ms
        stats.total_verify_ms += result.verify_ms

        output_ids.extend(draft_ids[: result.accepted])
        output_ids.append(result.next_token)
        draft.sync_after_verify(output_ids)
        stats.tokens_generated = len(output_ids) - start_len

        stats.block_log.append(
            f"block={stats.blocks} K={block_size} accepted={result.accepted} "
            f"draft_ms={draft_ms:.1f} network_ms={network_ms:.1f} "
            f"verify_ms={result.verify_ms:.1f}"
        )
        print(stats.block_log[-1])

        if draft.tokenizer.eos_token_id is not None:
            if result.next_token == draft.tokenizer.eos_token_id:
                break
            if any(t == draft.tokenizer.eos_token_id for t in draft_ids[: result.accepted]):
                break

    elapsed = time.perf_counter() - t_start
    return output_ids, stats, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Speculative decoding draft client")
    parser.add_argument("--verifier", default=DEFAULT_VERIFIER_URL, help="Verifier base URL")
    parser.add_argument("--prompt", default="Explain speculative decoding in one short paragraph.")
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--block-size", type=int, default=DEFAULT_BLOCK_SIZE)
    parser.add_argument("--skip-wait", action="store_true", help="Do not wait for /health")
    args = parser.parse_args()

    http = requests.Session()
    if not args.skip_wait:
        wait_for_verifier(http, args.verifier)

    draft = DraftModel()
    output_ids, stats, elapsed = speculative_generate(
        draft=draft,
        http=http,
        verifier_url=args.verifier,
        prompt=args.prompt,
        max_new_tokens=args.max_new_tokens,
        block_size=args.block_size,
    )

    text = draft.decode(output_ids)
    print("\n=== Generated text ===")
    print(text)
    print(stats.summary(elapsed))


if __name__ == "__main__":
    main()
