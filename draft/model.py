import os

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from shared.config import DRAFT_MODEL, FAST_DEMO


class DraftModel:
    """Draft model with KV cache for fast block drafting."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv("DRAFT_MODEL", DRAFT_MODEL)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

        print(f"Loading draft model: {self.model_name} on {self.device} ...")
        if FAST_DEMO:
            print("FAST_DEMO: draft matches verifier -> expect ~100% acceptance (greedy)")
        else:
            print(f"Real SD: {self.model_name.split('/')[-1]} draft -> SmolLM2-1.7B verifier")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config if self.device.type == "cuda" else None,
            device_map={"": 0} if self.device.type == "cuda" else None,
            torch_dtype=torch.float16 if self.device.type == "cpu" else None,
        )
        self.model.eval()
        self._token_ids: list[int] = []
        self._past_key_values = None
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

    def reset_cache(self) -> None:
        self._token_ids = []
        self._past_key_values = None

    def _crop_cache(self, length: int) -> None:
        self._token_ids = self._token_ids[:length]
        if self._past_key_values is not None and hasattr(self._past_key_values, "crop"):
            self._past_key_values.crop(length)

    def _sync_cache(self, prompt_ids: list[int]) -> None:
        if self._token_ids == prompt_ids:
            return
        self.reset_cache()
        input_ids = torch.tensor([prompt_ids], device=self.device)
        with torch.inference_mode():
            outputs = self.model(input_ids, use_cache=True)
        self._past_key_values = outputs.past_key_values
        self._token_ids = list(prompt_ids)

    def draft_tokens(self, prompt_ids: list[int], k: int) -> tuple[list[int], float]:
        """Generate k greedy draft tokens using KV cache; roll back before returning."""
        import time

        t0 = time.perf_counter()
        self._sync_cache(prompt_ids)
        snap_len = len(self._token_ids)

        draft: list[int] = []
        input_ids = torch.tensor([[self._token_ids[-1]]], device=self.device)
        self._crop_cache(snap_len - 1)
        with torch.inference_mode():
            outputs = self.model(
                input_ids,
                past_key_values=self._past_key_values,
                use_cache=True,
            )
        logits = outputs.logits[0, -1]
        self._past_key_values = outputs.past_key_values
        self._token_ids = list(prompt_ids)

        for _ in range(k):
            next_id = int(logits.argmax().item())
            draft.append(next_id)
            with torch.inference_mode():
                outputs = self.model(
                    torch.tensor([[next_id]], device=self.device),
                    past_key_values=self._past_key_values,
                    use_cache=True,
                )
            self._past_key_values = outputs.past_key_values
            self._token_ids.append(next_id)
            logits = outputs.logits[0, -1]

        self._crop_cache(snap_len)
        draft_ms = (time.perf_counter() - t0) * 1000
        return draft, draft_ms

    def sync_after_verify(self, prompt_ids: list[int]) -> None:
        """Resync draft cache after verifier accepts/rejects tokens."""
        self._sync_cache(prompt_ids)
