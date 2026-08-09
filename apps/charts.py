from html import escape

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from apps.csp_payoff import CSPPayoffSeries
from apps.technical_snapshot import TechnicalSnapshot


PAYOFF_LINE_COLOR = "#0F766E"
BREAK_EVEN_COLOR = "#F59E0B"
STRIKE_COLOR = "#64748B"
SPOT_COLOR = "#2563EB"
GRID_COLOR = "#E2E8F0"
CLOSE_COLOR = "#2563EB"
SMA_20_COLOR = "#0F766E"
SMA_50_COLOR = "#7C3AED"
EMA_20_COLOR = "#D97706"
BOLLINGER_COLOR = "#93C5FD"
BOLLINGER_MIDDLE_COLOR = "#1D4ED8"
MACD_COLOR = "#0F766E"
MACD_SIGNAL_COLOR = "#F59E0B"
PROFIT_COLOR = "#10B981"
LOSS_COLOR = "#EF4444"


def build_csp_payoff_figure(
    series: CSPPayoffSeries,
) -> go.Figure:
    underlying_prices = list(
        series.underlying_prices
    )
    profit_loss = list(
        series.profit_loss_dollars
    )

    positive_area = [
        max(value, 0.0)
        for value in profit_loss
    ]
    negative_area = [
        min(value, 0.0)
        for value in profit_loss
    ]

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=underlying_prices,
            y=positive_area,
            mode="lines",
            line={"width": 0},
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.18)",
            hoverinfo="skip",
            showlegend=False,
            name="Profit area",
        )
    )

    figure.add_trace(
        go.Scatter(
            x=underlying_prices,
            y=negative_area,
            mode="lines",
            line={"width": 0},
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.16)",
            hoverinfo="skip",
            showlegend=False,
            name="Loss area",
        )
    )

    figure.add_trace(
        go.Scatter(
            x=underlying_prices,
            y=profit_loss,
            mode="lines",
            name="Profit / loss",
            line={
                "color": PAYOFF_LINE_COLOR,
                "width": 3,
            },
            hovertemplate=(
                "Underlying: %{x:$,.2f}"
                "<br>Profit / loss: %{y:$,.2f}"
                "<extra></extra>"
            ),
        )
    )

    figure.add_hline(
        y=0,
        line_color="#0F172A",
        line_width=1,
    )

    figure.add_vline(
        x=series.break_even_price,
        line_color=BREAK_EVEN_COLOR,
        line_dash="dash",
        line_width=2,
        annotation_text=(
            f"Break-even "
            f"${series.break_even_price:,.2f}"
        ),
        annotation_position="top left",
    )

    figure.add_vline(
        x=series.strike,
        line_color=STRIKE_COLOR,
        line_dash="dot",
        line_width=2,
        annotation_text=(
            f"Strike ${series.strike:,.2f}"
        ),
        annotation_position="top right",
    )

    figure.add_vline(
        x=series.spot_price,
        line_color=SPOT_COLOR,
        line_dash="dashdot",
        line_width=2,
        annotation_text=(
            f"Spot ${series.spot_price:,.2f}"
        ),
        annotation_position="bottom right",
    )

    safe_ticker = escape(series.ticker)
    safe_expiration = escape(series.expiration)

    figure.update_layout(
        title={
            "text": (
                f"<b>{safe_ticker} cash-secured put payoff</b>"
                f"<br><sup>"
                f"Expiration {safe_expiration} · "
                f"Maximum profit "
                f"${series.max_profit_dollars:,.0f} · "
                f"Maximum loss "
                f"${series.max_loss_dollars:,.0f}"
                f"</sup>"
            ),
            "x": 0.02,
            "xanchor": "left",
        },
        height=460,
        margin={
            "l": 90,
            "r": 30,
            "t": 90,
            "b": 45,
        },
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="#FFFFFF",
        hovermode="closest",
        showlegend=False,
        font={
            "color": "#0F172A",
            "family": "sans-serif",
        },
        xaxis={
            "title": "Underlying price at expiration",
            "tickprefix": "$",
            "gridcolor": GRID_COLOR,
            "zeroline": False,
            "showline": True,
            "linecolor": GRID_COLOR,
        },
        yaxis={
            "title": {
                "text": "Profit / loss per contract",
                "standoff": 18,
            },
            "automargin": True,
            "tickprefix": "$",
            "gridcolor": GRID_COLOR,
            "zeroline": False,
            "showline": True,
            "linecolor": GRID_COLOR,
        },
    )

    return figure


