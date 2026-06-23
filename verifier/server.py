import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import DEFAULT_PORT, VERIFIER_MODEL
from shared.protocol import (
    HealthResponse,
    NextTokenRequest,
    NextTokenResponse,
    VerifyRequest,
    VerifyResponse,
)
from verifier.model import TargetModel

target: TargetModel | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global target
    model_name = os.getenv("VERIFIER_MODEL", VERIFIER_MODEL)
    target = TargetModel(model_name=model_name)
    yield
    target = None


app = FastAPI(title="Speculative Decoding Verifier", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if target is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return HealthResponse(
        status="ok",
        model=target.model_name,
        device=target.device,
    )


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest) -> VerifyResponse:
    if target is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if not req.prompt_ids:
        raise HTTPException(status_code=400, detail="prompt_ids must not be empty")

    accepted, next_token, verify_ms = target.verify(req.prompt_ids, req.draft_ids)
    return VerifyResponse(
        accepted=accepted,
        next_token=next_token,
        verify_ms=verify_ms,
    )


@app.post("/next_token", response_model=NextTokenResponse)
def next_token(req: NextTokenRequest) -> NextTokenResponse:
    if target is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if not req.prompt_ids:
        raise HTTPException(status_code=400, detail="prompt_ids must not be empty")

    token, verify_ms = target.next_token(req.prompt_ids)
    return NextTokenResponse(next_token=token, verify_ms=verify_ms)


def main() -> None:
    port = int(os.getenv("PORT", DEFAULT_PORT))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(
        "verifier.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
