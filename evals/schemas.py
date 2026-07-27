from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ToolCallExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(..., min_length=1)
    args_subset: dict[str, Any] = Field(default_factory=dict)
    outcome: Literal["success", "failure", "any"] = "success"
    min_calls: int = Field(default=1, ge=1)

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError(
                "tool_name must not have surrounding whitespace"
            )
        return value


class GoldenQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-z0-9_]+$",
    )
    category: str = Field(..., min_length=1)
    tier: Literal["core", "stress"] = "core"
    query: str = Field(..., min_length=1)

    expected_tools: list[str] = Field(..., min_length=1)
    optional_tools: list[str] = Field(default_factory=list)
    required_tool_calls: list[ToolCallExpectation] = Field(
        default_factory=list
    )

    must_preserve: list[str] = Field(default_factory=list)
    must_mention: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)

    notes: str = Field(..., min_length=1)

    @field_validator("category", "query", "notes")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("expected_tools", "optional_tools")
    @classmethod
    def validate_tool_names(cls, values: list[str]) -> list[str]:
        if any(not value or value != value.strip() for value in values):
            raise ValueError(
                "tool names must be nonblank and have no surrounding whitespace"
            )

        if len(values) != len(set(values)):
            raise ValueError("tool names must not contain duplicates")

        return values

    @field_validator("must_preserve", "must_mention", "forbidden")
    @classmethod
    def reject_blank_requirements(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("evaluation requirements must not be blank")
        return values

    @model_validator(mode="after")
    def ensure_tool_roles_do_not_overlap(self) -> GoldenQuery:
        required_tool_names = {
            expectation.tool_name
            for expectation in self.required_tool_calls
        }
        required_names = set(self.expected_tools) | required_tool_names
        overlap = required_names & set(self.optional_tools)

        if overlap:
            overlapping_names = ", ".join(sorted(overlap))
            raise ValueError(
                "tools cannot be both expected and optional: "
                f"{overlapping_names}"
            )

        return self