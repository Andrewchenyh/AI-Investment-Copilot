import asyncio
import threading
from typing import Any

import api.app as api_app


def test_get_history_reads_redis_in_threadpool(monkeypatch) -> None:
    event_loop_thread_id = threading.get_ident()
    history_thread_ids: list[int] = []
    captured: dict[str, Any] = {}

    def fake_get_history_items(session_id: str) -> list[dict[str, Any]]:
        history_thread_ids.append(threading.get_ident())
        captured["session_id"] = session_id

        return [
            {
                "query": "Analyze ORCL",
                "status": "success",
                "trace_id": "trace-123",
                "answer": "Grounded answer",
                "message": None,
                "trace": [],
            }
        ]

    monkeypatch.setattr(
        api_app,
        "get_history_items",
        fake_get_history_items,
    )

    response = asyncio.run(
        api_app.get_history(
            session_id="session-123",
            _="test-key",
        )
    )

    assert history_thread_ids
    assert history_thread_ids[0] != event_loop_thread_id
    assert captured["session_id"] == "session-123"
    assert response.session_id == "session-123"
    assert len(response.items) == 1
    assert response.items[0].query == "Analyze ORCL"