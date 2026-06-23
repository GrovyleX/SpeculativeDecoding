from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    prompt_ids: list[int]
    draft_ids: list[int] = Field(min_length=1)


class VerifyResponse(BaseModel):
    accepted: int
    next_token: int
    verify_ms: float
    network_hint_ms: float | None = None


class NextTokenRequest(BaseModel):
    prompt_ids: list[int]


class NextTokenResponse(BaseModel):
    next_token: int
    verify_ms: float


class HealthResponse(BaseModel):
    status: str
    model: str
    device: str
