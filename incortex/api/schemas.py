"""Pydantic request models and the one response envelope (Design_Doc §19).

Every response — success or failure — is the same envelope:
{"success": bool, "data": ... | null, "error": str | null}.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = Field(default="default", min_length=1)

    model_config = {"extra": "forbid"}


class MemoryAddRequest(BaseModel):
    content: str = Field(min_length=1)
    importance: float | None = Field(default=None, ge=0.0, le=1.0)

    model_config = {"extra": "forbid"}


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=50)

    model_config = {"extra": "forbid"}


class FeedbackRequest(BaseModel):
    success: bool
    rating: float | None = Field(default=None, ge=0.0, le=1.0)
    session_id: str = Field(default="default", min_length=1)

    model_config = {"extra": "forbid"}


class ToolExecuteRequest(BaseModel):
    tool: str = Field(min_length=1)
    request: dict = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


def envelope(data=None, error=None):
    """The consistent API envelope; exactly one of data/error is set."""
    return {"success": error is None, "data": data, "error": error}
