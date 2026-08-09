from apps.charts import (
    BREAK_EVEN_COLOR,
    PAYOFF_LINE_COLOR,
    SPOT_COLOR,
    STRIKE_COLOR,
    build_csp_payoff_figure,
)
from apps.csp_payoff import CSPPayoffSeries


def payoff_series(
    *,
    ticker: str = "ORCL",
    expiration: str = "2026-09-18",
) -> CSPPayoffSeries:
    return CSPPayoffSeries(
        ticker=ticker,
        expiration=expiration,
        spot_price=185.25,
        spot_price_as_of="2026-08-06",
        strike=180.0,
        premium=3.30,
        premium_source="bid_ask_midpoint",
        premium_quote_status="normal",
        premium_warning=None,
        contract_size=100,
        break_even_price=176.70,
        max_profit_dollars=330.0,
        max_loss_dollars=17_670.0,
        underlying_prices=(0.0, 170.0, 176.70, 180.0, 185.25),
        profit_loss_dollars=(-17_670.0, -670.0, 0.0, 330.0, 330.0),
    )


def test_build_csp_payoff_figure_renders_clipped_areas_and_payoff_line(
) -> None:
    series = payoff_series()

    figure = build_csp_payoff_figure(series)

    assert [trace.name for trace in figure.data] == [
        "Profit area",
        "Loss area",
        "Profit / loss",
    ]

    profit_area, loss_area, payoff_line = figure.data
    assert list(profit_area.x) == list(series.underlying_prices)
    assert list(profit_area.y) == [0.0, 0.0, 0.0, 330.0, 330.0]
    assert profit_area.fill == "tozeroy"
    assert profit_area.hoverinfo == "skip"

    assert list(loss_area.x) == list(series.underlying_prices)
    assert list(loss_area.y) == [-17_670.0, -670.0, 0.0, 0.0, 0.0]
    assert loss_area.fill == "tozeroy"
    assert loss_area.hoverinfo == "skip"

    assert list(payoff_line.x) == list(series.underlying_prices)
    assert list(payoff_line.y) == list(series.profit_loss_dollars)
    assert payoff_line.line.color == PAYOFF_LINE_COLOR
    assert payoff_line.line.width == 3
    assert "%{x:$,.2f}" in payoff_line.hovertemplate
    assert "%{y:$,.2f}" in payoff_line.hovertemplate


def test_build_csp_payoff_figure_marks_financial_landmarks() -> None:
    series = payoff_series()

    figure = build_csp_payoff_figure(series)

    shapes = list(figure.layout.shapes)
    assert len(shapes) == 4

    zero_line, break_even_line, strike_line, spot_line = shapes
    assert zero_line.y0 == zero_line.y1 == 0

    assert break_even_line.x0 == break_even_line.x1 == series.break_even_price
    assert break_even_line.line.color == BREAK_EVEN_COLOR
    assert break_even_line.line.dash == "dash"

    assert strike_line.x0 == strike_line.x1 == series.strike
    assert strike_line.line.color == STRIKE_COLOR
    assert strike_line.line.dash == "dot"

    assert spot_line.x0 == spot_line.x1 == series.spot_price
    assert spot_line.line.color == SPOT_COLOR
    assert spot_line.line.dash == "dashdot"

    annotation_text = {
        annotation.text
        for annotation in figure.layout.annotations
    }
    assert annotation_text == {
        "Break-even $176.70",
        "Strike $180.00",
        "Spot $185.25",
    }


def test_build_csp_payoff_figure_configures_dashboard_layout() -> None:
    figure = build_csp_payoff_figure(payoff_series())

    assert figure.layout.height == 460
    assert figure.layout.showlegend is False
    assert figure.layout.paper_bgcolor == "rgba(0, 0, 0, 0)"
    assert figure.layout.margin.l == 90
    assert figure.layout.xaxis.title.text == "Underlying price at expiration"
    assert figure.layout.xaxis.tickprefix == "$"
    assert figure.layout.yaxis.title.text == "Profit / loss per contract"
    assert figure.layout.yaxis.title.standoff == 18
    assert figure.layout.yaxis.automargin is True
    assert figure.layout.yaxis.tickprefix == "$"


def test_build_csp_payoff_figure_summarizes_risk_and_escapes_title(
) -> None:
    series = payoff_series(
        ticker="<ORCL>",
        expiration="2026-09-18<script>",
    )

    figure = build_csp_payoff_figure(series)

    title = figure.layout.title.text
    assert "&lt;ORCL&gt; cash-secured put payoff" in title
    assert "2026-09-18&lt;script&gt;" in title
    assert "Maximum profit $330" in title
    assert "Maximum loss $17,670" in title
    assert "<ORCL>" not in title
    assert "<script>" not in title


def test_build_csp_payoff_figure_does_not_mutate_source_series() -> None:
    series = payoff_series()
    original_prices = series.underlying_prices
    original_payoffs = series.profit_loss_dollars

    build_csp_payoff_figure(series)

    assert series.underlying_prices is original_prices
    assert series.profit_loss_dollars is original_payoffs
