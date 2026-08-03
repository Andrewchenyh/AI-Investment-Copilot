import pandas as pd
import pytest
from pydantic import ValidationError

from tools.options_tools import (
    CashSecuredPutInput,
    OptionsChainInput,
    _calculate_quote_metrics,
    _coerce_optional_bool,
    _coerce_optional_non_negative_float,
    _coerce_optional_non_negative_int,
    _prepare_option_contracts,
    analyze_cash_secured_put_tool,
    get_options_chain_tool,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("not-a-number", None),
        (float("nan"), None),
        (float("inf"), None),
        (float("-inf"), None),
        (-0.01, None),
        (0, 0.0),
        ("2.5", 2.5),
    ],
)
def test_optional_non_negative_float_coercion(
    value: object,
    expected: float | None,
) -> None:
    assert _coerce_optional_non_negative_float(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (-1, None),
        (1.5, None),
        (0, 0),
        ("12", 12),
    ],
)
def test_optional_non_negative_int_coercion(
    value: object,
    expected: int | None,
) -> None:
    assert _coerce_optional_non_negative_int(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        ("FALSE", False),
        ("1", True),
        ("0", False),
        (None, None),
        (float("nan"), None),
        ("unknown", None),
        (2, None),
    ],
)
def test_optional_bool_coercion(
    value: object,
    expected: bool | None,
) -> None:
    assert _coerce_optional_bool(value) is expected


@pytest.mark.parametrize(
    (
        "bid",
        "ask",
        "expected_mid",
        "expected_spread",
        "expected_spread_pct",
        "expected_status",
    ),
    [
        (1.95, 2.05, 2.0, 0.1, 0.05, "normal"),
        (1.0, 3.0, 2.0, 2.0, 1.0, "wide"),
        (2.1, 2.0, None, None, None, "crossed"),
        (None, 2.0, None, None, None, "unavailable"),
        (0.0, 2.0, None, None, None, "unavailable"),
    ],
)
def test_calculate_quote_metrics(
    bid: float | None,
    ask: float | None,
    expected_mid: float | None,
    expected_spread: float | None,
    expected_spread_pct: float | None,
    expected_status: str,
) -> None:
    metrics = _calculate_quote_metrics(bid, ask)

    if expected_mid is None:
        assert metrics.mid_price is None
        assert metrics.bid_ask_spread is None
        assert metrics.bid_ask_spread_pct is None
    else:
        assert metrics.mid_price == pytest.approx(expected_mid)
        assert metrics.bid_ask_spread == pytest.approx(expected_spread)
        assert metrics.bid_ask_spread_pct == pytest.approx(
            expected_spread_pct
        )

    assert metrics.quote_status == expected_status


def test_prepare_option_contracts_filters_rows_and_adds_liquidity_columns() -> None:
    option_df = pd.DataFrame(
        {
            "contractSymbol": [" P170 ", "", "P180", None, "P190"],
            "strike": [170, 175, "invalid", 185, 0],
        }
    )

    prepared = _prepare_option_contracts(
        option_df,
        require_contract_symbol=True,
    )

    assert prepared["contractSymbol"].tolist() == ["P170"]
    assert prepared["strike"].tolist() == [170.0]
    assert prepared["openInterest"].isna().all()
    assert prepared["volume"].isna().all()


def test_prepare_option_contracts_rejects_missing_required_column() -> None:
    option_df = pd.DataFrame({"strike": [170.0]})

    with pytest.raises(
        ValueError,
        match="missing required columns: contractSymbol",
    ):
        _prepare_option_contracts(
            option_df,
            require_contract_symbol=True,
        )


def test_get_options_chain_tool_rejects_all_invalid_contracts(mocker) -> None:
    mock_engine = mocker.patch("tools.options_tools.MarketDataEngine")
    mock_engine.return_value.get_option_expirations.return_value = ["2026-06-05"]
    mock_engine.return_value.get_options_chain.return_value = {
        "puts": pd.DataFrame(
            {
                "contractSymbol": ["", "P170", None],
                "strike": [170, "invalid", 180],
            }
        ),
        "calls": pd.DataFrame(),
    }

    with pytest.raises(ValueError, match="No valid put contracts found"):
        get_options_chain_tool(
            OptionsChainInput(
                ticker="ORCL",
                expiration="2026-06-05",
                target_strike=170,
            )
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
    selected_contract = result.contracts[0]
    assert selected_contract.mid_price == pytest.approx(2.0)
    assert selected_contract.bid_ask_spread == pytest.approx(0.2)
    assert selected_contract.bid_ask_spread_pct == pytest.approx(0.1)
    assert selected_contract.quote_status == "normal"


def test_get_options_chain_tool_preserves_unavailable_numeric_fields(mocker) -> None:
    mock_engine = mocker.patch("tools.options_tools.MarketDataEngine")
    mock_engine.return_value.get_option_expirations.return_value = ["2026-06-05"]
    mock_engine.return_value.get_options_chain.return_value = {
        "puts": pd.DataFrame(
            {
                "contractSymbol": ["P170"],
                "strike": [170.0],
                "lastPrice": [None],
                "bid": [float("nan")],
                "ask": [float("inf")],
                "volume": [-1],
                "openInterest": [None],
                "impliedVolatility": ["invalid"],
                "inTheMoney": [None],
            }
        ),
        "calls": pd.DataFrame(),
    }

    result = get_options_chain_tool(
        OptionsChainInput(
            ticker="ORCL",
            expiration="2026-06-05",
            target_strike=170,
            limit=1,
        )
    )

    contract = result.contracts[0]
    assert contract.last_price is None
    assert contract.bid is None
    assert contract.ask is None
    assert contract.volume is None
    assert contract.open_interest is None
    assert contract.implied_volatility is None
    assert contract.in_the_money is None
    assert contract.mid_price is None
    assert contract.bid_ask_spread is None
    assert contract.bid_ask_spread_pct is None
    assert contract.quote_status == "unavailable"


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


def test_cash_secured_put_input_rejects_zero_premium() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CashSecuredPutInput(
            ticker="ORCL",
            strike=180,
            expiration="2099-01-01",
            premium=0,
        )

    premium_error = exc_info.value.errors()[0]
    assert premium_error["loc"] == ("premium",)
    assert premium_error["type"] == "greater_than"


def test_cash_secured_put_rejects_unusable_market_premium(mocker) -> None:
    mock_engine = mocker.patch("tools.options_tools.MarketDataEngine")
    mock_engine.return_value.get_price_history.return_value = pd.DataFrame(
        {"Close": [188.16]}
    )
    mock_engine.return_value.get_options_chain.return_value = {
        "puts": pd.DataFrame(
            {
                "strike": [180.0],
                "lastPrice": [0.0],
                "bid": [0.0],
                "ask": [0.0],
                "volume": [10],
                "openInterest": [100],
            }
        )
    }

    with pytest.raises(ValueError, match="No usable premium quote found"):
        analyze_cash_secured_put_tool(
            CashSecuredPutInput(
                ticker="ORCL",
                strike=180,
                expiration="2099-01-01",
            )
        )
