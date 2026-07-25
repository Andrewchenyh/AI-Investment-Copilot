import asyncio

import pytest
from fastapi import HTTPException

import api.app as api_app
from api.schemas import AnalyzeRequest, CompareRequest


def test_analyze_does_not_expose_internal_exception(monkeypatch) -> None:
    async def fail_analysis(query: str, session_id: str | None = None):
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(api_app, "run_analysis", fail_analysis)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            api_app.analyze_json(
                AnalyzeRequest(query="Analyze ORCL"),
                _="test-key",
                __=None,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Analysis request failed."
    assert "sensitive" not in str(exc_info.value.detail)


def test_compare_does_not_expose_internal_exception(monkeypatch) -> None:
    async def fail_comparison(
        tickers: list[str],
        question: str,
        session_id: str | None = None,
    ):
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(api_app, "run_comparison", fail_comparison)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            api_app.compare_json(
                CompareRequest(
                    tickers=["ORCL", "MSFT"],
                    question="Compare them",
                ),
                _="test-key",
                __=None,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Comparison request failed."
    assert "sensitive" not in str(exc_info.value.detail)
