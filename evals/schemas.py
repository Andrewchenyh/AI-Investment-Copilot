from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from evals.concept_patterns import ANSWER_CONCEPT_PATTERNS


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
    query: str = Field(..., min_length=1)

    required_tool_calls: list[ToolCallExpectation] = Field(
        ...,
        min_length=1,
    )
    required_answer_concepts: list[str] = Field(
        ...,
        min_length=1,
    )
    required_answer_literals: list[str] = Field(default_factory=list)
    required_answer_literal_groups: list[list[str]] = Field(
        default_factory=list,
    )
    notes: str = Field(..., min_length=1)

    @field_validator("category", "query", "notes")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("required_answer_literals")
    @classmethod
    def validate_answer_literals(cls, values: list[str]) -> list[str]:
        if any(not value or value != value.strip() for value in values):
            raise ValueError(
                "required answer literals must be nonblank and trimmed"
            )

        normalized_values = [value.casefold() for value in values]
        if len(normalized_values) != len(set(normalized_values)):
            raise ValueError(
                "required answer literals must not contain duplicates"
            )

        return values

    @field_validator("required_answer_literal_groups")
    @classmethod
    def validate_answer_literal_groups(
        cls,
        groups: list[list[str]],
    ) -> list[list[str]]:
        for group in groups:
            if not group:
                raise ValueError(
                    "required answer literal groups must not be empty"
                )

            if any(
                not literal or literal != literal.strip()
                for literal in group
            ):
                raise ValueError(
                    "literal alternatives must be nonblank and trimmed"
                )

            normalized_literals = [
                literal.casefold()
                for literal in group
            ]
            if len(normalized_literals) != len(
                set(normalized_literals)
            ):
                raise ValueError(
                    "literal alternatives must not contain duplicates"
                )

        return groups

    @field_validator("required_answer_concepts")
    @classmethod
    def validate_answer_concepts(
        cls,
        values: list[str],
    ) -> list[str]:
        if any(
            not value
            or value != value.strip()
            for value in values
        ):
            raise ValueError(
                "required answer concepts must be nonblank and trimmed"
            )

        normalized_values = [
            value.casefold()
            for value in values
        ]
        if len(normalized_values) != len(
            set(normalized_values)
        ):
            raise ValueError(
                "required answer concepts must be unique"
            )

        unknown_concepts = sorted(
            set(values) - ANSWER_CONCEPT_PATTERNS.keys()
        )
        if unknown_concepts:
            raise ValueError(
                "unknown required answer concepts: "
                f"{unknown_concepts}"
            )

        return values
