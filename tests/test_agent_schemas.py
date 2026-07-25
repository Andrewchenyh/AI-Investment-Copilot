import pytest
from pydantic import ValidationError

from agents.schemas import AgentStep, ToolCall


def test_tool_action_requires_only_tool_call() -> None:
    tool_call = ToolCall(
        tool_name="get_current_price",
        tool_args_json='{"ticker": "ORCL"}',
    )

    step = AgentStep(
        thought="I need the current price.",
        action_type="tool_call",
        tool_call=tool_call,
    )

    assert step.tool_call == tool_call
    assert step.final_answer is None


def test_final_action_normalizes_answer_text() -> None:
    step = AgentStep(
        thought="The analysis is complete.",
        action_type="final_answer",
        final_answer="  ORCL is trading at the observed price.  ",
    )

    assert step.final_answer == "ORCL is trading at the observed price."
    assert step.tool_call is None


def test_tool_action_rejects_missing_tool_call() -> None:
    with pytest.raises(ValidationError, match="tool_call is required"):
        AgentStep(
            thought="I need market data.",
            action_type="tool_call",
        )


def test_tool_action_rejects_final_answer() -> None:
    with pytest.raises(
        ValidationError,
        match="final_answer must be omitted",
    ):
        AgentStep(
            thought="I need market data.",
            action_type="tool_call",
            tool_call=ToolCall(
                tool_name="get_current_price",
                tool_args_json='{"ticker": "ORCL"}',
            ),
            final_answer="Contradictory answer.",
        )


def test_final_action_rejects_missing_answer() -> None:
    with pytest.raises(
        ValidationError,
        match="final_answer must be non-empty",
    ):
        AgentStep(
            thought="The analysis is complete.",
            action_type="final_answer",
        )


def test_final_action_rejects_whitespace_only_answer() -> None:
    with pytest.raises(
        ValidationError,
        match="final_answer must be non-empty",
    ):
        AgentStep(
            thought="The analysis is complete.",
            action_type="final_answer",
            final_answer="   ",
        )


def test_final_action_rejects_tool_call() -> None:
    with pytest.raises(
        ValidationError,
        match="tool_call must be omitted",
    ):
        AgentStep(
            thought="The analysis is complete.",
            action_type="final_answer",
            tool_call=ToolCall(
                tool_name="get_current_price",
                tool_args_json='{"ticker": "ORCL"}',
            ),
            final_answer="Final answer.",
        )


def test_tool_call_rejects_empty_tool_name() -> None:
    with pytest.raises(ValidationError):
        ToolCall(
            tool_name="",
            tool_args_json="{}",
        )