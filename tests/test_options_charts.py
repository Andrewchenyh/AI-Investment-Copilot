import pytest

from apps.options_charts import (
    NORMAL_QUOTE_COLOR,
    WIDE_QUOTE_COLOR,
    _quote_arrays,
    build_options_liquidity_figure,
)
from apps.options_liquidity import (
    OptionLiquidityPoint,
    OptionsLiquiditySnapshot,
)


def liquidity_point(
    *,
    contract_symbol: str,
    strike: float,
    quote_status: str,
    bid: float | None = None,
    ask: float | None = None,
    mid_price: float | None = None,
    bid_ask_spread: float | None = None,
    bid_ask_spread_pct: float | None = None,
    volume: int | None = None,
    open_interest: int | None = None,
) -> OptionLiquidityPoint:
    return OptionLiquidityPoint(
        contract_symbol=contract_symbol,
        strike=strike,
        last_price=None,
        bid=bid,
        ask=ask,
        mid_price=mid_price,
        bid_ask_spread=bid_ask_spread,
        bid_ask_spread_pct=bid_ask_spread_pct,
        quote_status=quote_status,
        volume=volume,
        open_interest=open_interest,
        implied_volatility=None,
        in_the_money=False,
    )


def liquidity_snapshot(
    *,
    points: tuple[OptionLiquidityPoint, ...] | None = None,
    ticker: str = "ORCL",
    source: str = "yfinance",
) -> OptionsLiquiditySnapshot:
    if points is None:
        points = (
            liquidity_point(
                contract_symbol="P150",
                strike=150.0,
                quote_status="unavailable",
                ask=2.0,
                volume=None,
                open_interest=0,
            ),
            liquidity_point(
                contract_symbol="P160",
                strike=160.0,
                quote_status="crossed",
                bid=2.1,
                ask=2.0,
                volume=10,
                open_interest=100,
            ),
            liquidity_point(
                contract_symbol="P170",
                strike=170.0,
                quote_status="wide",
                bid=1.0,
                ask=3.0,
                mid_price=2.0,
                bid_ask_spread=2.0,
                bid_ask_spread_pct=1.0,
                volume=20,
                open_interest=200,
            ),
            liquidity_point(
                contract_symbol="P180",
                strike=180.0,
                quote_status="normal",
                bid=1.9,
                ask=2.1,
                mid_price=2.0,
                bid_ask_spread=0.2,
                bid_ask_spread_pct=0.1,
                volume=0,
                open_interest=None,
            ),
        )

    return OptionsLiquiditySnapshot(
        ticker=ticker,
        expiration="2026-09-18",
        option_type="put",
        contract_count=len(points),
        selection_basis="nearest_to_target_strike:170.0",
        expiration_selection_basis="user_specified",
        source=source,
        points=points,
    )


def trace_by_name(figure, name: str):
    return next(
        trace
        for trace in figure.data
        if trace.name == name
    )


def test_options_figure_plots_only_usable_quotes() -> None:
    figure = build_options_liquidity_figure(
        liquidity_snapshot()
    )

    assert [trace.name for trace in figure.data] == [
        "Midpoint curve",
        "Normal quote",
        "Wide quote",
        "Open interest",
        "Volume",
    ]

    midpoint = trace_by_name(figure, "Midpoint curve")
    normal = trace_by_name(figure, "Normal quote")
    wide = trace_by_name(figure, "Wide quote")

    assert list(midpoint.x) == [170.0, 180.0]
    assert list(midpoint.y) == [2.0, 2.0]
    assert list(normal.x) == [180.0]
    assert list(normal.y) == [2.0]
    assert normal.marker.color == NORMAL_QUOTE_COLOR
    assert normal.marker.symbol == "circle"
    assert list(wide.x) == [170.0]
    assert list(wide.y) == [2.0]
    assert wide.marker.color == WIDE_QUOTE_COLOR
    assert wide.marker.symbol == "diamond"

    premium_strikes = {
        strike
        for trace in (midpoint, normal, wide)
        for strike in trace.x
    }
    assert premium_strikes == {170.0, 180.0}
    assert all(
        premium != 0
        for trace in (midpoint, normal, wide)
        for premium in trace.y
    )


