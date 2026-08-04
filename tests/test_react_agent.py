import pytest

from agents.react_agent import (
    DEFAULT_MODEL_REQUEST_TIMEOUT_MS,
    ReActAgent,
)
from agents.schemas import AgentStep, ToolCall


def make_agent(step: AgentStep, max_steps: int = 1) -> ReActAgent:
    agent = object.__new__(ReActAgent)
    agent.max_steps = max_steps
    agent._get_validated_llm_step = (lambda user_query, trace: step)
    return agent


def terminal_event(agent: ReActAgent) -> dict:
    events = list(agent.run_with_events("test query", trace_id="trace-123"))
    return events[-1]


def test_agent_configures_default_model_request_timeout(
    monkeypatch,
    mocker,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client_constructor = mocker.patch("agents.react_agent.genai.Client")

    agent = ReActAgent(tool_registry=object())

    client_constructor.assert_called_once()
    call_kwargs = client_constructor.call_args.kwargs
    assert call_kwargs["api_key"] == "test-key"
    assert call_kwargs["http_options"].timeout == (
        DEFAULT_MODEL_REQUEST_TIMEOUT_MS
    )
    assert agent.model_request_timeout_ms == DEFAULT_MODEL_REQUEST_TIMEOUT_MS


def test_agent_rejects_non_positive_model_request_timeout(
    monkeypatch,
    mocker,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client_constructor = mocker.patch("agents.react_agent.genai.Client")

    with pytest.raises(
        ValueError,
        match="model_request_timeout_ms must be positive",
    ):
        ReActAgent(
            tool_registry=object(),
            model_request_timeout_ms=0,
        )

    client_constructor.assert_not_called()


def test_runtime_guard_rejects_empty_final_answer() -> None:
    agent = make_agent(
        AgentStep.model_construct(
            thought="Analysis is complete.",
            action_type="final_answer",
            tool_call=None,
            final_answer="   ",
        )
    )

    event = terminal_event(agent)

    assert event["event"] == "error"
    assert event["data"]["status"] == "error"
    assert event["data"]["trace_id"] == "trace-123"
    assert "did not provide any answer text" in event["data"]["message"]


def test_runtime_guard_rejects_missing_tool_details() -> None:
    agent = make_agent(
        AgentStep.model_construct(
            thought="I need market data.",
            action_type="tool_call",
            tool_call=None,
            final_answer=None,
        )
    )

    event = terminal_event(agent)

    assert event["event"] == "error"
    assert event["data"]["status"] == "error"
    assert "did not provide the required tool details" in event["data"]["message"]


def test_max_steps_returns_a_useful_error() -> None:
    agent = make_agent(
        AgentStep(
            thought="I need market data.",
            action_type="tool_call",
            tool_call=ToolCall(
                tool_name="get_current_price",
                tool_args_json="not-json",
            ),
        ),
        max_steps=1,
    )

    event = terminal_event(agent)

    assert event["event"] == "error"
    assert event["data"]["status"] == "error"
    assert "maximum of 1 steps" in event["data"]["message"]
