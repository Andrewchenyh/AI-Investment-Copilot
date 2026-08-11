import pytest

from agents.react_agent import (
    DEFAULT_AGENT_RUNTIME_SECONDS,
    DEFAULT_MODEL_REQUEST_TIMEOUT_MS,
    ReActAgent,
)
from agents.schemas import AgentStep, ToolCall, ToolObservation


def make_agent(step: AgentStep, max_steps: int = 1) -> ReActAgent:
    agent = object.__new__(ReActAgent)
    agent.max_steps = max_steps
    agent.max_runtime_seconds = DEFAULT_AGENT_RUNTIME_SECONDS
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
    assert agent.max_runtime_seconds == DEFAULT_AGENT_RUNTIME_SECONDS


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


@pytest.mark.parametrize("max_runtime_seconds", [0, -1, float("inf")])
def test_agent_rejects_invalid_runtime_budget(
    monkeypatch,
    mocker,
    max_runtime_seconds: float,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client_constructor = mocker.patch("agents.react_agent.genai.Client")

    with pytest.raises(
        ValueError,
        match="max_runtime_seconds must be finite and positive",
    ):
        ReActAgent(
            tool_registry=object(),
            max_runtime_seconds=max_runtime_seconds,
        )

    client_constructor.assert_not_called()


def test_runtime_budget_can_expire_before_first_model_call(mocker) -> None:
    agent = make_agent(
        AgentStep(
            thought="Finished.",
            action_type="final_answer",
            final_answer="Answer.",
        )
    )
    get_step = mocker.Mock(wraps=agent._get_validated_llm_step)
    agent._get_validated_llm_step = get_step
    mocker.patch(
        "agents.react_agent.time.monotonic",
        side_effect=[0.0, DEFAULT_AGENT_RUNTIME_SECONDS],
    )

    events = list(agent.run_with_events("query", trace_id="trace-123"))

    assert [event["event"] for event in events] == ["start", "error"]
    assert events[0]["data"]["max_runtime_seconds"] == (
        DEFAULT_AGENT_RUNTIME_SECONDS
    )
    assert "runtime limit" in events[-1]["data"]["message"]
    assert events[-1]["data"]["trace"] == []
    get_step.assert_not_called()


def test_runtime_budget_prevents_tool_call_after_model_step(mocker) -> None:
    agent = make_agent(
        AgentStep(
            thought="I need price data.",
            action_type="tool_call",
            tool_call=ToolCall(
                tool_name="get_current_price",
                tool_args_json='{"ticker": "ORCL"}',
            ),
        )
    )
    execute_tool = mocker.patch.object(agent, "_execute_tool")
    mocker.patch(
        "agents.react_agent.time.monotonic",
        side_effect=[0.0, 0.0, DEFAULT_AGENT_RUNTIME_SECONDS],
    )

    events = list(agent.run_with_events("query", trace_id="trace-123"))

    assert [event["event"] for event in events] == [
        "start",
        "thought",
        "error",
    ]
    assert events[-1]["data"]["trace"][0]["action_type"] == "tool_call"
    execute_tool.assert_not_called()


def test_final_answer_is_accepted_after_soft_runtime_deadline(mocker) -> None:
    final_step = AgentStep(
        thought="Finished.",
        action_type="final_answer",
        final_answer="Grounded answer.",
    )
    agent = make_agent(final_step)
    monotonic = mocker.patch(
        "agents.react_agent.time.monotonic",
        side_effect=[0.0, 0.0, DEFAULT_AGENT_RUNTIME_SECONDS],
    )

    def finish_after_deadline(user_query, trace):
        monotonic()
        return final_step

    agent._get_validated_llm_step = finish_after_deadline

    events = list(agent.run_with_events("query", trace_id="trace-123"))

    assert events[-1]["event"] == "final_answer"
    assert events[-1]["data"]["status"] == "success"
    assert events[-1]["data"]["answer"] == "Grounded answer."


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


def test_agent_enforces_explicit_strike_before_tool_execution(
    mocker,
) -> None:
    agent = make_agent(
        AgentStep(
            thought="I need the options chain.",
            action_type="tool_call",
            tool_call=ToolCall(
                tool_name="get_options_chain",
                tool_args_json=(
                    '{"ticker": "SNDK", "target_strike": 1130}'
                ),
            ),
        )
    )
    execute_tool = mocker.patch.object(
        agent,
        "_execute_tool",
        return_value=ToolObservation(
            tool_name="get_options_chain",
            tool_args={
                "ticker": "SNDK",
                "target_strike": 1000.0,
            },
            result={},
            success=True,
        ),
    )

    events = list(
        agent.run_with_events(
            "Write a 1000 cash-secured put on SNDK.",
            trace_id="trace-123",
        )
    )

    execute_tool.assert_called_once_with(
        tool_name="get_options_chain",
        tool_args={
            "ticker": "SNDK",
            "target_strike": 1000.0,
        },
        trace_id="trace-123",
    )
    tool_result = next(
        event
        for event in events
        if event["event"] == "tool_result"
    )
    assert tool_result["data"]["tool_args"] == {
        "ticker": "SNDK",
        "target_strike": 1000.0,
    }


def test_agent_defers_csp_final_answer_until_analysis_attempt(
    mocker,
) -> None:
    steps = [
        AgentStep(
            thought="I need an options contract.",
            action_type="tool_call",
            tool_call=ToolCall(
                tool_name="get_options_chain",
                tool_args_json='{"ticker": "MSFT"}',
            ),
        ),
        AgentStep(
            thought="I can answer from the chain.",
            action_type="final_answer",
            final_answer="Premature answer.",
        ),
        AgentStep(
            thought="I need the deterministic CSP metrics.",
            action_type="tool_call",
            tool_call=ToolCall(
                tool_name="analyze_cash_secured_put",
                tool_args_json=(
                    '{"ticker": "MSFT", "strike": 500, '
                    '"expiration": "2026-08-19"}'
                ),
            ),
        ),
        AgentStep(
            thought="The analysis is complete.",
            action_type="final_answer",
            final_answer="Grounded CSP answer.",
        ),
    ]
    agent = make_agent(steps[0], max_steps=4)
    get_step = mocker.patch.object(
        agent,
        "_get_validated_llm_step",
        side_effect=steps,
    )
    mocker.patch.object(
        agent,
        "_execute_tool",
        side_effect=[
            ToolObservation(
                tool_name="get_options_chain",
                tool_args={"ticker": "MSFT"},
                result={"contracts": [{"strike": 500.0}]},
                success=True,
            ),
            ToolObservation(
                tool_name="analyze_cash_secured_put",
                tool_args={
                    "ticker": "MSFT",
                    "strike": 500,
                    "expiration": "2026-08-19",
                },
                result={"break_even": 494.45},
                success=True,
            ),
        ],
    )

    events = list(
        agent.run_with_events(
            "Should I write a cash-secured put on MSFT?",
            trace_id="trace-123",
        )
    )

    corrections = [
        event
        for event in events
        if event["event"] == "thought"
        and event["data"]["action_type"] == "workflow_correction"
    ]
    assert len(corrections) == 1
    assert "MSFT" in corrections[0]["data"]["thought"]
    assert events[-1]["event"] == "final_answer"
    assert events[-1]["data"]["answer"] == "Grounded CSP answer."
    assert get_step.call_count == 4
