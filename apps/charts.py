from html import escape

import plotly.graph_objects as go

from apps.csp_payoff import CSPPayoffSeries


PAYOFF_LINE_COLOR = "#0F766E"
BREAK_EVEN_COLOR = "#F59E0B"
STRIKE_COLOR = "#64748B"
SPOT_COLOR = "#2563EB"
GRID_COLOR = "#E2E8F0"


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
