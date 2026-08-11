from dataclasses import FrozenInstanceError

import pytest

from apps.options_liquidity import (
    OptionLiquidityPoint,
    OptionsLiquiditySnapshot,
    build_options_liquidity_snapshot,
    format_selection_basis,
)


def option_contract(
    *,
    contract_symbol: str,
    strike: float,
    bid: float | None = 1.90,
    ask: float | None = 2.10,
    mid_price: float | None = 2.00,
    bid_ask_spread: float | None = 0.20,
    bid_ask_spread_pct: float | None = 0.10,
    quote_status: str = "normal",
    volume: int | None = 20,
    open_interest: int | None = 200,
    expiration: str = "2026-09-18",
    option_type: str = "put",
) -> dict:
    return {
        "contract_symbol": contract_symbol,
        "strike": strike,
        "last_price": 1.95,
        "bid": bid,
        "ask": ask,
        "mid_price": mid_price,
        "bid_ask_spread": bid_ask_spread,
        "bid_ask_spread_pct": bid_ask_spread_pct,
        "quote_status": quote_status,
        "volume": volume,
        "open_interest": open_interest,
        "implied_volatility": 0.32,
        "in_the_money": False,
        "expiration": expiration,
        "option_type": option_type,
    }


def options_observation(
    **overrides: object,
) -> dict:
    contracts = [
        option_contract(
            contract_symbol="P180",
            strike=180.0,
            volume=0,
            open_interest=None,
        ),
        option_contract(
            contract_symbol="P170",
            strike=170.0,
            bid=1.0,
            ask=3.0,
            mid_price=2.0,
            bid_ask_spread=2.0,
            bid_ask_spread_pct=1.0,
            quote_status="wide",
        ),
        option_contract(
            contract_symbol="P160",
            strike=160.0,
            bid=2.1,
            ask=2.0,
            mid_price=None,
            bid_ask_spread=None,
            bid_ask_spread_pct=None,
            quote_status="crossed",
        ),
        option_contract(
            contract_symbol="P150",
            strike=150.0,
            bid=None,
            ask=2.0,
            mid_price=None,
            bid_ask_spread=None,
            bid_ask_spread_pct=None,
            quote_status="unavailable",
            volume=None,
            open_interest=0,
        ),
    ]
    observation = {
        "ticker": " orcl ",
        "expiration": "2026-09-18",
        "option_type": "put",
        "contract_count": len(contracts),
        "selection_basis": "nearest_to_target_strike:170.0",
        "expiration_selection_basis": "user_specified",
        "contracts": contracts,
        "source": "yfinance",
    }
    observation.update(overrides)
    return observation


def successful_options_result(
    **overrides: object,
) -> dict:
    return {
        "tool_name": "get_options_chain",
        "success": True,
        "observation": options_observation(
            **overrides
        ),
    }


def test_build_options_liquidity_snapshot_maps_and_sorts_contracts() -> None:
    snapshot = build_options_liquidity_snapshot(
        [successful_options_result()]
    )

    assert snapshot is not None
    assert snapshot.ticker == "ORCL"
    assert snapshot.expiration == "2026-09-18"
    assert snapshot.option_type == "put"
    assert snapshot.contract_count == 4
    assert snapshot.selection_basis == (
        "nearest_to_target_strike:170.0"
    )
    assert snapshot.expiration_selection_basis == "user_specified"
    assert snapshot.source == "yfinance"
    assert [point.strike for point in snapshot.points] == [
        150.0,
        160.0,
        170.0,
        180.0,
    ]
    assert [point.quote_status for point in snapshot.points] == [
        "unavailable",
        "crossed",
        "wide",
        "normal",
    ]

    unavailable, _, _, normal = snapshot.points
    assert unavailable.volume is None
    assert unavailable.open_interest == 0
    assert normal.volume == 0
    assert normal.open_interest is None


def test_build_options_liquidity_snapshot_uses_latest_successful_result(
) -> None:
    trace = [
        successful_options_result(ticker="MSFT"),
        successful_options_result(ticker="ORCL"),
        {
            "tool_name": "get_options_chain",
            "success": False,
            "observation": options_observation(
                ticker="AAPL"
            ),
        },
    ]

    snapshot = build_options_liquidity_snapshot(trace)

    assert snapshot is not None
    assert snapshot.ticker == "ORCL"


