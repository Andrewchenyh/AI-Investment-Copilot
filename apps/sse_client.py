import json
from collections.abc import Iterable, Iterator
from typing import Any


SSEEvent = tuple[str, dict[str, Any]]


TERMINAL_EVENT_NAMES = frozenset(
    {
        "final_answer",
        "error",
    }
)


_EVENT_REQUIRED_FIELD_TYPES: dict[
    str,
    dict[str, type[Any]],
] = {
    "start": {
        "trace_id": str,
    },
    "thought": {
        "trace_id": str,
        "step": int,
        "thought": str,
        "action_type": str,
    },
    "tool_call": {
        "trace_id": str,
        "tool_name": str,
        "tool_args_json": str,
    },
    "tool_result": {
        "trace_id": str,
        "tool_name": str,
        "success": bool,
        "observation": dict,
    },
    "final_answer": {
        "trace_id": str,
        "answer": str,
        "trace": list,
    },
    "error": {
        "trace_id": str,
        "message": str,
    },
}


class SSEProtocolError(ValueError):
    """Raised when an SSE event contains malformed or unexpected data."""


def _decode_event(
    event_name: str | None,
    data_lines: list[str],
) -> SSEEvent | None:
    if not data_lines:
        return None

    if not event_name:
        raise SSEProtocolError(
            "Received SSE data without an event name."
        )

    raw_data = "\n".join(data_lines)

    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise SSEProtocolError(
            f"Event '{event_name}' contained invalid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise SSEProtocolError(
            f"Event '{event_name}' payload must be a JSON object."
        )

    return event_name, payload


def parse_sse_lines(
    lines: Iterable[str],
) -> Iterator[SSEEvent]:
    current_event: str | None = None
    current_data_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip("\r")

        if line == "":
            decoded_event = _decode_event(
                current_event,
                current_data_lines,
            )
            if decoded_event is not None:
                yield decoded_event

            current_event = None
            current_data_lines = []
            continue

        if line.startswith(":"):
            # SSE comment or keepalive.
            continue

        field, separator, value = line.partition(":")
        if not separator:
            continue

        if value.startswith(" "):
            value = value[1:]

        if field == "event":
            current_event = value
        elif field == "data":
            current_data_lines.append(value)

    # Flush a final valid event even when the stream closes without
    # the blank separator required by the usual SSE framing.
    decoded_event = _decode_event(
        current_event,
        current_data_lines,
    )
    if decoded_event is not None:
        yield decoded_event


def validate_event_payloads(
    events: Iterable[SSEEvent],
) -> Iterator[SSEEvent]:
    for event_name, payload in events:
        required_fields = _EVENT_REQUIRED_FIELD_TYPES.get(
            event_name
        )

        if required_fields is None:
            raise SSEProtocolError(
                f"Received unsupported SSE event '{event_name}'."
            )

        for field_name, expected_type in required_fields.items():
            if field_name not in payload:
                raise SSEProtocolError(
                    f"Event '{event_name}' is missing required "
                    f"field '{field_name}'."
                )

            value = payload[field_name]
            if type(value) is not expected_type:
                raise SSEProtocolError(
                    f"Event '{event_name}' field '{field_name}' "
                    f"must be {expected_type.__name__}."
                )

        yield event_name, payload


def require_terminal_event(
    events: Iterable[SSEEvent],
) -> Iterator[SSEEvent]:
    terminal_event_seen = False

    for event_name, payload in events:
        if event_name in TERMINAL_EVENT_NAMES:
            terminal_event_seen = True

        yield event_name, payload

    if not terminal_event_seen:
        raise SSEProtocolError(
            "The SSE stream ended without a terminal event."
        )
