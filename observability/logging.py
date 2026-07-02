import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            payload.update(extra_fields)

        return json.dumps(payload, default=str)


def configure_json_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)


def summarize_payload(payload: Any, max_chars: int = 800) -> str:
    try:
        serialized = json.dumps(payload, default=str, sort_keys=True)
    except TypeError:
        serialized = str(payload)

    if len(serialized) <= max_chars:
        return serialized

    return serialized[:max_chars] + "...[truncated]"


def log_event(
    logger: logging.Logger,
    event: str,
    trace_id: str | None = None,
    **fields: Any,
) -> None:
    logger.info(
        event,
        extra={
            "extra_fields": {
                "event": event,
                "trace_id": trace_id,
                **fields,
            }
        },
    )