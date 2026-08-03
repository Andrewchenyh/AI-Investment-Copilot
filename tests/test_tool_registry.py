from unittest.mock import Mock

from pydantic import BaseModel

from tools.registry import RegisteredTool, ToolRegistry
from tools.setup_registry import build_tool_registry
from tools.technical_analysis_tools import (
    TechnicalAnalysisInput,
    TechnicalAnalysisOutput,
    analyze_technical_indicators_tool,
)


class CacheTestInput(BaseModel):
    ticker: str


class CacheTestOutput(BaseModel):
    ticker: str
    price: float


def build_cache_test_registry(
    mocker,
    *,
    tool_name: str = "get_current_price",
) -> tuple[ToolRegistry, Mock]:
    tool_function = mocker.Mock(
        return_value=CacheTestOutput(ticker="ORCL", price=170.0)
    )
    registry = ToolRegistry()
    registry.register(
        RegisteredTool(
            name=tool_name,
            description="Test tool",
            input_model=CacheTestInput,
            output_model=CacheTestOutput,
            func=tool_function,
        )
    )
    return registry, tool_function


def test_registry_includes_technical_analysis_tool() -> None:
    registry = build_tool_registry()

    tool = registry.get_tool("analyze_technical_indicators")

    assert tool.input_model is TechnicalAnalysisInput
    assert tool.output_model is TechnicalAnalysisOutput
    assert tool.func is analyze_technical_indicators_tool
    assert "analyze_technical_indicators" in registry.list_tool_names()
    assert "RSI" in tool.description
    assert "MACD" in tool.description


def test_market_tool_descriptions_match_their_data_contracts() -> None:
    registry = build_tool_registry()

    price_tool = registry.get_tool("get_current_price")
    volatility_tool = registry.get_tool("get_historical_volatility")

    assert "daily closing price" in price_tool.description
    assert "effective date" in price_tool.description
    assert "realized volatility" in volatility_tool.description


def test_technical_analysis_registry_execution_uses_cache(mocker) -> None:
    cached_result = {
        "ticker": "AAPL",
        "cached_for_test": True,
    }
    get_cached_result = mocker.patch(
        "tools.registry.get_cached_tool_result",
        return_value=cached_result,
    )
    set_cached_result = mocker.patch(
        "tools.registry.set_cached_tool_result"
    )

    registry = build_tool_registry()
    registered_tool = registry.get_tool("analyze_technical_indicators")
    tool_function = mocker.patch.object(registered_tool, "func")

    result = registry.execute(
        "analyze_technical_indicators",
        {"ticker": "AAPL"},
        trace_id="test-trace",
    )

    assert result == cached_result
    get_cached_result.assert_called_once_with(
        "analyze_technical_indicators",
        {"ticker": "AAPL"},
    )
    tool_function.assert_not_called()
    set_cached_result.assert_not_called()


def test_cache_read_failure_falls_back_to_tool_execution(mocker) -> None:
    get_cached_result = mocker.patch(
        "tools.registry.get_cached_tool_result",
        side_effect=ConnectionError("Redis unavailable"),
    )
    set_cached_result = mocker.patch(
        "tools.registry.set_cached_tool_result"
    )
    log_event = mocker.patch("tools.registry.log_event")
    registry, tool_function = build_cache_test_registry(mocker)

    result = registry.execute(
        "get_current_price",
        {"ticker": "ORCL"},
        trace_id="trace-read-failure",
    )

    assert result == {"ticker": "ORCL", "price": 170.0}
    get_cached_result.assert_called_once_with(
        "get_current_price",
        {"ticker": "ORCL"},
    )
    tool_function.assert_called_once_with(CacheTestInput(ticker="ORCL"))
    set_cached_result.assert_called_once()

    failure_logs = [
        call
        for call in log_event.call_args_list
        if call.args[1] == "tool_cache_read_failed"
    ]
    assert len(failure_logs) == 1
    assert failure_logs[0].kwargs["trace_id"] == "trace-read-failure"
    assert failure_logs[0].kwargs["error_type"] == "ConnectionError"
    assert failure_logs[0].kwargs["error_message"] == "Redis unavailable"


def test_cache_write_failure_does_not_discard_tool_result(mocker) -> None:
    mocker.patch(
        "tools.registry.get_cached_tool_result",
        return_value=None,
    )
    set_cached_result = mocker.patch(
        "tools.registry.set_cached_tool_result",
        side_effect=ConnectionError("Redis unavailable"),
    )
    log_event = mocker.patch("tools.registry.log_event")
    registry, tool_function = build_cache_test_registry(mocker)

    result = registry.execute(
        "get_current_price",
        {"ticker": "ORCL"},
        trace_id="trace-write-failure",
    )

    assert result == {"ticker": "ORCL", "price": 170.0}
    tool_function.assert_called_once_with(CacheTestInput(ticker="ORCL"))
    set_cached_result.assert_called_once()

    failure_logs = [
        call
        for call in log_event.call_args_list
        if call.args[1] == "tool_cache_write_failed"
    ]
    assert len(failure_logs) == 1
    assert failure_logs[0].kwargs["trace_id"] == "trace-write-failure"
    assert failure_logs[0].kwargs["error_type"] == "ConnectionError"
    assert failure_logs[0].kwargs["error_message"] == "Redis unavailable"


def test_non_cacheable_tool_executes_without_cache_access(mocker) -> None:
    get_cached_result = mocker.patch("tools.registry.get_cached_tool_result")
    set_cached_result = mocker.patch("tools.registry.set_cached_tool_result")
    registry, tool_function = build_cache_test_registry(
        mocker,
        tool_name="uncached_test_tool",
    )

    result = registry.execute(
        "uncached_test_tool",
        {"ticker": "ORCL"},
        trace_id="trace-uncached",
    )

    assert result == {"ticker": "ORCL", "price": 170.0}
    tool_function.assert_called_once_with(CacheTestInput(ticker="ORCL"))
    get_cached_result.assert_not_called()
    set_cached_result.assert_not_called()
