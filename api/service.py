import json
from api.schemas import AnalyzeResponse
from agents.react_agent import ReActAgent
from tools.setup_registry import build_tool_registry
from api.history import save_history_item

tool_registry = build_tool_registry()
agent = ReActAgent(tool_registry=tool_registry, max_steps=6)

async def run_analysis(query: str, session_id: str | None = None) -> AnalyzeResponse:
    result = agent.ask(query)
    if session_id:
        save_history_item(
            session_id=session_id,
            item={
                "query": query,
                "status": result["status"],
                "answer": result.get("answer"),
                "message": result.get("message"),
                "trace": result["trace"],
            },
        )
    return AnalyzeResponse(
        status=result["status"],
        answer=result.get("answer"),
        message=result.get("message"),
        trace=result["trace"],
    )


async def stream_analysis(query: str, session_id: str | None = None):
    """
    Stream analysis events as Server-Sent Events (SSE).
    """
    for event in agent.run_with_events(query):
        if session_id and event["event"] in {"final_answer", "error"}:
            result = event["data"]
            save_history_item(
                session_id=session_id,
                item={
                    "query": query,
                    "status": result["status"],
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
