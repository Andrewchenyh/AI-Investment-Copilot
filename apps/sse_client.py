import json
from collections.abc import Iterable, Iterator
from typing import Any


SSEEvent = tuple[str, dict[str, Any]]


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
