import json
from api.schemas import AnalyzeResponse
from agents.react_agent import ReActAgent
from tools.setup_registry import build_tool_registry


tool_registry = build_tool_registry()
agent = ReActAgent(tool_registry=tool_registry, max_steps=6)


async def run_analysis(query: str) -> AnalyzeResponse:
    result = agent.ask(query)

    return AnalyzeResponse(
        status=result["status"],
        answer=result.get("answer"),
        message=result.get("message"),
        trace=result["trace"],
    )


async def stream_analysis(query: str):
    """
    Stream analysis events as Server-Sent Events (SSE).
    """
    for event in agent.run_with_events(query):
        sse_message = (
            f"event: {event['event']}\n"
            f"data: {json.dumps(event['data'])}\n\n"
        )
        yield sse_message