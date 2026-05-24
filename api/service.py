from api.schemas import AnalyzeResponse
from agents.react_agent import ReActAgent
from tools.setup_registry import build_tool_registry


tool_registry = build_tool_registry()
agent = ReActAgent(tool_registry=tool_registry, max_steps=6)


async def run_analysis(query: str) -> AnalyzeResponse:
    """
    Run the investment copilot analysis and normalize the result
    into the API response schema.

    This is async so the API layer is ready for future streaming
    and other async I/O patterns.
    """
    result = agent.ask(query)

    return AnalyzeResponse(
        status=result["status"],
        answer=result.get("answer"),
        message=result.get("message"),
        trace=result["trace"],
    )