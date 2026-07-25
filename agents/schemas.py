from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


class ToolCall(BaseModel):
    tool_name: str = Field(..., min_length = 1, description="Name of the tool to execute")
    tool_args_json: str = Field(
        default="{}",
        description="JSON object string containing the arguments to pass into the tool"
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
    
    @model_validator(mode="after")
    def validate_action_payload(self) -> "AgentStep":
        if self.action_type == "tool_call":
            if self.tool_call is None:
                raise ValueError(
                    "tool_call is required when action_type is 'tool_call'."
                )
            if self.final_answer is not None:
                raise ValueError(
                    "final_answer must be omitted when action_type is 'tool_call'."
                )

        elif self.action_type == "final_answer":
            if self.tool_call is not None:
                raise ValueError(
                    "tool_call must be omitted when action_type is 'final_answer'."
                )

            normalized_answer = (self.final_answer or "").strip()
            if not normalized_answer:
                raise ValueError(
                    "final_answer must be non-empty when action_type is 'final_answer'."
                )

            self.final_answer = normalized_answer

        return self


class ToolObservation(BaseModel):
    tool_name: str
    tool_args: dict[str, Any]
    result: dict[str, Any]
    success: bool = True
    error: str | None = None