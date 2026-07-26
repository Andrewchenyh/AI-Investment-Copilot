from typing import Any, Callable, Generic, TypeVar
from pydantic import BaseModel
import logging
import time

from observability.logging import log_event, summarize_payload
from tools.cache import get_cached_tool_result, set_cached_tool_result
from observability.metrics import metrics

logger = logging.getLogger(__name__)

ToolInput = TypeVar("ToolInput", bound=BaseModel)
ToolOutput = TypeVar("ToolOutput", bound=BaseModel)

class RegisteredTool(Generic[ToolInput, ToolOutput]):
    def __init__(
        self,
        name: str,
        description: str,
        input_model: type[ToolInput],
        output_model: type[ToolOutput],
        func: Callable[[ToolInput], ToolOutput],
    ):
        self.name = name
        self.description = description
        self.input_model = input_model
        self.output_model = output_model
        self.func = func

    def describe(self) -> str:
        return (
            f"Tool: {self.name}\n"
            f"Description: {self.description}\n"
            f"Input schema: {self.input_model.model_json_schema()}\n"
            f"Output schema: {self.output_model.model_json_schema()}\n"
        )


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, RegisteredTool[Any, Any]] = {}

    def register(
        self,
        tool: RegisteredTool[Any, Any],
    ) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get_tool(
        self,
        tool_name: str,
    ) -> RegisteredTool[Any, Any]:
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool '{tool_name}'.")
        return self._tools[tool_name]

    def execute(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        tool = self.get_tool(tool_name)

        cacheable_tools = {
            "get_current_price",
            "get_historical_volatility",
            "get_options_chain",
            "analyze_technical_indicators"
        }

        try:
            if tool_name in cacheable_tools:
                cached_result = get_cached_tool_result(tool_name, tool_args)
                if cached_result is not None:
                    latency_ms = (time.perf_counter() - start) * 1000
                    log_event(
                        logger,
                        "tool_execution",
                        trace_id=trace_id,
                        tool_name=tool_name,
                        success=True,
                        cache_hit=True,
                        latency_ms=round(latency_ms, 2),
                        input_summary=summarize_payload(tool_args),
                        output_summary=summarize_payload(cached_result),
                    )
                    metrics.record_tool_execution(
                        latency_ms=latency_ms,
                        success=True,
                        cache_hit=True,
                    )
                    return cached_result

            validated_input = tool.input_model.model_validate(tool_args)
            result = tool.func(validated_input)

            if not isinstance(result, tool.output_model):
                result = tool.output_model.model_validate(result)

            result_dict = result.model_dump()

            if tool_name in cacheable_tools:
                set_cached_tool_result(tool_name, tool_args, result_dict, ttl_seconds=300)

            latency_ms = (time.perf_counter() - start) * 1000
            log_event(
                logger,
                "tool_execution",
                trace_id=trace_id,
                tool_name=tool_name,
                success=True,
                cache_hit=False,
                latency_ms=round(latency_ms, 2),
                input_summary=summarize_payload(tool_args),
                output_summary=summarize_payload(result_dict),
            )
            metrics.record_tool_execution(
                latency_ms=latency_ms,
                success=True,
                cache_hit=False,
            )

            return result_dict

        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            log_event(
                logger,
                "tool_execution",
                trace_id=trace_id,
                tool_name=tool_name,
                success=False,
                cache_hit=False,
                latency_ms=round(latency_ms, 2),
                input_summary=summarize_payload(tool_args),
                error=str(exc),
            )
            metrics.record_tool_execution(
                latency_ms=latency_ms,
                success=False,
                cache_hit=False,
            )

            raise


    def describe_tools(self) -> str:
        return "\n\n".join(tool.describe() for tool in self._tools.values())

    def list_tool_names(self) -> list[str]:
        return list(self._tools.keys())
