import json

import pytest

from apps.sse_client import SSEProtocolError, parse_sse_lines


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
