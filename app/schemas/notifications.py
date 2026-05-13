from typing import Optional

from pydantic import BaseModel, Field


class FcmTokenRegisterRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=4096)
    user_agent: Optional[str] = Field(None, max_length=500)


class FcmTestPushResponse(BaseModel):
    ok: bool
    success: int = 0
    failure: int = 0
    tokens_targeted: int = 0
    reason: Optional[str] = None
    detail: Optional[str] = None
