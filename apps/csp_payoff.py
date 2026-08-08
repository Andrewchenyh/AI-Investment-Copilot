import math
from dataclasses import dataclass
from typing import Any

from analysis.risk_metrics import (
    cash_secured_put_break_even,
    cash_secured_put_max_loss,
    cash_secured_put_max_profit,
    cash_secured_put_profit_at_expiration,
)


@dataclass(frozen=True)
class CSPPayoffSeries:
    ticker: str
    expiration: str
    spot_price: float
    spot_price_as_of: str
    strike: float
    premium: float
    premium_source: str
    premium_quote_status: str | None
    premium_warning: str | None
    contract_size: int
    break_even_price: float
    max_profit_dollars: float
    max_loss_dollars: float
    underlying_prices: tuple[float, ...]
    profit_loss_dollars: tuple[float, ...]


def _positive_finite_number(
    value: Any,
) -> float | None:
    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    number = float(value)
    if not math.isfinite(number) or number <= 0:
        return None

    return number


def _non_empty_text(
    value: Any,
    default: str = "Unavailable",
) -> str:
    if not isinstance(value, str):
        return default

    normalized = value.strip()
    return normalized or default


def _latest_successful_csp_observation(
    trace: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for item in reversed(trace):
        if item.get("tool_name") != "analyze_cash_secured_put":
            continue

        if item.get("success") is not True:
            continue

        observation = item.get("observation")
        if isinstance(observation, dict):
            return observation

    return None


def build_csp_payoff_series(
    trace: list[dict[str, Any]],
    point_count: int = 101,
) -> CSPPayoffSeries | None:
    if type(point_count) is not int or point_count < 2:
        raise ValueError(
            "point_count must be an integer of at least 2."
        )

    observation = _latest_successful_csp_observation(
        trace
    )
    if observation is None:
        return None

    spot_price = _positive_finite_number(
        observation.get("spot_price")
    )
    strike = _positive_finite_number(
        observation.get("strike")
    )
    premium = _positive_finite_number(
        observation.get("premium")
    )

    contract_size = observation.get("contract_size")
    if type(contract_size) is not int or contract_size <= 0:
        return None

    if (
        spot_price is None
        or strike is None
        or premium is None
        or premium >= strike
    ):
        return None

    break_even = cash_secured_put_break_even(
        strike,
        premium,
    )
    max_profit = cash_secured_put_max_profit(
        premium,
        contract_size,
    )
    max_loss = cash_secured_put_max_loss(
        strike,
        premium,
        contract_size,
    )

    maximum_underlying_price = (
        max(spot_price, strike) * 1.5
    )
    underlying_prices = {
        maximum_underlying_price
        * index
        / (point_count - 1)
        for index in range(point_count)
    }

    # Ensure the chart contains every financially important landmark.
    underlying_prices.update(
        {
            0.0,
            break_even,
            strike,
            spot_price,
            maximum_underlying_price,
        }
    )

    sorted_prices = tuple(sorted(underlying_prices))

    profit_loss_values: list[float] = []
    for underlying_price in sorted_prices:
        profit_loss = cash_secured_put_profit_at_expiration(
            underlying_price=underlying_price,
            strike=strike,
            premium=premium,
            contract_size=contract_size,
        )

        # Normalize insignificant floating-point noise at break-even.
        if abs(profit_loss) < 1e-9:
            profit_loss = 0.0

        profit_loss_values.append(profit_loss)

    quote_status = observation.get(
        "premium_quote_status"
    )
    if not isinstance(quote_status, str):
        quote_status = None

    premium_warning = observation.get("premium_warning")
    if not isinstance(premium_warning, str):
        premium_warning = None

    return CSPPayoffSeries(
        ticker=_non_empty_text(
            observation.get("ticker")
        ),
        expiration=_non_empty_text(
            observation.get("expiration")
        ),
        spot_price=spot_price,
        spot_price_as_of=_non_empty_text(
            observation.get("spot_price_as_of")
        ),
        strike=strike,
        premium=premium,
        premium_source=_non_empty_text(
            observation.get("premium_source")
        ),
        premium_quote_status=quote_status,
        premium_warning=premium_warning,
        contract_size=contract_size,
        break_even_price=break_even,
        max_profit_dollars=max_profit,
        max_loss_dollars=max_loss,
        underlying_prices=sorted_prices,
        profit_loss_dollars=tuple(
            profit_loss_values
        ),
    )
