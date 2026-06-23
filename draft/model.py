import os

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from shared.config import DRAFT_MODEL


class DraftModel:
    """Small draft model running locally on the client machine."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv("DRAFT_MODEL", DRAFT_MODEL)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

        print(f"Loading draft model: {self.model_name} on {self.device} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config if self.device == "cuda" else None,
            device_map={"": 0} if self.device == "cuda" else None,
            torch_dtype=torch.float16 if self.device == "cpu" else None,
        )
        self.model.eval()
        print("Draft model ready.")

    def encode_prompt(self, prompt: str) -> list[int]:
        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        return self.tokenizer.encode(text, add_special_tokens=False)

    def decode(self, token_ids: list[int]) -> str:
        return self.tokenizer.decode(token_ids, skip_special_tokens=True)

    def draft_tokens(self, prompt_ids: list[int], k: int) -> tuple[list[int], float]:
        """Generate k greedy draft tokens autoregressively."""
        import time

        t0 = time.perf_counter()
        ids = list(prompt_ids)
        draft: list[int] = []

        for _ in range(k):
            input_ids = torch.tensor([ids], device=self.model.device)
            with torch.no_grad():
                logits = self.model(input_ids).logits[0, -1]
            next_id = int(logits.argmax().item())
            draft.append(next_id)
            ids.append(next_id)

        draft_ms = (time.perf_counter() - t0) * 1000
        return draft, draft_ms
