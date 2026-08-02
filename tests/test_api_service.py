import asyncio
import threading
from typing import Any
import asyncio
import json
import threading

import api.service as service


async def collect_stream(stream) -> list[str]:
    return [message async for message in stream]


def parse_sse_data(message: str) -> dict[str, Any]:
    data_line = next(
        line
        for line in message.splitlines()
        if line.startswith("data: ")
    )
    return json.loads(data_line.removeprefix("data: "))


def test_run_analysis_executes_agent_in_threadpool(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_ask(query: str, trace_id: str) -> dict[str, Any]:
        raise AssertionError("fake_ask should be passed to the threadpool wrapper")

    async def fake_run_in_threadpool(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs

        return {
            "status": "success",
            "answer": "Grounded answer",
            "trace": [],
        }

    monkeypatch.setattr(service.agent, "ask", fake_ask)
    monkeypatch.setattr(
        service,
        "run_in_threadpool",
        fake_run_in_threadpool,
    )

    response = asyncio.run(service.run_analysis("Analyze ORCL"))

    assert captured["func"] is fake_ask
    assert captured["args"] == ("Analyze ORCL",)
    assert captured["kwargs"]["trace_id"] == response.trace_id
    assert response.status == "success"
    assert response.answer == "Grounded answer"


def test_run_comparison_executes_agent_in_threadpool(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_ask(query: str, trace_id: str) -> dict[str, Any]:
        raise AssertionError("fake_ask should be passed to the threadpool wrapper")

    async def fake_run_in_threadpool(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs

        return {
            "status": "success",
            "answer": "ORCL and MSFT comparison",
            "trace": [],
        }

    monkeypatch.setattr(service.agent, "ask", fake_ask)
    monkeypatch.setattr(
        service,
        "run_in_threadpool",
        fake_run_in_threadpool,
    )

    tickers = ["ORCL", "MSFT"]
    question = "Compare them"
    expected_query = service.build_comparison_query(tickers, question)

    response = asyncio.run(
        service.run_comparison(
            tickers=tickers,
            question=question,
        )
    )

    assert captured["func"] is fake_ask
    assert captured["args"] == (expected_query,)
    assert captured["kwargs"]["trace_id"] == response.trace_id
    assert response.status == "success"
    assert response.answer == "ORCL and MSFT comparison"


def test_stream_analysis_iterates_agent_in_threadpool(monkeypatch) -> None:
    event_thread_ids: list[int] = []
    event_loop_thread_id = threading.get_ident()

    def fake_run_with_events(query: str, trace_id: str):
        event_thread_ids.append(threading.get_ident())
        yield {
            "event": "start",
            "data": {
                "query": query,
            },
        }

    monkeypatch.setattr(
        service.agent,
        "run_with_events",
        fake_run_with_events,
    )

    messages = asyncio.run(
        collect_stream(service.stream_analysis("Analyze ORCL"))
    )

    assert event_thread_ids
    assert event_thread_ids[0] != event_loop_thread_id
    assert len(messages) == 1
    assert messages[0].startswith("event: start\n")


def test_stream_comparison_iterates_agent_in_threadpool(monkeypatch) -> None:
    event_thread_ids: list[int] = []
    event_loop_thread_id = threading.get_ident()

    def fake_run_with_events(query: str, trace_id: str):
        event_thread_ids.append(threading.get_ident())
        yield {
            "event": "start",
            "data": {
                "query": query,
            },
        }

    monkeypatch.setattr(
        service.agent,
        "run_with_events",
        fake_run_with_events,
    )

    messages = asyncio.run(
        collect_stream(
            service.stream_comparison(
                tickers=["ORCL", "MSFT"],
                question="Compare them",
            )
        )
    )

    assert event_thread_ids
    assert event_thread_ids[0] != event_loop_thread_id
    assert len(messages) == 1
    assert messages[0].startswith("event: start\n")


def test_run_analysis_saves_history_in_threadpool(monkeypatch) -> None:
    event_loop_thread_id = threading.get_ident()
    history_thread_ids: list[int] = []
    saved: dict[str, Any] = {}

    def fake_ask(query: str, trace_id: str) -> dict[str, Any]:
        return {
            "status": "success",
            "answer": "Grounded answer",
            "trace": [],
        }

    def fake_save_history_item(
        session_id: str,
        item: dict[str, Any],
    ) -> None:
        history_thread_ids.append(threading.get_ident())
        saved["session_id"] = session_id
        saved["item"] = item

    monkeypatch.setattr(service.agent, "ask", fake_ask)
    monkeypatch.setattr(
        service,
        "save_history_item",
        fake_save_history_item,
    )

    response = asyncio.run(
        service.run_analysis(
            "Analyze ORCL",
            session_id="session-123",
        )
    )

    assert history_thread_ids
    assert history_thread_ids[0] != event_loop_thread_id
    assert saved["session_id"] == "session-123"
    assert saved["item"]["trace_id"] == response.trace_id
    assert saved["item"]["answer"] == "Grounded answer"


def test_stream_analysis_saves_history_in_threadpool(monkeypatch) -> None:
    event_loop_thread_id = threading.get_ident()
    history_thread_ids: list[int] = []
    saved: dict[str, Any] = {}

    def fake_run_with_events(query: str, trace_id: str):
        yield {
            "event": "final_answer",
            "data": {
                "status": "success",
                "answer": "Streamed answer",
                "trace": [],
            },
        }

    def fake_save_history_item(
        session_id: str,
        item: dict[str, Any],
    ) -> None:
        history_thread_ids.append(threading.get_ident())
        saved["session_id"] = session_id
        saved["item"] = item

    monkeypatch.setattr(
        service.agent,
        "run_with_events",
        fake_run_with_events,
    )
    monkeypatch.setattr(
        service,
        "save_history_item",
        fake_save_history_item,
    )

    messages = asyncio.run(
        collect_stream(
            service.stream_analysis(
                "Analyze ORCL",
                session_id="session-123",
            )
        )
    )

    assert history_thread_ids
    assert history_thread_ids[0] != event_loop_thread_id
    assert saved["session_id"] == "session-123"
    assert saved["item"]["answer"] == "Streamed answer"
    assert messages[0].startswith("event: final_answer\n")


def test_run_analysis_succeeds_when_history_save_fails(monkeypatch) -> None:
    def fake_ask(query: str, trace_id: str) -> dict[str, Any]:
        return {
            "status": "success",
            "answer": "Grounded answer",
            "trace": [],
        }

    def fail_history_save(
        session_id: str,
        item: dict[str, Any],
    ) -> None:
        raise ConnectionError("Redis unavailable")

    logged_events: list[dict[str, Any]] = []

    def capture_log_event(
        logger,
        event: str,
        trace_id: str | None = None,
        **fields: Any,
    ) -> None:
        logged_events.append(
            {
                "event": event,
                "trace_id": trace_id,
                **fields,
            }
        )

    monkeypatch.setattr(service.agent, "ask", fake_ask)
    monkeypatch.setattr(
        service,
        "save_history_item",
        fail_history_save,
    )
    monkeypatch.setattr(
        service,
        "log_event",
        capture_log_event,
    )

    response = asyncio.run(
        service.run_analysis(
            "Analyze ORCL",
            session_id="session-123",
        )
    )

    assert response.status == "success"
    assert response.answer == "Grounded answer"
    history_failure = next(
        event
        for event in logged_events
        if event["event"] == "history_save_failed"
    )

    assert history_failure["trace_id"] == response.trace_id
    assert history_failure["session_id"] == "session-123"
    assert history_failure["error_type"] == "ConnectionError"
    assert history_failure["error_message"] == "Redis unavailable"


def test_stream_analysis_emits_final_answer_when_history_save_fails(
    monkeypatch,
) -> None:
    def fake_run_with_events(query: str, trace_id: str):
        yield {
            "event": "final_answer",
            "data": {
                "status": "success",
                "answer": "Streamed answer",
                "trace": [],
            },
        }

    def fail_history_save(
        session_id: str,
        item: dict[str, Any],
    ) -> None:
        raise ConnectionError("Redis unavailable")

    monkeypatch.setattr(
        service.agent,
        "run_with_events",
        fake_run_with_events,
    )
    monkeypatch.setattr(
        service,
        "save_history_item",
        fail_history_save,
    )

    messages = asyncio.run(
        collect_stream(
            service.stream_analysis(
                "Analyze ORCL",
                session_id="session-123",
            )
        )
    )

    assert len(messages) == 1
    assert messages[0].startswith("event: final_answer\n")
    assert '"status": "success"' in messages[0]
    assert '"answer": "Streamed answer"' in messages[0]


def test_stream_analysis_converts_unexpected_exception_to_error_event(
    monkeypatch,
) -> None:
    def failing_run_with_events(query: str, trace_id: str):
        yield {
            "event": "start",
            "data": {
                "query": query,
            },
        }
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(
        service.agent,
        "run_with_events",
        failing_run_with_events,
    )

    messages = asyncio.run(
        collect_stream(service.stream_analysis("Analyze ORCL"))
    )

    assert len(messages) == 2
    assert messages[0].startswith("event: start\n")
    assert messages[1].startswith("event: error\n")

    error_data = parse_sse_data(messages[1])

    assert error_data["status"] == "error"
    assert error_data["trace_id"]
    assert error_data["message"] == (
        "The analysis stream failed unexpectedly. "
        "Please retry the request."
    )
    assert "sensitive internal detail" not in messages[1]
    assert "trace" not in error_data


def test_stream_comparison_converts_unexpected_exception_to_error_event(
    monkeypatch,
) -> None:
    def failing_run_with_events(query: str, trace_id: str):
        yield {
            "event": "start",
            "data": {
                "query": query,
            },
        }
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(
        service.agent,
        "run_with_events",
        failing_run_with_events,
    )

    messages = asyncio.run(
        collect_stream(
            service.stream_comparison(
                tickers=["ORCL", "MSFT"],
                question="Compare them",
            )
        )
    )

    assert len(messages) == 2
    assert messages[-1].startswith("event: error\n")

    error_data = parse_sse_data(messages[-1])

    assert error_data["status"] == "error"
    assert error_data["trace_id"]
    assert error_data["message"] == (
        "The comparison stream failed unexpectedly. "
        "Please retry the request."
    )
    assert "sensitive internal detail" not in messages[-1]
    assert "trace" not in error_data