def build_technical_snapshot_figure(
    snapshot: TechnicalSnapshot,
) -> go.Figure:
    figure = make_subplots(
        rows=3,
        cols=1,
        specs=[
            [{"type": "xy"}],
            [{"type": "indicator"}],
            [{"type": "xy"}],
        ],
        subplot_titles=(
            "Price positioning",
            "RSI (14)",
            "MACD snapshot",
        ),
        row_heights=[
            0.42,
            0.25,
            0.33,
        ],
        vertical_spacing=0.15,
    )

    price_markers = (
        (
            "Close",
            snapshot.close,
            CLOSE_COLOR,
            "diamond",
            15,
        ),
        (
            "EMA (20)",
            snapshot.ema_20,
            EMA_20_COLOR,
            "circle",
            12,
        ),
        (
            "SMA (20)",
            snapshot.sma_20,
            SMA_20_COLOR,
            "circle",
            12,
        ),
        (
            "SMA (50)",
            snapshot.sma_50,
            SMA_50_COLOR,
            "circle",
            12,
        ),
    )

    for (
        label,
        value,
        color,
        symbol,
        size,
    ) in price_markers:
        figure.add_trace(
            go.Scatter(
                x=[value],
                y=[label],
                mode="markers",
                marker={
                    "color": color,
                    "size": size,
                    "symbol": symbol,
                    "line": {
                        "color": "#FFFFFF",
                        "width": 1,
                    },
                },
                name=label,
                hovertemplate=(
                    f"{label}: %{{x:$,.2f}}"
                    "<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1,
            col=1,
        )

    figure.add_trace(
        go.Scatter(
            x=[
                snapshot.bollinger_lower,
                snapshot.bollinger_upper,
            ],
            y=[
                "Bollinger band (20)",
                "Bollinger band (20)",
            ],
            mode="lines+markers",
            line={
                "color": BOLLINGER_COLOR,
                "width": 10,
            },
            marker={
                "color": BOLLINGER_MIDDLE_COLOR,
                "size": 7,
            },
            name="Bollinger range",
            hovertemplate=(
                "Bollinger boundary: %{x:$,.2f}"
                "<extra></extra>"
            ),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    figure.add_trace(
        go.Scatter(
            x=[snapshot.bollinger_middle],
            y=["Bollinger band (20)"],
            mode="markers",
            marker={
                "color": BOLLINGER_MIDDLE_COLOR,
                "size": 12,
                "symbol": "diamond",
            },
            name="Bollinger middle",
            hovertemplate=(
                "Bollinger middle: %{x:$,.2f}"
                "<extra></extra>"
            ),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    figure.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=snapshot.rsi_14,
            number={
                "valueformat": ".1f",
                "font": {
                    "color": "#0F172A",
                    "size": 34,
                },
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickvals": [
                        0,
                        30,
                        70,
                        100,
                    ],
                },
                "bar": {
                    "color": CLOSE_COLOR,
                    "thickness": 0.32,
                },
                "steps": [
                    {
                        "range": [0, 30],
                        "color": (
                            "rgba(37, 99, 235, 0.12)"
                        ),
                    },
                    {
                        "range": [30, 70],
                        "color": (
                            "rgba(100, 116, 139, 0.08)"
                        ),
                    },
                    {
                        "range": [70, 100],
                        "color": (
                            "rgba(239, 68, 68, 0.12)"
                        ),
                    },
                ],
            },
        ),
        row=2,
        col=1,
    )

    histogram_color = (
        PROFIT_COLOR
        if snapshot.macd_histogram >= 0
        else LOSS_COLOR
    )

    figure.add_trace(
        go.Bar(
            x=[
                "MACD",
                "Signal",
                "Histogram",
            ],
            y=[
                snapshot.macd_line,
                snapshot.macd_signal,
                snapshot.macd_histogram,
            ],
            marker_color=[
                MACD_COLOR,
                MACD_SIGNAL_COLOR,
                histogram_color,
            ],
            hovertemplate=(
                "%{x}: %{y:,.2f}"
                "<extra></extra>"
            ),
            showlegend=False,
        ),
        row=3,
        col=1,
    )

    figure.add_shape(
        type="line",
        x0=0,
        x1=1,
        y0=0,
        y1=0,
        xref="x2 domain",
        yref="y2",
        line={
            "color": "#64748B",
            "width": 1,
        },
        layer="below",
    )

    safe_ticker = escape(snapshot.ticker)
    safe_as_of = escape(snapshot.as_of)
    safe_lookback = escape(snapshot.lookback_period)
    safe_interval = escape(snapshot.interval)
    safe_source = escape(snapshot.source)

    figure.update_layout(
        title={
            "text": (
                f"<b>{safe_ticker} technical "
                f"indicator snapshot</b>"
                f"<br><sup>"
                f"As of {safe_as_of} · "
                f"{snapshot.observation_count} observations · "
                f"{safe_lookback} lookback · "
                f"{safe_interval} bars · "
                f"{safe_source}"
                f"</sup>"
            ),
            "x": 0.02,
            "xanchor": "left",
        },
        height=920,
        margin={
            "l": 90,
            "r": 75,
            "t": 100,
            "b": 60,
        },
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="#FFFFFF",
        showlegend=False,
        font={
            "color": "#0F172A",
            "family": "sans-serif",
        },
    )

    figure.update_xaxes(
        title_text="Price level",
        tickprefix="$",
        gridcolor=GRID_COLOR,
        automargin=True,
        row=1,
        col=1,
    )
    figure.update_yaxes(
        categoryorder="array",
        categoryarray=[
            "Bollinger band (20)",
            "SMA (50)",
            "SMA (20)",
            "EMA (20)",
            "Close",
        ],
        automargin=True,
        row=1,
        col=1,
    )
    figure.update_xaxes(
        showgrid=False,
        row=3,
        col=1,
    )
    figure.update_yaxes(
        title_text="Indicator value",
        gridcolor=GRID_COLOR,
        zeroline=False,
        automargin=True,
        row=3,
        col=1,
    )

    figure.update_annotations(
        font={
            "color": "#334155",
            "size": 14,
        }
    )

    return figure
