from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="The user's natural-language investment analysis question."
    )


class AnalyzeResponse(BaseModel):
    status: str
    answer: str | None = None
    message: str | None = None
    trace: list[dict[str, Any]]