import json

import pytest

from apps.sse_client import (
    SSEProtocolError,
    parse_sse_lines,
    require_terminal_event,
    validate_event_payloads,
)


def test_parse_sse_lines_decodes_event() -> None:
    lines = [
        "event: start",
        'data: {"trace_id": "trace-123"}',
        "",
    ]

    events = list(parse_sse_lines(lines))

    assert events == [("start", {"trace_id": "trace-123"})]


def test_parse_sse_lines_flushes_final_event_without_blank_line() -> None:
    lines = [
        "event: final_answer",
        'data: {"answer": "Complete"}',
    ]

    events = list(parse_sse_lines(lines))

    assert events == [("final_answer", {"answer": "Complete"})]


def test_parse_sse_lines_handles_multiple_events_and_ignores_comments() -> None:
    lines = [
        ": keepalive",
        "retry: 5000",
        "event: thought\r",
        'data: {"step": 1}\r',
        "\r",
        "event: tool_result",
        'data: {"success": true}',
        "",
    ]

    events = list(parse_sse_lines(lines))

    assert events == [
        ("thought", {"step": 1}),
        ("tool_result", {"success": True}),
    ]


def test_parse_sse_lines_joins_multiline_data() -> None:
    lines = [
        "event: thought",
        "data: {",
        'data: "step": 1,',
        'data: "thought": "Inspecting market data"',
        "data: }",
        "",
    ]

    events = list(parse_sse_lines(lines))

    assert events == [
        (
            "thought",
            {
                "step": 1,
                "thought": "Inspecting market data",
            },
        )
    ]


def test_parse_sse_lines_rejects_data_without_event_name() -> None:
    lines = ['data: {"status": "success"}', ""]

    with pytest.raises(
        SSEProtocolError,
        match="without an event name",
    ):
        list(parse_sse_lines(lines))


def test_parse_sse_lines_wraps_malformed_json_error() -> None:
    lines = ["event: error", "data: not-json", ""]

    with pytest.raises(
        SSEProtocolError,
        match="contained invalid JSON",
    ) as exc_info:
        list(parse_sse_lines(lines))

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


@pytest.mark.parametrize(
    "payload",
    ["[]", '"answer"', "null"],
)
def test_parse_sse_lines_rejects_non_object_payloads(
    payload: str,
) -> None:
    lines = ["event: final_answer", f"data: {payload}", ""]

    with pytest.raises(
        SSEProtocolError,
        match="payload must be a JSON object",
    ):
        list(parse_sse_lines(lines))


def test_require_terminal_event_accepts_final_answer() -> None:
    events = [
        ("start", {"trace_id": "trace-123"}),
        ("final_answer", {"answer": "Complete"}),
    ]

    validated_events = list(require_terminal_event(events))

    assert validated_events == events


def test_require_terminal_event_accepts_error() -> None:
    events = [
        ("start", {"trace_id": "trace-123"}),
        ("error", {"message": "Analysis failed."}),
    ]

    validated_events = list(require_terminal_event(events))

    assert validated_events == events


def test_require_terminal_event_yields_before_detecting_incomplete_stream(
) -> None:
    events = [
        ("start", {"trace_id": "trace-123"}),
        ("thought", {"step": 1}),
    ]
    validated_events = require_terminal_event(events)

    assert next(validated_events) == events[0]
    assert next(validated_events) == events[1]

    with pytest.raises(
        SSEProtocolError,
        match="ended without a terminal event",
    ):
        next(validated_events)


def test_require_terminal_event_rejects_empty_stream() -> None:
    with pytest.raises(
        SSEProtocolError,
        match="ended without a terminal event",
    ):
        list(require_terminal_event([]))


@pytest.mark.parametrize(
    ("event_name", "payload"),
    [
        ("start", {"trace_id": "trace-123"}),
        (
            "thought",
            {
                "trace_id": "trace-123",
                "step": 1,
                "thought": "Inspecting market data.",
                "action_type": "tool_call",
            },
        ),
        (
            "tool_call",
            {
                "trace_id": "trace-123",
                "tool_name": "get_current_price",
                "tool_args_json": '{"ticker": "ORCL"}',
            },
        ),
        (
            "tool_result",
            {
                "trace_id": "trace-123",
                "tool_name": "get_current_price",
                "success": True,
                "observation": {"price": 170.0},
            },
        ),
        (
            "final_answer",
            {
                "trace_id": "trace-123",
                "answer": "Analysis complete.",
                "trace": [],
            },
        ),
        (
            "error",
            {
                "trace_id": "trace-123",
                "message": "Analysis failed.",
            },
        ),
    ],
)
def test_validate_event_payloads_accepts_supported_events(
    event_name: str,
    payload: dict,
) -> None:
    events = [(event_name, payload)]

    validated_events = list(validate_event_payloads(events))

    assert validated_events == events


def test_validate_event_payloads_accepts_workflow_correction_thought() -> None:
    events = [
        (
            "thought",
            {
                "trace_id": "trace-123",
                "step": 2,
                "thought": (
                    "Final answer deferred because cash-secured-put "
                    "analysis is still required for: MSFT."
                ),
                "action_type": "workflow_correction",
            },
        )
    ]

    assert list(validate_event_payloads(events)) == events


def test_validate_event_payloads_rejects_missing_required_field() -> None:
    events = [
        (
            "thought",
            {
                "trace_id": "trace-123",
                "thought": "Inspecting market data.",
                "action_type": "tool_call",
            },
        )
    ]

    with pytest.raises(
        SSEProtocolError,
        match="missing required field 'step'",
    ):
        list(validate_event_payloads(events))


def test_validate_event_payloads_rejects_incorrect_field_type() -> None:
    events = [
        (
            "final_answer",
            {
                "trace_id": "trace-123",
                "answer": "Analysis complete.",
                "trace": {},
            },
        )
    ]

    with pytest.raises(
        SSEProtocolError,
        match="field 'trace' must be list",
    ):
        list(validate_event_payloads(events))


def test_validate_event_payloads_does_not_treat_bool_as_int() -> None:
    events = [
        (
            "thought",
            {
                "trace_id": "trace-123",
                "step": True,
                "thought": "Inspecting market data.",
                "action_type": "tool_call",
            },
        )
    ]

    with pytest.raises(
        SSEProtocolError,
        match="field 'step' must be int",
    ):
        list(validate_event_payloads(events))


def test_validate_event_payloads_rejects_unsupported_event() -> None:
    events = [("heartbeat", {"trace_id": "trace-123"})]

    with pytest.raises(
        SSEProtocolError,
        match="unsupported SSE event 'heartbeat'",
    ):
        list(validate_event_payloads(events))
