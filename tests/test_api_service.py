import asyncio
from typing import Any

import api.service as service


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