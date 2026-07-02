import json
from uuid import uuid4
import logging
import time
from api.schemas import AnalyzeResponse, CompareResponse
from agents.react_agent import ReActAgent
from tools.setup_registry import build_tool_registry
from api.history import save_history_item
from observability.logging import log_event

tool_registry = build_tool_registry()
agent = ReActAgent(tool_registry=tool_registry, max_steps=10)
logger = logging.getLogger(__name__)

async def run_analysis(query: str, session_id: str | None = None) -> AnalyzeResponse:
    trace_id = str(uuid4())

    start = time.perf_counter()
    log_event(logger, "analysis_request_started", trace_id=trace_id, query=query)

    result = agent.ask(query, trace_id=trace_id)

    latency_ms = (time.perf_counter() - start) * 1000
    log_event(
        logger,
        "analysis_request_finished",
        trace_id=trace_id,
        status=result["status"],
        latency_ms=round(latency_ms, 2),
    )

    if session_id:
        save_history_item(
            session_id=session_id,
            item={
                "query": query,
                "status": result["status"],
                "trace_id": trace_id,
                "answer": result.get("answer"),
                "message": result.get("message"),
                "trace": result["trace"],
            },
        )

    return AnalyzeResponse(
        status=result["status"],
        trace_id=trace_id,
        answer=result.get("answer"),
        message=result.get("message"),
        trace=result["trace"],
    )


async def stream_analysis(query: str, session_id: str | None = None):
    trace_id = str(uuid4())
    start = time.perf_counter()
    for event in agent.run_with_events(query, trace_id=trace_id):
        event["data"]["trace_id"] = trace_id

        if session_id and event["event"] in {"final_answer", "error"}:
            result = event["data"]
            save_history_item(
                session_id=session_id,
                item={
                    "query": query,
                    "status": result["status"],
                    "trace_id": trace_id,
                    "answer": result.get("answer"),
                    "message": result.get("message"),
                    "trace": result["trace"],
                },
            )

        sse_message = (
            f"event: {event['event']}\n"
            f"data: {json.dumps(event['data'])}\n\n"
        )
        yield sse_message


def build_comparison_query(tickers: list[str], question: str) -> str:
    normalized_tickers = [ticker.upper().strip() for ticker in tickers]

    return (
        f"Compare these tickers: {', '.join(normalized_tickers)}.\n"
        f"User comparison question: {question}\n"
        "Analyze each ticker using the same criteria before making the comparison."
    )
    
    
async def run_comparison(
    tickers: list[str],
    question: str,
    session_id: str | None = None,
) -> CompareResponse:
    trace_id = str(uuid4())
    comparison_query = build_comparison_query(tickers, question)

    start = time.perf_counter()
    log_event(logger, "comparison_request_started", trace_id=trace_id, query=comparison_query)

    result = agent.ask(comparison_query, trace_id=trace_id)

    latency_ms = (time.perf_counter() - start) * 1000
    log_event(
        logger,
        "comparison_request_finished",
        trace_id=trace_id,
        status=result["status"],
        latency_ms=round(latency_ms, 2),
    )

    if session_id:
        save_history_item(
            session_id=session_id,
            item={
                "query": comparison_query,
                "status": result["status"],
                "trace_id": trace_id,
                "answer": result.get("answer"),
                "message": result.get("message"),
                "trace": result["trace"],
            },
        )

    return CompareResponse(
        status=result["status"],
        trace_id=trace_id,
        answer=result.get("answer"),
        message=result.get("message"),
        trace=result["trace"],
    )
    

async def stream_comparison(
    tickers: list[str],
    question: str,
    session_id: str | None = None,
):
    trace_id = str(uuid4())
    comparison_query = build_comparison_query(tickers, question)

    for event in agent.run_with_events(comparison_query, trace_id=trace_id):
        event["data"]["trace_id"] = trace_id

        if session_id and event["event"] in {"final_answer", "error"}:
            result = event["data"]
            save_history_item(
                session_id=session_id,
                item={
                    "query": comparison_query,
                    "status": result["status"],
                    "trace_id": trace_id,
                    "answer": result.get("answer"),
                    "message": result.get("message"),
                    "trace": result["trace"],
                },
            )

        sse_message = (
            f"event: {event['event']}\n"
            f"data: {json.dumps(event['data'])}\n\n"
        )
        yield sse_message