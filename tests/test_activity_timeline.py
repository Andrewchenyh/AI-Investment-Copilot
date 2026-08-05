import pytest

from apps.activity_timeline import describe_activity_event


@pytest.mark.parametrize(
    ("event_name", "event_data", "expected_description"),
    [
        (
            "start",
            {"trace_id": "trace-123"},
            "Analysis started.",
        ),
        (
            "tool_call",
            {
                "step": 2,
                "tool_name": "get_options_chain",
            },
            "Step 2: Running `get_options_chain`.",
        ),
        (
            "tool_result",
            {
                "tool_name": "get_options_chain",
                "success": True,
            },
            "`get_options_chain` completed successfully.",
        ),
        (
            "final_answer",
            {"answer": "Complete."},
            "Analysis completed.",
        ),
        (
            "error",
            {"message": "Analysis failed."},
            "Analysis stopped before completion.",
        ),
    ],
)
def test_describe_activity_event_returns_observable_status(
    event_name: str,
    event_data: dict,
    expected_description: str,
) -> None:
    assert (
        describe_activity_event(event_name, event_data)
        == expected_description
    )


def test_describe_activity_event_reports_final_synthesis_without_thought(
) -> None:
    private_thought = "Unstructured model-generated reasoning."

    description = describe_activity_event(
        "thought",
        {
            "step": 3,
            "action_type": "final_answer",
            "thought": private_thought,
        },
    )

    assert description == "Step 3: Synthesizing the grounded response."
    assert private_thought not in description


def test_describe_activity_event_hides_tool_call_thought() -> None:
    description = describe_activity_event(
        "thought",
        {
            "step": 1,
            "action_type": "tool_call",
            "thought": "I should inspect ORCL's latest price.",
        },
    )

    assert description is None


def test_describe_activity_event_hides_raw_tool_failure() -> None:
    raw_error = "Provider secret or implementation detail"

    description = describe_activity_event(
        "tool_result",
        {
            "tool_name": "get_current_price",
            "success": False,
            "error": raw_error,
        },
    )

    assert description == (
        "`get_current_price` could not complete; "
        "the agent is adjusting its approach."
    )
    assert raw_error not in description


def test_describe_activity_event_ignores_unknown_event() -> None:
    assert describe_activity_event("unknown", {}) is None
