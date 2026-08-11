from dataclasses import replace

from apps.charts import (
    LOSS_COLOR,
    MACD_COLOR,
    MACD_SIGNAL_COLOR,
    PROFIT_COLOR,
    build_technical_snapshot_figure,
)
from apps.technical_snapshot import TechnicalSnapshot


def technical_snapshot() -> TechnicalSnapshot:
    return TechnicalSnapshot(
        ticker="AAPL",
        as_of="2026-08-07",
        close=229.35,
        observation_count=251,
        sma_20=221.10,
        sma_50=214.25,
        ema_20=223.40,
        rsi_14=58.75,
        macd_line=3.20,
        macd_signal=2.65,
        macd_histogram=0.55,
        bollinger_middle=221.10,
        bollinger_upper=235.80,
        bollinger_lower=206.40,
        lookback_period="1y",
        interval="1d",
        source="yfinance",
    )


def test_technical_figure_maps_price_levels_and_bollinger_band() -> None:
    snapshot = technical_snapshot()

    figure = build_technical_snapshot_figure(snapshot)

    assert [trace.type for trace in figure.data] == [
        "scatter",
        "scatter",
        "scatter",
        "scatter",
        "scatter",
        "scatter",
        "indicator",
        "bar",
    ]
    assert [trace.name for trace in figure.data[:6]] == [
        "Close",
        "EMA (20)",
        "SMA (20)",
        "SMA (50)",
        "Bollinger range",
        "Bollinger middle",
    ]
    assert [list(trace.x) for trace in figure.data[:4]] == [
        [snapshot.close],
        [snapshot.ema_20],
        [snapshot.sma_20],
        [snapshot.sma_50],
    ]
    assert list(figure.data[4].x) == [
        snapshot.bollinger_lower,
        snapshot.bollinger_upper,
    ]
    assert list(figure.data[5].x) == [
        snapshot.bollinger_middle
    ]


def test_technical_figure_configures_bounded_rsi_gauge() -> None:
    snapshot = technical_snapshot()

    figure = build_technical_snapshot_figure(snapshot)

    indicator = figure.data[6]
    assert indicator.value == snapshot.rsi_14
    assert indicator.mode == "gauge+number"
    assert list(indicator.gauge.axis.range) == [0, 100]
    assert list(indicator.gauge.axis.tickvals) == [
        0,
        30,
        70,
        100,
    ]
    assert [list(step.range) for step in indicator.gauge.steps] == [
        [0, 30],
        [30, 70],
        [70, 100],
    ]


def test_technical_figure_maps_macd_values_and_direction_color() -> None:
    positive_snapshot = technical_snapshot()
    negative_snapshot = replace(
        positive_snapshot,
        macd_histogram=-0.55,
    )

    positive_bar = build_technical_snapshot_figure(
        positive_snapshot
    ).data[7]
    negative_bar = build_technical_snapshot_figure(
        negative_snapshot
    ).data[7]

    assert list(positive_bar.x) == [
        "MACD",
        "Signal",
        "Histogram",
    ]
    assert list(positive_bar.y) == [3.20, 2.65, 0.55]
    assert list(positive_bar.marker.color) == [
        MACD_COLOR,
        MACD_SIGNAL_COLOR,
        PROFIT_COLOR,
    ]
    assert list(negative_bar.y) == [3.20, 2.65, -0.55]
    assert list(negative_bar.marker.color) == [
        MACD_COLOR,
        MACD_SIGNAL_COLOR,
        LOSS_COLOR,
    ]


def test_technical_figure_configures_subplots_and_macd_zero_line() -> None:
    figure = build_technical_snapshot_figure(
        technical_snapshot()
    )

    assert [
        annotation.text
        for annotation in figure.layout.annotations
    ] == [
        "Price positioning",
        "RSI (14)",
        "MACD snapshot",
    ]
    assert figure.layout.height == 920
    assert figure.layout.margin.l == 90
    assert figure.layout.margin.r == 75
    assert figure.layout.xaxis.title.text == "Price level"
    assert figure.layout.xaxis.tickprefix == "$"
    assert figure.layout.yaxis2.title.text == "Indicator value"

    assert len(figure.layout.shapes) == 1
    zero_line = figure.layout.shapes[0]
    assert zero_line.xref == "x2 domain"
    assert zero_line.yref == "y2"
    assert zero_line.y0 == zero_line.y1 == 0


def test_technical_figure_escapes_provenance_title() -> None:
    snapshot = replace(
        technical_snapshot(),
        ticker="<AAPL>",
        as_of="2026-08-07<script>",
        lookback_period="<1y>",
        interval="<1d>",
        source="<source>",
    )

    figure = build_technical_snapshot_figure(snapshot)

    title = figure.layout.title.text
    assert "&lt;AAPL&gt; technical indicator snapshot" in title
    assert "2026-08-07&lt;script&gt;" in title
    assert "&lt;1y&gt; lookback" in title
    assert "&lt;1d&gt; bars" in title
    assert "&lt;source&gt;" in title
    assert "<AAPL>" not in title
    assert "<script>" not in title