def test_options_figure_uses_bid_ask_ranges_as_error_bars() -> None:
    figure = build_options_liquidity_figure(
        liquidity_snapshot()
    )

    normal = trace_by_name(figure, "Normal quote")
    wide = trace_by_name(figure, "Wide quote")

    assert list(normal.error_y.array) == pytest.approx([0.1])
    assert list(normal.error_y.arrayminus) == pytest.approx([0.1])
    assert normal.error_y.symmetric is False
    assert list(wide.error_y.array) == pytest.approx([1.0])
    assert list(wide.error_y.arrayminus) == pytest.approx([1.0])
    assert wide.error_y.symmetric is False


def test_options_figure_preserves_missing_and_zero_liquidity() -> None:
    figure = build_options_liquidity_figure(
        liquidity_snapshot()
    )

    open_interest = trace_by_name(figure, "Open interest")
    volume = trace_by_name(figure, "Volume")

    assert list(open_interest.x) == [150.0, 160.0, 170.0, 180.0]
    assert list(open_interest.y) == [0, 100, 200, None]
    assert list(volume.x) == [150.0, 160.0, 170.0, 180.0]
    assert list(volume.y) == [None, 10, 20, 0]


def test_options_figure_summarizes_quote_quality_and_layout() -> None:
    figure = build_options_liquidity_figure(
        liquidity_snapshot(
            ticker="<ORCL>",
            source="feed<script>",
        )
    )

    title = figure.layout.title.text
    assert "&lt;ORCL&gt;" in title
    assert "feed&lt;script&gt;" in title
    assert "Normal 1" in title
    assert "Wide 1" in title
    assert "Crossed 1" in title
    assert "Unavailable 1" in title
    assert figure.layout.height == 720
    assert figure.layout.barmode == "group"
    assert figure.layout.xaxis.matches == "x2"
    assert figure.layout.xaxis2.title.text == "Strike"
    assert figure.layout.yaxis.title.text == "Premium per share"
    assert figure.layout.yaxis2.title.text == "Contracts"
    assert figure.layout.legend.orientation == "h"


def test_options_figure_explains_sample_without_usable_quotes() -> None:
    snapshot = liquidity_snapshot(
        points=(
            liquidity_point(
                contract_symbol="P150",
                strike=150.0,
                quote_status="unavailable",
                ask=2.0,
                volume=None,
                open_interest=0,
            ),
            liquidity_point(
                contract_symbol="P160",
                strike=160.0,
                quote_status="crossed",
                bid=2.1,
                ask=2.0,
                volume=10,
                open_interest=100,
            ),
        )
    )

    figure = build_options_liquidity_figure(snapshot)

    assert [trace.name for trace in figure.data] == [
        "Open interest",
        "Volume",
    ]
    assert any(
        annotation.text
        == "No usable two-sided quotes in the selected contract sample."
        for annotation in figure.layout.annotations
    )
    assert "Crossed 1" in figure.layout.title.text
    assert "Unavailable 1" in figure.layout.title.text


@pytest.mark.parametrize(
    "missing_field",
    [
        "bid",
        "ask",
        "mid_price",
        "bid_ask_spread_pct",
    ],
)
def test_quote_arrays_rejects_incomplete_quoted_points(
    missing_field: str,
) -> None:
    values = {
        "bid": 1.9,
        "ask": 2.1,
        "mid_price": 2.0,
        "bid_ask_spread_pct": 0.1,
    }
    values[missing_field] = None
    malformed_point = liquidity_point(
        contract_symbol="P180",
        strike=180.0,
        quote_status="normal",
        bid=values["bid"],
        ask=values["ask"],
        mid_price=values["mid_price"],
        bid_ask_spread=0.2,
        bid_ask_spread_pct=values["bid_ask_spread_pct"],
    )

    with pytest.raises(
        ValueError,
        match="Quoted option points require",
    ):
        _quote_arrays([malformed_point])
