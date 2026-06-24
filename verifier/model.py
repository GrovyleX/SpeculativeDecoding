import os
import time
import uuid

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from shared.config import FAST_DEMO, VERIFIER_MODEL


class VerifierSession:
    """One decoding session with KV cache on the verifier GPU."""

    def __init__(self, model: AutoModelForCausalLM, device: torch.device, prompt_ids: list[int]) -> None:
        self.model = model
        self.device = device
        self.token_ids: list[int] = list(prompt_ids)
        self.past_key_values = None
        self._prefill(prompt_ids)

    def _prefill(self, prompt_ids: list[int]) -> None:
        input_ids = torch.tensor([prompt_ids], device=self.device)
        with torch.inference_mode():
            outputs = self.model(input_ids, use_cache=True)
        self.past_key_values = outputs.past_key_values

    def _crop_cache(self, length: int) -> None:
        if self.past_key_values is not None and hasattr(self.past_key_values, "crop"):
            self.past_key_values.crop(length)

    def _append_tokens(self, token_ids: list[int]) -> None:
        if not token_ids:
            return
        input_ids = torch.tensor([token_ids], device=self.device)
        with torch.inference_mode():
            outputs = self.model(
                input_ids,
                past_key_values=self.past_key_values,
                use_cache=True,
            )
        self.past_key_values = outputs.past_key_values
        self.token_ids.extend(token_ids)

    def verify(self, draft_ids: list[int]) -> tuple[int, int, float]:
        t0 = time.perf_counter()
        input_ids = torch.tensor([draft_ids], device=self.device)

        with torch.inference_mode():
            outputs = self.model(
                input_ids,
                past_key_values=self.past_key_values,
                use_cache=True,
            )

        logits = outputs.logits[0]
        prefix_len = len(self.token_ids)

        for i, draft_token in enumerate(draft_ids):
            predicted = int(logits[i].argmax().item())
            if predicted != draft_token:
                self._crop_cache(prefix_len + i)
                self.token_ids.extend(draft_ids[:i])
                self._append_tokens([predicted])
                verify_ms = (time.perf_counter() - t0) * 1000
                return i, predicted, verify_ms

        next_token = int(logits[-1].argmax().item())
        self.past_key_values = outputs.past_key_values
        self.token_ids.extend(draft_ids)
        self._append_tokens([next_token])

        verify_ms = (time.perf_counter() - t0) * 1000
        return len(draft_ids), next_token, verify_ms

    def next_token(self) -> tuple[int, float]:
        t0 = time.perf_counter()
        self._crop_cache(len(self.token_ids) - 1)
        last_token = self.token_ids[-1]
        input_ids = torch.tensor([[last_token]], device=self.device)
        with torch.inference_mode():
            outputs = self.model(
                input_ids,
                past_key_values=self.past_key_values,
                use_cache=True,
            )
        token = int(outputs.logits[0, -1].argmax().item())
        self.past_key_values = outputs.past_key_values
        self._append_tokens([token])
        verify_ms = (time.perf_counter() - t0) * 1000
        return token, verify_ms


class TargetModel:
    """Target (verifier) model with session-based KV-cache decoding."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv("VERIFIER_MODEL", VERIFIER_MODEL)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

        print(f"Loading verifier model: {self.model_name} on {self.device} ...")
        print(f"FAST_DEMO mode: {FAST_DEMO} (0 = SmolLM2-360M draft → {self.model_name.split('/')[-1]})")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config if self.device.type == "cuda" else None,
            device_map={"": 0} if self.device.type == "cuda" else None,
            torch_dtype=torch.float16 if self.device.type == "cpu" else None,
        )
        self.model.eval()
        self.sessions: dict[str, VerifierSession] = {}
        print("Verifier model ready.")

    def start_session(self, prompt_ids: list[int]) -> str:
        session_id = uuid.uuid4().hex
        self.sessions[session_id] = VerifierSession(self.model, self.device, prompt_ids)
        return session_id

    def get_session(self, session_id: str) -> VerifierSession:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session_id: {session_id}")
        return session

    def end_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)
