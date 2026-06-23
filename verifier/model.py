import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from shared.config import VERIFIER_MODEL


class TargetModel:
    """Target (verifier) model loaded once at server startup."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv("VERIFIER_MODEL", VERIFIER_MODEL)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

        print(f"Loading verifier model: {self.model_name} on {self.device} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config if self.device == "cuda" else None,
            device_map={"": 0} if self.device == "cuda" else None,
            torch_dtype=torch.float16 if self.device == "cpu" else None,
        )
        self.model.eval()
        print("Verifier model ready.")

    def verify(self, prompt_ids: list[int], draft_ids: list[int]) -> tuple[int, int, float]:
        """
        Greedy speculative verification.

        Returns (accepted_count, next_token, verify_ms).
        """
        t0 = time.perf_counter()
        full_ids = prompt_ids + draft_ids
        input_ids = torch.tensor([full_ids], device=self.model.device)

        with torch.no_grad():
            logits = self.model(input_ids).logits[0]

        prompt_len = len(prompt_ids)
        accepted = 0

        for k, draft_token in enumerate(draft_ids):
            pos = prompt_len + k - 1
            target_token = int(logits[pos].argmax().item())
            if target_token == draft_token:
                accepted += 1
            else:
                verify_ms = (time.perf_counter() - t0) * 1000
                return accepted, target_token, verify_ms

        next_pos = prompt_len + len(draft_ids) - 1
        next_token = int(logits[next_pos].argmax().item())
        verify_ms = (time.perf_counter() - t0) * 1000
        return accepted, next_token, verify_ms

    def next_token(self, prompt_ids: list[int]) -> tuple[int, float]:
        """Single-step autoregressive token (baseline decoding)."""
        t0 = time.perf_counter()
        input_ids = torch.tensor([prompt_ids], device=self.model.device)

        with torch.no_grad():
            logits = self.model(input_ids).logits[0, -1]

        token = int(logits.argmax().item())
        verify_ms = (time.perf_counter() - t0) * 1000
        return token, verify_ms
