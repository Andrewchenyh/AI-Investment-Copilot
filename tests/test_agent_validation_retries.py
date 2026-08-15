import httpx
import pytest

from agents.react_agent import (
    DEFAULT_AGENT_RUNTIME_SECONDS,
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
    agent.max_runtime_seconds = DEFAULT_AGENT_RUNTIME_SECONDS

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
    agent.max_runtime_seconds = DEFAULT_AGENT_RUNTIME_SECONDS

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


def test_model_timeout_retries_once_then_succeeds(mocker) -> None:
    agent = object.__new__(ReActAgent)
    agent.max_step_validation_retries = 1
    agent.max_model_timeout_retries = 1
    agent.model_timeout_retry_delay_seconds = 1.0
    final_step = AgentStep(
        thought="The retry succeeded.",
        action_type="final_answer",
        final_answer="Grounded final answer.",
    )
    llm_step = mocker.patch.object(
        agent,
        "_llm_step",
        side_effect=[
            httpx.ReadTimeout("model response timed out"),
            final_step,
        ],
    )
    sleep = mocker.patch("agents.react_agent.time.sleep")

    result = agent._get_validated_llm_step(
        user_query="test query",
        trace=[],
    )

    assert result == final_step
    assert llm_step.call_count == 2
    assert [
        call.kwargs["is_validation_retry"]
        for call in llm_step.call_args_list
    ] == [False, False]
    sleep.assert_called_once_with(1.0)


def test_model_timeout_raises_after_retry_limit(mocker) -> None:
    agent = object.__new__(ReActAgent)
    agent.max_step_validation_retries = 1
    agent.max_model_timeout_retries = 1
    agent.model_timeout_retry_delay_seconds = 0
    llm_step = mocker.patch.object(
        agent,
        "_llm_step",
        side_effect=httpx.ReadTimeout("model response timed out"),
    )

    with pytest.raises(
        httpx.ReadTimeout,
        match="model response timed out",
    ):
        agent._get_validated_llm_step(
            user_query="test query",
            trace=[],
        )

    assert llm_step.call_count == 2


def test_timeout_and_validation_retries_use_independent_budgets(
    mocker,
) -> None:
    agent = object.__new__(ReActAgent)
    agent.max_step_validation_retries = 1
    agent.max_model_timeout_retries = 2
    agent.model_timeout_retry_delay_seconds = 0
    final_step = AgentStep(
        thought="Both transient failures were recovered.",
        action_type="final_answer",
        final_answer="Grounded final answer.",
    )
    call_count = 0

    def fake_llm_step(**kwargs) -> AgentStep:
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            raise httpx.ReadTimeout("first timeout")
        if call_count == 2:
            return make_invalid_step()
        if call_count == 3:
            raise httpx.ReadTimeout("second timeout")
        return final_step

    llm_step = mocker.patch.object(
        agent,
        "_llm_step",
        side_effect=fake_llm_step,
    )

    result = agent._get_validated_llm_step(
        user_query="test query",
        trace=[],
    )

    assert result == final_step
    assert [
        call.kwargs["is_validation_retry"]
        for call in llm_step.call_args_list
    ] == [False, False, True, True]


def test_unrelated_model_error_is_not_retried(mocker) -> None:
    agent = object.__new__(ReActAgent)
    agent.max_step_validation_retries = 1
    agent.max_model_timeout_retries = 1
    agent.model_timeout_retry_delay_seconds = 0
    llm_step = mocker.patch.object(
        agent,
        "_llm_step",
        side_effect=RuntimeError("programming error"),
    )

    with pytest.raises(RuntimeError, match="programming error"):
        agent._get_validated_llm_step(
            user_query="test query",
            trace=[],
        )

    llm_step.assert_called_once()


def test_negative_model_timeout_retry_limit_is_rejected(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with pytest.raises(
        ValueError,
        match="max_model_timeout_retries cannot be negative",
    ):
        ReActAgent(
            tool_registry=object(),
            max_model_timeout_retries=-1,
        )


@pytest.mark.parametrize(
    "retry_delay",
    [-1, float("inf"), float("nan")],
)
def test_invalid_model_timeout_retry_delay_is_rejected(
    monkeypatch,
    retry_delay: float,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with pytest.raises(
        ValueError,
        match=(
            "model_timeout_retry_delay_seconds must be finite "
            "and non-negative"
        ),
    ):
        ReActAgent(
            tool_registry=object(),
            model_timeout_retry_delay_seconds=retry_delay,
        )
