from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="The user's natural-language investment analysis question.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional client-provided session ID for storing analysis history.",
    )


class AnalyzeResponse(BaseModel):
    status: str
    answer: str | None = None
    message: str | None = None
    trace: list[dict[str, Any]]
    
    
class HistoryItem(BaseModel):
    query: str
    status: str
    answer: str | None = None
    message: str | None = None
    trace: list[dict[str, Any]]


class HistoryResponse(BaseModel):
    session_id: str
    items: list[HistoryItem]