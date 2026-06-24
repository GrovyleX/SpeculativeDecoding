from pydantic import BaseModel, Field


class SessionStartRequest(BaseModel):
    prompt_ids: list[int] = Field(min_length=1)


class SessionStartResponse(BaseModel):
    session_id: str


class VerifyRequest(BaseModel):
    session_id: str
    draft_ids: list[int] = Field(min_length=1)


class VerifyResponse(BaseModel):
    accepted: int
    next_token: int
    verify_ms: float


class NextTokenRequest(BaseModel):
    session_id: str


class NextTokenResponse(BaseModel):
    next_token: int
    verify_ms: float


class HealthResponse(BaseModel):
    status: str
    model: str
    device: str
    fast_demo: bool
    sessions: int
