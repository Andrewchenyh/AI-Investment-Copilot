from typing import Any, Literal
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute")
    tool_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass into the tool"
    )


class AgentStep(BaseModel):
    thought: str = Field(..., description="Why the agent chose this next step")
    action_type: Literal["tool_call", "final_answer"] = Field(
        ...,
        description="Whether to call a tool or finish with an answer"
    )
    tool_call: ToolCall | None = Field(
        default=None,
        description="Required when action_type is tool_call"
    )
    final_answer: str | None = Field(
        default=None,
        description="Required when action_type is final_answer"
    )


class ToolObservation(BaseModel):
    tool_name: str
    tool_args: dict[str, Any]
    result: dict[str, Any]
    success: bool = True
    error: str | None = None