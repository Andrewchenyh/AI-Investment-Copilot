import pandas as pd
import pytest

from tools.options_tools import (
    CashSecuredPutInput,
    OptionsChainInput,
    analyze_cash_secured_put_tool,
    get_options_chain_tool,
)


def test_get_options_chain_tool_selects_contracts_near_target_strike(mocker) -> None:
    mock_engine = mocker.patch("tools.options_tools.MarketDataEngine")
    mock_engine.return_value.get_option_expirations.return_value = ["2026-06-05"]
    mock_engine.return_value.get_options_chain.return_value = {
        "puts": pd.DataFrame(
            {
                "contractSymbol": ["P160", "P170", "P180"],
                "strike": [160.0, 170.0, 180.0],
                "lastPrice": [1.0, 2.0, 3.0],
                "bid": [0.9, 1.9, 2.9],
                "ask": [1.1, 2.1, 3.1],
                "volume": [10, 20, 30],
                "openInterest": [100, 200, 300],
                "impliedVolatility": [0.4, 0.5, 0.6],
                "inTheMoney": [False, False, False],
            }
        ),
        "calls": pd.DataFrame(),
    }

    result = get_options_chain_tool(
        OptionsChainInput(
            ticker="ORCL",
            expiration="2026-06-05",
            option_type="put",
            target_strike=171,
            limit=2,
        )
    )

    assert result.ticker == "ORCL"
    assert result.expiration == "2026-06-05"
    assert result.option_type == "put"
    assert result.contract_count == 2
    assert result.selection_basis == "nearest_to_target_strike:171.0"
    assert [contract.strike for contract in result.contracts] == [170.0, 180.0]


def test_analyze_cash_secured_put_with_explicit_premium(mocker) -> None:
    mock_engine = mocker.patch("tools.options_tools.MarketDataEngine")
    mock_engine.return_value.get_price_history.return_value = pd.DataFrame(
        {
            "Close": [188.16],
        }
    )

    result = analyze_cash_secured_put_tool(
        CashSecuredPutInput(
            ticker="orcl",
            strike=180,
            expiration="2099-01-01",
            premium=3.30,
        )
    )

    assert result.ticker == "ORCL"
    assert result.spot_price == 188.16
    assert result.strike == 180
    assert result.premium == 3.30
    assert result.break_even_price == 176.70
    assert result.max_profit_dollars == 330.0
    assert result.cash_required_dollars == 18000
    assert result.simple_return == pytest.approx(0.0183333333)