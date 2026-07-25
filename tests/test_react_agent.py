from agents.react_agent import ReActAgent
from agents.schemas import AgentStep, ToolCall


def make_agent(step: AgentStep, max_steps: int = 1) -> ReActAgent:
    agent = object.__new__(ReActAgent)
    agent.max_steps = max_steps
    agent._get_validated_llm_step = (lambda user_query, trace: step)
    return agent


def terminal_event(agent: ReActAgent) -> dict:
    events = list(agent.run_with_events("test query", trace_id="trace-123"))
    return events[-1]


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
