import pytest

from agents.react_agent import (
    AgentStepValidationError,
    ReActAgent,
)
from agents.schemas import AgentStep


def make_invalid_step() -> AgentStep:
    return AgentStep.model_validate(
        {
            "thought": "I need market data.",
            "action_type": "tool_call",
            "tool_call": None,
            "final_answer": None,
        }
    )


def test_invalid_step_retries_once_then_succeeds() -> None:
    agent = object.__new__(ReActAgent)
    agent.max_steps = 1
    agent.max_step_validation_retries = 1

    retry_flags: list[bool] = []

    def fake_llm_step(
        user_query: str,
        trace: list[dict],
        is_validation_retry: bool = False,
    ) -> AgentStep:
        retry_flags.append(is_validation_retry)

        if len(retry_flags) == 1:
            return make_invalid_step()

        return AgentStep(
            thought="The retry produced a valid answer.",
            action_type="final_answer",
            final_answer="Grounded final answer.",
        )

    agent._llm_step = fake_llm_step

    events = list(
        agent.run_with_events(
            "test query",
            trace_id="trace-123",
        )
    )

    assert retry_flags == [False, True]
    assert [event["event"] for event in events] == [
        "start",
        "thought",
        "final_answer",
    ]
    assert events[-1]["data"]["status"] == "success"
    assert events[-1]["data"]["answer"] == "Grounded final answer."


def test_repeated_invalid_steps_emit_controlled_error() -> None:
    agent = object.__new__(ReActAgent)
    agent.max_steps = 3
    agent.max_step_validation_retries = 1

    retry_flags: list[bool] = []

    def always_invalid_llm_step(
        user_query: str,
        trace: list[dict],
        is_validation_retry: bool = False,
    ) -> AgentStep:
        retry_flags.append(is_validation_retry)
        return make_invalid_step()

    agent._llm_step = always_invalid_llm_step

    events = list(
        agent.run_with_events(
            "test query",
            trace_id="trace-123",
        )
    )

    assert retry_flags == [False, True]
    assert [event["event"] for event in events] == [
        "start",
        "error",
    ]

    error_data = events[-1]["data"]

    assert error_data["status"] == "error"
    assert error_data["trace_id"] == "trace-123"
    assert error_data["trace"] == []
    assert error_data["message"] == (
        "The model repeatedly returned an invalid action. "
        "Please retry the request."
    )


def test_validation_retries_can_be_disabled() -> None:
    agent = object.__new__(ReActAgent)
    agent.max_step_validation_retries = 0

    retry_flags: list[bool] = []

    def always_invalid_llm_step(
        user_query: str,
        trace: list[dict],
        is_validation_retry: bool = False,
    ) -> AgentStep:
        retry_flags.append(is_validation_retry)
        return make_invalid_step()

    agent._llm_step = always_invalid_llm_step

    with pytest.raises(
        AgentStepValidationError,
        match="after 1 attempts",
    ):
        agent._get_validated_llm_step(
            user_query="test query",
            trace=[],
        )

    assert retry_flags == [False]


def test_negative_validation_retry_limit_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with pytest.raises(
        ValueError,
        match="cannot be negative",
    ):
        ReActAgent(
            tool_registry=object(),
            max_step_validation_retries=-1,
        )
