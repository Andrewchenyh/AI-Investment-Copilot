import asyncio
import threading
from typing import Any

import api.service as service


async def collect_stream(stream) -> list[str]:
    return [message async for message in stream]


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
