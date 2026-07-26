from tools.basic_market_tools import (
    CurrentPriceInput,
    CurrentPriceOutput,
    HistoricalVolatilityInput,
    HistoricalVolatilityOutput,
    get_current_price_tool,
    get_historical_volatility_tool,
)

from tools.technical_analysis_tools import (
    TechnicalAnalysisInput,
    TechnicalAnalysisOutput,
    analyze_technical_indicators_tool,
)

from tools.options_tools import (
    CashSecuredPutInput,
    CashSecuredPutOutput,
    OptionsChainInput,
    OptionsChainOutput,
    analyze_cash_secured_put_tool,
    get_options_chain_tool,
)

from tools.registry import RegisteredTool, ToolRegistry


def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        RegisteredTool(
            name="analyze_technical_indicators",
            description="Compute the latest daily technical-indicator snapshot for a "
            "stock using SMA, EMA, RSI, MACD, and Bollinger Bands.",
            input_model=TechnicalAnalysisInput,
            output_model=TechnicalAnalysisOutput,
            func=analyze_technical_indicators_tool,
        )
    )

    registry.register(
        RegisteredTool(
            name="get_current_price",
            description="Fetch the most recent available stock price for a ticker.",
            input_model=CurrentPriceInput,
            output_model=CurrentPriceOutput,
            func=get_current_price_tool,
        )
    )

    registry.register(
        RegisteredTool(
            name="get_historical_volatility",
            description="Compute annualized realized volatility from recent daily closing prices.",
            input_model=HistoricalVolatilityInput,
            output_model=HistoricalVolatilityOutput,
            func=get_historical_volatility_tool,
        )
    )

    registry.register(
        RegisteredTool(
            name="get_options_chain",
            description="Fetch a limited set of option contracts for a ticker, expiration, and option type.",
            input_model=OptionsChainInput,
            output_model=OptionsChainOutput,
            func=get_options_chain_tool,
        )
    )

    registry.register(
        RegisteredTool(
            name="analyze_cash_secured_put",
            description="Analyze a candidate short cash-secured put using spot price, strike, expiration, and premium.",
            input_model=CashSecuredPutInput,
            output_model=CashSecuredPutOutput,
            func=analyze_cash_secured_put_tool,
        )
    )

    return registry
