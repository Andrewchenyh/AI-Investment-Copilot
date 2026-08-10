from html import escape

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from apps.options_liquidity import (
    OptionLiquidityPoint,
    OptionsLiquiditySnapshot,
)


NORMAL_QUOTE_COLOR = "#0F766E"
WIDE_QUOTE_COLOR = "#F59E0B"
MIDPOINT_LINE_COLOR = "#94A3B8"
OPEN_INTEREST_COLOR = "#7C3AED"
VOLUME_COLOR = "#2563EB"
GRID_COLOR = "#E2E8F0"


def _quote_arrays(
    points: list[OptionLiquidityPoint],
) -> tuple[
    list[float],
    list[float],
    list[float],
    list[float],
    list[list[object]],
]:
    strikes: list[float] = []
    mid_prices: list[float] = []
    upper_errors: list[float] = []
    lower_errors: list[float] = []
    custom_data: list[list[object]] = []

    for point in points:
        if (
            point.bid is None
            or point.ask is None
            or point.mid_price is None
            or point.bid_ask_spread_pct is None
        ):
            raise ValueError(
                "Quoted option points require bid, ask, "
                "midpoint, and spread percentage."
            )

        strikes.append(point.strike)
        mid_prices.append(point.mid_price)
        upper_errors.append(
            point.ask - point.mid_price
        )
        lower_errors.append(
            point.mid_price - point.bid
        )
        custom_data.append(
            [
                point.contract_symbol,
                point.bid,
                point.ask,
                point.bid_ask_spread_pct,
                point.open_interest,
                point.volume,
            ]
        )

    return (
        strikes,
        mid_prices,
        upper_errors,
        lower_errors,
        custom_data,
    )


def build_options_liquidity_figure(
    snapshot: OptionsLiquiditySnapshot,
) -> go.Figure:
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=(
            "Quote midpoint and bid–ask range",
            "Liquidity by strike",
        ),
        row_heights=[0.55, 0.45],
        vertical_spacing=0.14,
    )

    quoted_points = [
        point
        for point in snapshot.points
        if point.quote_status in {"normal", "wide"}
    ]

    if quoted_points:
        figure.add_trace(
            go.Scatter(
                x=[
                    point.strike
                    for point in quoted_points
                ],
                y=[
                    point.mid_price
                    for point in quoted_points
                ],
                mode="lines",
                line={
                    "color": MIDPOINT_LINE_COLOR,
                    "width": 2,
                },
                hoverinfo="skip",
                showlegend=False,
                name="Midpoint curve",
            ),
            row=1,
            col=1,
        )

    for (
        status,
        label,
        color,
        symbol,
    ) in (
        (
            "normal",
            "Normal quote",
            NORMAL_QUOTE_COLOR,
            "circle",
        ),
        (
            "wide",
            "Wide quote",
            WIDE_QUOTE_COLOR,
            "diamond",
        ),
    ):
        status_points = [
            point
            for point in quoted_points
            if point.quote_status == status
        ]
        if not status_points:
            continue

        (
            strikes,
            mid_prices,
            upper_errors,
            lower_errors,
            custom_data,
        ) = _quote_arrays(status_points)

        figure.add_trace(
            go.Scatter(
                x=strikes,
                y=mid_prices,
                mode="markers",
                marker={
                    "color": color,
                    "size": 12,
                    "symbol": symbol,
                    "line": {
                        "color": "#FFFFFF",
                        "width": 1,
                    },
                },
                error_y={
                    "type": "data",
                    "array": upper_errors,
                    "arrayminus": lower_errors,
                    "symmetric": False,
                    "color": color,
                    "thickness": 1.5,
                    "width": 5,
                },
                customdata=custom_data,
                name=label,
                hovertemplate=(
                    "Contract: %{customdata[0]}"
                    "<br>Strike: %{x:$,.2f}"
                    "<br>Midpoint: %{y:$,.2f}"
                    "<br>Bid: %{customdata[1]:$,.2f}"
                    "<br>Ask: %{customdata[2]:$,.2f}"
                    "<br>Spread: %{customdata[3]:.1%}"
                    "<br>Open interest: %{customdata[4]}"
                    "<br>Volume: %{customdata[5]}"
                    "<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )

    strikes = [
        point.strike
        for point in snapshot.points
    ]

    figure.add_trace(
        go.Bar(
            x=strikes,
            y=[
                point.open_interest
                for point in snapshot.points
            ],
            name="Open interest",
            marker_color=OPEN_INTEREST_COLOR,
            customdata=[
                [point.contract_symbol]
                for point in snapshot.points
            ],
            hovertemplate=(
                "Contract: %{customdata[0]}"
                "<br>Strike: %{x:$,.2f}"
                "<br>Open interest: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        row=2,
        col=1,
    )

    figure.add_trace(
        go.Bar(
            x=strikes,
            y=[
                point.volume
                for point in snapshot.points
            ],
            name="Volume",
            marker_color=VOLUME_COLOR,
            customdata=[
                [point.contract_symbol]
                for point in snapshot.points
            ],
            hovertemplate=(
                "Contract: %{customdata[0]}"
                "<br>Strike: %{x:$,.2f}"
                "<br>Volume: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        row=2,
        col=1,
    )

    if not quoted_points:
        figure.add_annotation(
            text=(
                "No usable two-sided quotes in "
                "the selected contract sample."
            ),
            x=0.5,
            y=0.80,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={
                "color": "#64748B",
                "size": 13,
            },
        )

    status_counts = {
        status: sum(
            point.quote_status == status
            for point in snapshot.points
        )
        for status in (
            "normal",
            "wide",
            "crossed",
            "unavailable",
        )
    }
    status_summary = " · ".join(
        f"{status.title()} {count}"
        for status, count in status_counts.items()
        if count > 0
    )

    safe_ticker = escape(snapshot.ticker)
    safe_expiration = escape(snapshot.expiration)
    safe_option_type = escape(snapshot.option_type)
    safe_source = escape(snapshot.source)

    figure.update_layout(
        title={
            "text": (
                f"<b>{safe_ticker} "
                f"{safe_option_type} contract sample</b>"
                f"<br><sup>"
                f"Expiration {safe_expiration} · "
                f"{snapshot.contract_count} contracts · "
                f"{status_summary} · "
                f"{safe_source}"
                f"</sup>"
            ),
            "x": 0.02,
            "xanchor": "left",
        },
        height=720,
        margin={
            "l": 85,
            "r": 45,
            "t": 105,
            "b": 90,
        },
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="#FFFFFF",
        barmode="group",
        hovermode="closest",
        font={
            "color": "#0F172A",
            "family": "sans-serif",
        },
        legend={
            "orientation": "h",
            "x": 0.5,
            "xanchor": "center",
            "y": -0.12,
            "yanchor": "top",
        },
    )

    figure.update_xaxes(
        tickprefix="$",
        gridcolor=GRID_COLOR,
        automargin=True,
        row=1,
        col=1,
    )
    figure.update_yaxes(
        title_text="Premium per share",
        tickprefix="$",
        gridcolor=GRID_COLOR,
        automargin=True,
        row=1,
        col=1,
    )
    figure.update_xaxes(
        title_text="Strike",
        tickprefix="$",
        gridcolor=GRID_COLOR,
        automargin=True,
        row=2,
        col=1,
    )
    figure.update_yaxes(
        title_text="Contracts",
        gridcolor=GRID_COLOR,
        rangemode="tozero",
        automargin=True,
        row=2,
        col=1,
    )

    figure.update_annotations(
        font={
            "color": "#334155",
            "size": 14,
        }
    )

    return figure