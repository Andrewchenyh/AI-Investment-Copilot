import math
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import ValidationError

from tools.options_tools import (
    OptionContract,
    OptionsChainOutput,
    QuoteStatus,
    WIDE_BID_ASK_SPREAD_PCT,
)


@dataclass(frozen=True)
class OptionLiquidityPoint:
    contract_symbol: str
    strike: float
    last_price: float | None
    bid: float | None
    ask: float | None
    mid_price: float | None
    bid_ask_spread: float | None
    bid_ask_spread_pct: float | None
    quote_status: QuoteStatus
    volume: int | None
    open_interest: int | None
    implied_volatility: float | None
    in_the_money: bool | None


@dataclass(frozen=True)
class OptionsLiquiditySnapshot:
    ticker: str
    expiration: str
    option_type: str
    contract_count: int
    selection_basis: str
    expiration_selection_basis: str
    source: str
    points: tuple[OptionLiquidityPoint, ...]


def _latest_successful_options_observation(
    trace: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for item in reversed(trace):
        if item.get("tool_name") != "get_options_chain":
            continue

        if item.get("success") is not True:
            continue

        observation = item.get("observation")
        if isinstance(observation, dict):
            return observation

    return None


def _valid_optional_number(
    value: float | None,
) -> bool:
    return (
        value is None
        or (
            math.isfinite(value)
            and value >= 0
        )
    )


def _quote_is_consistent(
    contract: OptionContract,
) -> bool:
    metrics = (
        contract.mid_price,
        contract.bid_ask_spread,
        contract.bid_ask_spread_pct,
    )

    if contract.quote_status in {"normal", "wide"}:
        if (
            contract.bid is None
            or contract.ask is None
            or contract.bid <= 0
            or contract.ask <= 0
            or contract.ask < contract.bid
            or any(value is None for value in metrics)
        ):
            return False

        expected_mid = (
            contract.bid + contract.ask
        ) / 2
        expected_spread = (
            contract.ask - contract.bid
        )
        expected_spread_pct = (
            expected_spread / expected_mid
        )

        if not math.isclose(
            contract.mid_price,
            expected_mid,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            return False

        if not math.isclose(
            contract.bid_ask_spread,
            expected_spread,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            return False

        if not math.isclose(
            contract.bid_ask_spread_pct,
            expected_spread_pct,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            return False

        if contract.quote_status == "normal":
            return (
                contract.bid_ask_spread_pct
                <= WIDE_BID_ASK_SPREAD_PCT
            )

        return (
            contract.bid_ask_spread_pct
            > WIDE_BID_ASK_SPREAD_PCT
        )

    if any(value is not None for value in metrics):
        return False

    if contract.quote_status == "crossed":
        return (
            contract.bid is not None
            and contract.ask is not None
            and contract.bid > 0
            and contract.ask > 0
            and contract.ask < contract.bid
        )

    return (
        contract.bid is None
        or contract.ask is None
        or contract.bid <= 0
        or contract.ask <= 0
    )


def build_options_liquidity_snapshot(
    trace: list[dict[str, Any]],
) -> OptionsLiquiditySnapshot | None:
    observation = (
        _latest_successful_options_observation(
            trace
        )
    )
    if observation is None:
        return None

    if type(observation.get("contract_count")) is not int:
        return None

    try:
        output = OptionsChainOutput.model_validate(
            observation
        )
        date.fromisoformat(output.expiration)
    except (ValidationError, ValueError):
        return None

    ticker = output.ticker.strip().upper()
    option_type = output.option_type.strip().lower()
    selection_basis = output.selection_basis.strip()
    expiration_basis = (
        output.expiration_selection_basis.strip()
    )
    source = output.source.strip()

    if (
        not ticker
        or option_type not in {"put", "call"}
        or not selection_basis
        or not expiration_basis
        or not source
        or output.contract_count <= 0
        or output.contract_count != len(output.contracts)
    ):
        return None

    points: list[OptionLiquidityPoint] = []
    seen_symbols: set[str] = set()

    for contract in output.contracts:
        contract_symbol = (
            contract.contract_symbol.strip()
        )

        if (
            not contract_symbol
            or contract_symbol in seen_symbols
            or contract.expiration != output.expiration
            or contract.option_type != option_type
            or not math.isfinite(contract.strike)
            or contract.strike <= 0
        ):
            return None

        optional_numbers = (
            contract.last_price,
            contract.bid,
            contract.ask,
            contract.mid_price,
            contract.bid_ask_spread,
            contract.bid_ask_spread_pct,
            contract.implied_volatility,
        )
        if not all(
            _valid_optional_number(value)
            for value in optional_numbers
        ):
            return None

        if not _quote_is_consistent(contract):
            return None

        seen_symbols.add(contract_symbol)
        points.append(
            OptionLiquidityPoint(
                contract_symbol=contract_symbol,
                strike=contract.strike,
                last_price=contract.last_price,
                bid=contract.bid,
                ask=contract.ask,
                mid_price=contract.mid_price,
                bid_ask_spread=(
                    contract.bid_ask_spread
                ),
                bid_ask_spread_pct=(
                    contract.bid_ask_spread_pct
                ),
                quote_status=contract.quote_status,
                volume=contract.volume,
                open_interest=contract.open_interest,
                implied_volatility=(
                    contract.implied_volatility
                ),
                in_the_money=contract.in_the_money,
            )
        )

    points.sort(
        key=lambda point: (
            point.strike,
            point.contract_symbol,
        )
    )

    return OptionsLiquiditySnapshot(
        ticker=ticker,
        expiration=output.expiration,
        option_type=option_type,
        contract_count=output.contract_count,
        selection_basis=selection_basis,
        expiration_selection_basis=(
            expiration_basis
        ),
        source=source,
        points=tuple(points),
    )

def format_selection_basis(
    selection_basis: str,
) -> str:
    basis_name, separator, raw_value = (
        selection_basis.strip().partition(":")
    )

    labels = {
        "liquidity": "liquidity ranking",
        "nearest_to_target_strike": (
            "proximity to the requested strike"
        ),
        "nearest_to_reference_price": (
            "proximity to the current share price"
        ),
    }
    label = labels.get(
        basis_name,
        basis_name.replace("_", " "),
    )

    if not separator:
        return label

    try:
        reference_value = float(raw_value)
    except ValueError:
        return label

    if not math.isfinite(reference_value):
        return label

    return f"{label} (${reference_value:,.2f})"