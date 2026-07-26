from tools.setup_registry import build_tool_registry
from tools.technical_analysis_tools import (
    TechnicalAnalysisInput,
    TechnicalAnalysisOutput,
    analyze_technical_indicators_tool,
)


def test_registry_includes_technical_analysis_tool() -> None:
    registry = build_tool_registry()

    tool = registry.get_tool("analyze_technical_indicators")

    assert tool.input_model is TechnicalAnalysisInput
    assert tool.output_model is TechnicalAnalysisOutput
    assert tool.func is analyze_technical_indicators_tool
    assert "analyze_technical_indicators" in registry.list_tool_names()
    assert "RSI" in tool.description
    assert "MACD" in tool.description


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