def test_build_options_liquidity_snapshot_returns_none_without_chain() -> None:
    trace = [
        {"step": 1, "thought": "Inspecting data."},
        {
            "tool_name": "get_options_chain",
            "success": False,
            "observation": options_observation(),
        },
    ]

    assert build_options_liquidity_snapshot(trace) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"contract_count": True},
        {"contract_count": 3},
        {"expiration": "not-a-date"},
        {"ticker": "   "},
        {"option_type": "future"},
        {"selection_basis": "   "},
        {"expiration_selection_basis": ""},
        {"source": ""},
        {"contracts": []},
        {"contracts": None},
    ],
)
def test_build_options_liquidity_snapshot_rejects_invalid_chain(
    overrides: dict,
) -> None:
    assert build_options_liquidity_snapshot(
        [successful_options_result(**overrides)]
    ) is None


@pytest.mark.parametrize(
    "contracts",
    [
        [
            option_contract(
                contract_symbol="P170",
                strike=170.0,
            ),
            option_contract(
                contract_symbol="P170",
                strike=180.0,
            ),
        ],
        [
            option_contract(
                contract_symbol="P170",
                strike=170.0,
                expiration="2026-10-16",
            )
        ],
        [
            option_contract(
                contract_symbol="P170",
                strike=170.0,
                option_type="call",
            )
        ],
        [
            option_contract(
                contract_symbol="",
                strike=170.0,
            )
        ],
        [
            option_contract(
                contract_symbol="P170",
                strike=float("inf"),
            )
        ],
    ],
)
def test_build_options_liquidity_snapshot_rejects_invalid_contracts(
    contracts: list[dict],
) -> None:
    assert build_options_liquidity_snapshot(
        [
            successful_options_result(
                contract_count=len(contracts),
                contracts=contracts,
            )
        ]
    ) is None


@pytest.mark.parametrize(
    "contract",
    [
        option_contract(
            contract_symbol="P170",
            strike=170.0,
            mid_price=2.25,
        ),
        option_contract(
            contract_symbol="P170",
            strike=170.0,
            quote_status="wide",
        ),
        option_contract(
            contract_symbol="P170",
            strike=170.0,
            bid=1.0,
            ask=3.0,
            mid_price=2.0,
            bid_ask_spread=2.0,
            bid_ask_spread_pct=1.0,
            quote_status="normal",
        ),
        option_contract(
            contract_symbol="P170",
            strike=170.0,
            bid=2.1,
            ask=2.0,
            mid_price=2.05,
            bid_ask_spread=0.1,
            bid_ask_spread_pct=0.05,
            quote_status="crossed",
        ),
        option_contract(
            contract_symbol="P170",
            strike=170.0,
            mid_price=None,
            bid_ask_spread=None,
            bid_ask_spread_pct=None,
            quote_status="unavailable",
        ),
    ],
)
def test_build_options_liquidity_snapshot_rejects_inconsistent_quote(
    contract: dict,
) -> None:
    assert build_options_liquidity_snapshot(
        [
            successful_options_result(
                contract_count=1,
                contracts=[contract],
            )
        ]
    ) is None


def test_build_options_liquidity_snapshot_does_not_use_stale_fallback(
) -> None:
    trace = [
        successful_options_result(ticker="MSFT"),
        successful_options_result(contract_count=3),
    ]

    assert build_options_liquidity_snapshot(trace) is None


def test_options_liquidity_snapshot_is_immutable() -> None:
    snapshot = build_options_liquidity_snapshot(
        [successful_options_result()]
    )

    assert snapshot is not None
    assert isinstance(snapshot.points, tuple)
    assert isinstance(snapshot.points[0], OptionLiquidityPoint)

    with pytest.raises(FrozenInstanceError):
        setattr(snapshot, "ticker", "MSFT")

    with pytest.raises(FrozenInstanceError):
        setattr(snapshot.points[0], "strike", 200.0)

    assert isinstance(snapshot, OptionsLiquiditySnapshot)


@pytest.mark.parametrize(
    ("selection_basis", "expected"),
    [
        (
            "liquidity",
            "liquidity ranking",
        ),
        (
            "nearest_to_target_strike:170.0",
            "proximity to the requested strike ($170.00)",
        ),
        (
            "nearest_to_reference_price:147.02000427246094",
            "proximity to the current share price ($147.02)",
        ),
        (
            "  nearest_to_reference_price:147.5  ",
            "proximity to the current share price ($147.50)",
        ),
        (
            "future_selection_method",
            "future selection method",
        ),
    ],
)
def test_format_selection_basis_returns_human_readable_label(
    selection_basis: str,
    expected: str,
) -> None:
    assert format_selection_basis(selection_basis) == expected


@pytest.mark.parametrize(
    "raw_value",
    [
        "unknown",
        "nan",
        "inf",
        "-inf",
    ],
)
def test_format_selection_basis_hides_invalid_reference_value(
    raw_value: str,
) -> None:
    assert format_selection_basis(
        f"nearest_to_reference_price:{raw_value}"
    ) == "proximity to the current share price"
