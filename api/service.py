import json
from uuid import uuid4
import logging
import time
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool
from api.schemas import AnalyzeResponse, CompareResponse
from agents.react_agent import ReActAgent
from tools.setup_registry import build_tool_registry
from api.history import save_history_item
from observability.logging import log_event
from observability.metrics import metrics

tool_registry = build_tool_registry()
agent = ReActAgent(tool_registry=tool_registry, max_steps=10)
logger = logging.getLogger(__name__)

async def run_analysis(query: str, session_id: str | None = None) -> AnalyzeResponse:
    trace_id = str(uuid4())

    start = time.perf_counter()
    log_event(logger, "analysis_request_started", trace_id=trace_id, query=query)

    result = await run_in_threadpool(
        agent.ask,
        query,
        trace_id=trace_id,
    )

    latency_ms = (time.perf_counter() - start) * 1000
    metrics.record_request_latency(latency_ms)
    
    log_event(
        logger,
        "analysis_request_finished",
        trace_id=trace_id,
        status=result["status"],
        latency_ms=round(latency_ms, 2),
    )

    if session_id:
        await run_in_threadpool(
            save_history_item,
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
    log_event(
        logger,
        "analysis_stream_started",
        trace_id=trace_id,
        query=query,
    )

    try:
        async for event in iterate_in_threadpool(
            agent.run_with_events(query, trace_id=trace_id)
        ):
            event["data"]["trace_id"] = trace_id

            if session_id and event["event"] in {"final_answer", "error"}:
                result = event["data"]
                await run_in_threadpool(
                    save_history_item,
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

            if event["event"] in {"final_answer", "error"}:
                result = event["data"]
                latency_ms = (time.perf_counter() - start) * 1000
                metrics.record_request_latency(latency_ms)

                log_event(
                    logger,
                    "analysis_stream_finished",
                    trace_id=trace_id,
                    status=result["status"],
                    latency_ms=round(latency_ms, 2),
                )

            sse_message = (
                f"event: {event['event']}\n"
                f"data: {json.dumps(event['data'])}\n\n"
            )
            yield sse_message


    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000

        log_event(
            logger,
            "analysis_stream_failed",
            trace_id=trace_id,
            error_type=type(e).__name__,
            error_message=str(e),
            latency_ms=round(latency_ms, 2),
        )

        raise


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

    result = await run_in_threadpool(
        agent.ask,
        comparison_query,
        trace_id=trace_id,
    )

    latency_ms = (time.perf_counter() - start) * 1000
    metrics.record_request_latency(latency_ms)
    
    log_event(
        logger,
        "comparison_request_finished",
        trace_id=trace_id,
        status=result["status"],
        latency_ms=round(latency_ms, 2),
    )

    if session_id:
        await run_in_threadpool(
            save_history_item,
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

    start = time.perf_counter()
    log_event(
        logger,
        "comparison_stream_started",
        trace_id=trace_id,
        query=comparison_query,
        tickers=[ticker.upper().strip() for ticker in tickers],
    )

    try:
        async for event in iterate_in_threadpool(
            agent.run_with_events(comparison_query, trace_id=trace_id)
        ):
            event["data"]["trace_id"] = trace_id

            if session_id and event["event"] in {"final_answer", "error"}:
                result = event["data"]
                await run_in_threadpool(
                    save_history_item,
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

            if event["event"] in {"final_answer", "error"}:
                result = event["data"]
                latency_ms = (time.perf_counter() - start) * 1000
                metrics.record_request_latency(latency_ms)

                log_event(
                    logger,
                    "comparison_stream_finished",
                    trace_id=trace_id,
                    status=result["status"],
                    latency_ms=round(latency_ms, 2),
                )

            sse_message = (
                f"event: {event['event']}\n"
                f"data: {json.dumps(event['data'])}\n\n"
            )
            yield sse_message

    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000

        log_event(
            logger,
            "comparison_stream_failed",
            trace_id=trace_id,
            error_type=type(e).__name__,
            error_message=str(e),
            latency_ms=round(latency_ms, 2),
        )

        raise