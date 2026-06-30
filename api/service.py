import json
from api.schemas import AnalyzeResponse, CompareResponse
from agents.react_agent import ReActAgent
from tools.setup_registry import build_tool_registry
from api.history import save_history_item
from uuid import uuid4

tool_registry = build_tool_registry()
agent = ReActAgent(tool_registry=tool_registry, max_steps=10)

async def run_analysis(query: str, session_id: str | None = None) -> AnalyzeResponse:
    trace_id = str(uuid4())

    result = agent.ask(query, trace_id=trace_id)

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

    result = agent.ask(comparison_query, trace_id=trace_id)

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