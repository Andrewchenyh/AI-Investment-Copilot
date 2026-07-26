from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


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
        overlap = set(self.expected_tools) & set(self.optional_tools)

        if overlap:
            overlapping_names = ", ".join(sorted(overlap))
            raise ValueError(
                "tools cannot be both expected and optional: "
                f"{overlapping_names}"
            )

        return self