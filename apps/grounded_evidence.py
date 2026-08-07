import math
from typing import Any


EvidenceRow = dict[str, str]


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    number = float(value)
    if not math.isfinite(number):
        return None

    return number


def _format_money(value: Any) -> str:
    number = _finite_number(value)
    if number is None:
        return "Unavailable"

    return f"${number:,.2f}"


def _format_percent(value: Any) -> str:
    number = _finite_number(value)
    if number is None:
        return "Unavailable"

    return f"{number * 100:.2f}%"


def _format_number(value: Any) -> str:
    number = _finite_number(value)
    if number is None:
        return "Unavailable"

    return f"{number:,.2f}"


def _humanize(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "Unavailable"

    return value.replace("_", " ")


def _row(
    metric: str,
    value: str,
    evidence: str,
) -> EvidenceRow:
    return {
        "Metric": metric,
        "Value": value,
        "Evidence": evidence,
    }


def build_grounded_evidence(
    trace: list[dict[str, Any]],
) -> list[EvidenceRow]:
    rows: list[EvidenceRow] = []

    for item in trace:
        if item.get("success") is not True:
            continue

        tool_name = item.get("tool_name")
        observation = item.get("observation")

        if not isinstance(observation, dict):
            continue

        source = _humanize(observation.get("source"))

        if tool_name == "get_current_price":
            ticker = observation.get("ticker", "")
            rows.append(
                _row(
                    f"{ticker} latest close",
                    _format_money(observation.get("price")),
                    (
                        f"{source} · as of "
                        f"{observation.get('as_of', 'Unavailable')} · "
                        f"{_humanize(observation.get('price_type'))}"
                    ),
                )
            )

        elif tool_name == "analyze_technical_indicators":
            ticker = observation.get("ticker", "")

            moving_averages = observation.get("moving_averages")
            if not isinstance(moving_averages, dict):
                moving_averages = {}

            macd = observation.get("macd")
            if not isinstance(macd, dict):
                macd = {}

            bollinger_bands = observation.get("bollinger_bands")
            if not isinstance(bollinger_bands, dict):
                bollinger_bands = {}

            evidence = (
                f"As of {observation.get('as_of', 'Unavailable')} · "
                f"{_humanize(observation.get('lookback_period'))} lookback · "
                f"{_humanize(observation.get('interval'))} bars · "
                f"{source}"
            )

            rows.extend(
                [
                    _row(
                        f"{ticker} close",
                        _format_number(observation.get("close")),
                        evidence,
                    ),
                    _row(
                        f"{ticker} RSI (14)",
                        _format_number(observation.get("rsi_14")),
                        "0–100 momentum scale · " + evidence,
                    ),
                    _row(
                        f"{ticker} SMA (20)",
                        _format_number(moving_averages.get("sma_20")),
                        evidence,
                    ),
                    _row(
                        f"{ticker} SMA (50)",
                        _format_number(moving_averages.get("sma_50")),
                        evidence,
                    ),
                    _row(
                        f"{ticker} EMA (20)",
                        _format_number(moving_averages.get("ema_20")),
                        evidence,
                    ),
                    _row(
                        f"{ticker} MACD histogram",
                        _format_number(macd.get("histogram")),
                        evidence,
                    ),
                    _row(
                        f"{ticker} Bollinger lower",
                        _format_number(bollinger_bands.get("lower")),
                        evidence,
                    ),
                    _row(
                        f"{ticker} Bollinger middle",
                        _format_number(bollinger_bands.get("middle")),
                        evidence,
                    ),
                    _row(
                        f"{ticker} Bollinger upper",
                        _format_number(bollinger_bands.get("upper")),
                        evidence,
                    ),
                ]
            )

        elif tool_name == "get_historical_volatility":
            ticker = observation.get("ticker", "")
            rows.append(
                _row(
                    f"{ticker} historical volatility",
                    _format_percent(
                        observation.get("annualized_volatility")
                    ),
                    (
                        f"{observation.get('lookback_days', 'Unavailable')}"
                        f"-day lookback · as of "
                        f"{observation.get('as_of', 'Unavailable')} · "
                        f"{source}"
                    ),
                )
            )

        elif tool_name == "get_options_chain":
            contract_count = observation.get("contract_count")
            count_text = (
                str(contract_count)
                if type(contract_count) is int
                else "Unavailable"
            )

            rows.append(
                _row(
                    "Options chain",
                    (
                        f"{count_text} "
                        f"{observation.get('option_type', '')} contracts"
                    ),
                    (
                        f"Expiration "
                        f"{observation.get('expiration', 'Unavailable')} · "
                        f"{source}"
                    ),
                )
            )

        elif tool_name == "analyze_cash_secured_put":
            premium_evidence = (
                f"Source: "
                f"{_humanize(observation.get('premium_source'))}"
            )

            quote_status = observation.get(
                "premium_quote_status"
            )
            if isinstance(quote_status, str):
                premium_evidence += (
                    f" · Quote: {_humanize(quote_status)}"
                )

            rows.extend(
                [
                    _row(
                        "CSP spot price",
                        _format_money(
                            observation.get("spot_price")
                        ),
                        (
                            f"As of "
                            f"{observation.get('spot_price_as_of', 'Unavailable')}"
                            f" · "
                            f"{_humanize(observation.get('spot_price_type'))}"
                        ),
                    ),
                    _row(
                        "Strike",
                        _format_money(observation.get("strike")),
                        "Selected put contract",
                    ),
                    _row(
                        "Premium per share",
                        _format_money(observation.get("premium")),
                        premium_evidence,
                    ),
                    _row(
                        "Break-even",
                        _format_money(
                            observation.get("break_even_price")
                        ),
                        "Strike minus premium",
                    ),
                    _row(
                        "Cash collateral",
                        _format_money(
                            observation.get(
                                "cash_required_dollars"
                            )
                        ),
                        _humanize(
                            observation.get("collateral_basis")
                        ),
                    ),
                    _row(
                        "Maximum profit",
                        _format_money(
                            observation.get("max_profit_dollars")
                        ),
                        "Premium × contract size",
                    ),
                    _row(
                        "Maximum loss",
                        _format_money(
                            observation.get("max_loss_dollars")
                        ),
                        "Underlying falls to zero",
                    ),
                    _row(
                        "Simple return",
                        _format_percent(
                            observation.get("simple_return")
                        ),
                        _humanize(
                            observation.get("return_basis")
                        ),
                    ),
                    _row(
                        "Annualized return",
                        _format_percent(
                            observation.get("annualized_return")
                        ),
                        _humanize(
                            observation.get(
                                "annualization_method"
                            )
                        ),
                    ),
                ]
            )

            premium_warning = observation.get("premium_warning")
            if isinstance(premium_warning, str) and premium_warning:
                rows.append(
                    _row(
                        "Quote warning",
                        premium_warning,
                        "Automated quote-quality check",
                    )
                )

            limitations = observation.get("limitations")
            if isinstance(limitations, list):
                rows.append(
                    _row(
                        "Model limitations",
                        f"{len(limitations)} disclosed",
                        "Structured CSP limitations",
                    )
                )

    return rows