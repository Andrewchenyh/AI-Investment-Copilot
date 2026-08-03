import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from analysis.risk_metrics import (
    annualized_return,
    cash_secured_put_break_even,
    cash_secured_put_cash_required,
    cash_secured_put_max_profit,
    cash_secured_put_max_loss,
    simple_return_on_secured_cash,
)
from tools.market_data import (
    MarketDataEngine,
    extract_latest_daily_close,
)


WIDE_BID_ASK_SPREAD_PCT = 0.20

QuoteStatus = Literal[
    "normal",
    "wide",
    "crossed",
    "unavailable",
]

PremiumSource = Literal[
    "provided_input",
    "bid_ask_midpoint",
    "last_price",
]


CollateralBasis = Literal[
    "strike_times_contract_size_before_premium"
]

ReturnBasis = Literal[
    "premium_over_gross_strike_collateral"
]

AnnualizationMethod = Literal[
    "simple_non_compounded_365_day"
]

CSP_LIMITATIONS = (
    "Annualized return is a simple, non-compounded approximation.",
    "Fees, taxes, and execution slippage are not included.",
    "Dividend effects and early-assignment risk are not modeled.",
    "Maximum loss assumes the underlying price falls to zero.",
)


@dataclass(frozen=True)
class QuoteMetrics:
    mid_price: float | None
    bid_ask_spread: float | None
    bid_ask_spread_pct: float | None
    quote_status: QuoteStatus


def _coerce_optional_non_negative_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(coerced) or coerced < 0:
        return None

    return coerced


def _coerce_optional_non_negative_int(
    value: object,
) -> int | None:
    coerced = _coerce_optional_non_negative_float(value)

    if coerced is None or not coerced.is_integer():
        return None

    return int(coerced)


def _coerce_optional_bool(value: object) -> bool | None:
    if value is None:
        return None

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {"true", "1"}:
            return True

        if normalized in {"false", "0"}:
            return False

        return None

    try:
        if value == 1:
            return True

        if value == 0:
            return False
    except (TypeError, ValueError):
        return None

    return None


def _prepare_option_contracts(
    option_df,
    *,
    require_contract_symbol: bool,
):
    required_columns = {"strike"}

    if require_contract_symbol:
        required_columns.add("contractSymbol")

    missing_columns = sorted(
        required_columns - set(option_df.columns)
    )
    if missing_columns:
        missing_list = ", ".join(missing_columns)
        raise ValueError(
            f"Options data is missing required columns: {missing_list}."
        )

    prepared = option_df.copy()

    prepared["strike"] = prepared["strike"].map(
        _coerce_optional_non_negative_float
    )
    valid_rows = prepared["strike"].notna() & prepared["strike"].gt(0)

    if require_contract_symbol:
        prepared["contractSymbol"] = prepared["contractSymbol"].map(
            lambda value: (
                value.strip()
                if isinstance(value, str)
                else ""
            )
        )
        valid_rows &= prepared["contractSymbol"].ne("")

    for column in ("openInterest", "volume"):
        if column not in prepared.columns:
            prepared[column] = None

        prepared[column] = prepared[column].map(
            _coerce_optional_non_negative_int
        )

    return prepared.loc[valid_rows].copy()


def _calculate_quote_metrics(
    bid: float | None,
    ask: float | None,
) -> QuoteMetrics:
    if (
        bid is None
        or ask is None
        or bid <= 0
        or ask <= 0
    ):
        return QuoteMetrics(
            mid_price=None,
            bid_ask_spread=None,
            bid_ask_spread_pct=None,
            quote_status="unavailable",
        )

    if ask < bid:
        return QuoteMetrics(
            mid_price=None,
            bid_ask_spread=None,
            bid_ask_spread_pct=None,
            quote_status="crossed",
        )

    mid_price = (bid + ask) / 2
    bid_ask_spread = ask - bid
    bid_ask_spread_pct = bid_ask_spread / mid_price

    quote_status: QuoteStatus = "normal"
    if bid_ask_spread_pct > WIDE_BID_ASK_SPREAD_PCT:
        quote_status = "wide"

    return QuoteMetrics(
        mid_price=mid_price,
        bid_ask_spread=bid_ask_spread,
        bid_ask_spread_pct=bid_ask_spread_pct,
        quote_status=quote_status,
    )


def _get_reference_spot_price(engine: MarketDataEngine, ticker: str) -> float | None:
    price_history = engine.get_price_history(
        ticker=ticker,
        period="5d",
        interval="1d",
    )
    if price_history.empty:
        return None
    return float(price_history["Close"].iloc[-1])


def _choose_relevant_contracts(
    option_df,
    option_type: str,
    limit: int,
    target_strike: float | None,
    reference_price: float | None,
):
    ranked = option_df.copy()

    if target_strike is not None:
        ranked["distance_score"] = (ranked["strike"] - target_strike).abs()
        ranked = ranked.sort_values(
            by=["distance_score", "openInterest", "volume"],
            ascending=[True, False, False],
        )
        return ranked.head(limit).copy()

    if reference_price is not None:
        if option_type == "put":
            preferred = ranked[ranked["strike"] <= reference_price].copy()
            if preferred.empty:
                preferred = ranked.copy()
            preferred["distance_score"] = (preferred["strike"] - reference_price).abs()
            preferred = preferred.sort_values(
                by=["distance_score", "openInterest", "volume"],
                ascending=[True, False, False],
            )
            return preferred.head(limit).copy()

        preferred = ranked[ranked["strike"] >= reference_price].copy()
        if preferred.empty:
            preferred = ranked.copy()
        preferred["distance_score"] = (preferred["strike"] - reference_price).abs()
        preferred = preferred.sort_values(
            by=["distance_score", "openInterest", "volume"],
            ascending=[True, False, False],
        )
        return preferred.head(limit).copy()

    ranked = ranked.sort_values(by=["openInterest", "volume"], ascending=[False, False])
    return ranked.head(limit).copy()


def _choose_expiration(
    expirations: list[str],
    explicit_expiration: str | None,
    min_days_to_expiration: int,
    max_days_to_expiration: int,
) -> tuple[str, str]:
    """
    Choose an expiration date using a simple DTE policy.

    Returns:
        (selected_expiration, selection_reason)
    """
    if explicit_expiration is not None:
        if explicit_expiration not in expirations:
            raise ValueError(
                f"Expiration '{explicit_expiration}' is not available. "
                f"Available expirations include: {expirations[:10]}"
            )
        return explicit_expiration, "user_specified"

    today = date.today()
    dated_expirations: list[tuple[str, int]] = []

    for exp in expirations:
        exp_date = date.fromisoformat(exp)
        dte = (exp_date - today).days
        if dte >= 0:
            dated_expirations.append((exp, dte))

    if not dated_expirations:
        raise ValueError("No non-expired option expirations are available.")

    in_target_window = [
        (exp, dte)
        for exp, dte in dated_expirations
        if min_days_to_expiration <= dte <= max_days_to_expiration
    ]
    if in_target_window:
        selected = min(in_target_window, key=lambda item: item[1])
        return selected[0], f"default_window_{min_days_to_expiration}_{max_days_to_expiration}_dte"

    above_minimum = [
        (exp, dte)
        for exp, dte in dated_expirations
        if dte >= min_days_to_expiration
    ]
    if above_minimum:
        selected = min(above_minimum, key=lambda item: item[1])
        return selected[0], f"nearest_above_min_{min_days_to_expiration}_dte"

    selected = min(dated_expirations, key=lambda item: item[1])
    return selected[0], "nearest_available_fallback"


class OptionsChainInput(BaseModel):
    ticker: str = Field(
        ...,
        description="Stock ticker symbol, for example MSFT or AAPL."
    )
    expiration: str | None = Field(
        default=None,
        description="Option expiration date in YYYY-MM-DD format."
    )
    min_days_to_expiration: int = Field(
        default=7,
        ge=0,
        le=365,
        description="Minimum preferred days to expiration when expiration is not explicitly provided."
    )
    max_days_to_expiration: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Maximum preferred days to expiration when expiration is not explicitly provided."
    )
    option_type: Literal["call", "put"] = Field(
        default="put",
        description="Whether to return call or put contracts."
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of contracts to return."
    )
    target_strike: float | None = Field(
        default=None,
        gt=0,
        description="Optional strike to center the returned contracts around."
    )
    reference_price: float | None = Field(
        default=None,
        gt=0,
        description="Optional underlying price used to prioritize nearby strikes."
    )


class OptionContract(BaseModel):
    contract_symbol: str
    strike: float = Field(..., gt=0)
    last_price: float | None = Field(default=None, ge=0)
    bid: float | None = Field(default=None, ge=0)
    ask: float | None = Field(default=None, ge=0)
    mid_price: float | None = Field(default=None, ge=0)
    bid_ask_spread: float | None = Field(default=None, ge=0)
    bid_ask_spread_pct: float | None = Field(default=None, ge=0)
    quote_status: QuoteStatus
    volume: int | None = Field(default=None, ge=0)
    open_interest: int | None = Field(default=None, ge=0)
    implied_volatility: float | None = Field(default=None, ge=0)
    in_the_money: bool | None = None
    expiration: str
    option_type: str


class OptionsChainOutput(BaseModel):
    ticker: str
    expiration: str
    option_type: str
    contract_count: int
    selection_basis: str
    expiration_selection_basis: str
    contracts: list[OptionContract]
    source: str = "yfinance"


def get_options_chain_tool(args: OptionsChainInput) -> OptionsChainOutput:
    """
    Fetch a filtered options chain for a ticker.

    If no expiration is provided, the nearest available expiration is used.
    Returns a limited list of structured option contracts for the requested side.
    """
    engine = MarketDataEngine()

    expirations = engine.get_option_expirations(args.ticker)
    if not expirations:
        raise ValueError(f"No option expirations found for ticker '{args.ticker}'.")

    expiration, expiration_selection_basis = _choose_expiration(
        expirations=expirations,
        explicit_expiration=args.expiration,
        min_days_to_expiration=args.min_days_to_expiration,
        max_days_to_expiration=args.max_days_to_expiration,
    )

    chain = engine.get_options_chain(args.ticker, expiration)
    option_df = chain["puts"] if args.option_type == "put" else chain["calls"]

    if option_df.empty:
        raise ValueError(
            f"No {args.option_type} contracts found for ticker '{args.ticker}' at expiration '{expiration}'."
        )

    option_df = _prepare_option_contracts(
        option_df,
        require_contract_symbol=True,
    )

    if option_df.empty:
        raise ValueError(
            f"No valid {args.option_type} contracts found for ticker "
            f"'{args.ticker}' at expiration '{expiration}'."
        )

    reference_price = args.reference_price
    if reference_price is None and args.target_strike is None:
        reference_price = _get_reference_spot_price(engine, args.ticker)

    selected = _choose_relevant_contracts(
        option_df=option_df,
        option_type=args.option_type,
        limit=args.limit,
        target_strike=args.target_strike,
        reference_price=reference_price,
    )

    selection_basis = "liquidity"
    if args.target_strike is not None:
        selection_basis = f"nearest_to_target_strike:{args.target_strike}"
    elif reference_price is not None:
        selection_basis = f"nearest_to_reference_price:{reference_price}"

    contracts: list[OptionContract] = []
    for _, row in selected.iterrows():
        bid = _coerce_optional_non_negative_float(row.get("bid"))
        ask = _coerce_optional_non_negative_float(row.get("ask"))
        quote_metrics = _calculate_quote_metrics(bid, ask)
        contracts.append(
            OptionContract(
                contract_symbol=str(row.get("contractSymbol", "")),
                strike=float(row["strike"]),
                last_price=_coerce_optional_non_negative_float(
                    row.get("lastPrice")
                ),
                bid=bid,
                ask=ask,
                mid_price=quote_metrics.mid_price,
                bid_ask_spread=quote_metrics.bid_ask_spread,
                bid_ask_spread_pct=quote_metrics.bid_ask_spread_pct,
                quote_status=quote_metrics.quote_status,
                volume=_coerce_optional_non_negative_int(row.get("volume")),
                open_interest=_coerce_optional_non_negative_int(
                    row.get("openInterest")
                ),
                implied_volatility=_coerce_optional_non_negative_float(
                    row.get("impliedVolatility")
                ),
                in_the_money=_coerce_optional_bool(row.get("inTheMoney")),
                expiration=expiration,
                option_type=args.option_type,
            )
        )

    return OptionsChainOutput(
        ticker=args.ticker.upper(),
        expiration=expiration,
        option_type=args.option_type,
        contract_count=len(contracts),
        selection_basis=selection_basis,
        expiration_selection_basis=expiration_selection_basis,
        contracts=contracts,
        source="yfinance",
    )


class CashSecuredPutInput(BaseModel):
    ticker: str = Field(
        ...,
        description="Stock ticker symbol, for example MSFT or AAPL."
    )
    strike: float = Field(
        ...,
        gt=0,
        description="Put strike price."
    )
    expiration: str = Field(
        ...,
        description="Option expiration date in YYYY-MM-DD format."
    )
    premium: float | None = Field(
        default=None,
        gt=0,
        description=(
            "Optional premium to use directly. If omitted, the tool will "
            "try to infer it from the option chain."
        ),
    )
    contract_size: int = Field(
        default=100,
        gt=0,
        description="Number of shares controlled by one options contract."
    )

    @model_validator(mode="after")
    def validate_premium_below_strike(self) -> "CashSecuredPutInput":
        if self.premium is not None and self.premium >= self.strike:
            raise ValueError(
                "premium must be less than strike."
            )

        return self


class CashSecuredPutOutput(BaseModel):
    ticker: str
    spot_price: float
    spot_price_as_of: str
    spot_price_type: Literal["latest_daily_close"] = "latest_daily_close"
    strike: float
    expiration: str
    days_to_expiration: int
    premium: float
    premium_source: PremiumSource
    premium_quote_status: QuoteStatus | None = None
    premium_warning: str | None = None
    break_even_price: float
    max_profit_dollars: float
    max_loss_dollars: float
    collateral_basis: CollateralBasis = (
        "strike_times_contract_size_before_premium"
    )
    return_basis: ReturnBasis = (
        "premium_over_gross_strike_collateral"
    )
    annualization_method: AnnualizationMethod = (
        "simple_non_compounded_365_day"
    )
    limitations: list[str]
    cash_required_dollars: float
    simple_return: float
    annualized_return: float
    distance_to_strike_pct: float
    distance_to_break_even_pct: float
    contract_size: int
    source: str = "yfinance"


def analyze_cash_secured_put_tool(
    args: CashSecuredPutInput,
) -> CashSecuredPutOutput:
    """
    Analyze a candidate short cash-secured put position.

    If premium is not supplied, the tool uses a valid non-crossed bid-ask
    midpoint when available, otherwise falls back to the last price with a
    warning. The result records the selected premium's source.
    """
    engine = MarketDataEngine()

    price_history = engine.get_price_history(
        ticker=args.ticker,
        period="5d",
        interval="1d",
    )
    spot_snapshot = extract_latest_daily_close(
        price_history,
        args.ticker,
    )
    spot_price = spot_snapshot.price

    premium = args.premium
    premium_source: PremiumSource = "provided_input"
    premium_quote_status: QuoteStatus | None = None
    premium_warning: str | None = None

    if premium is None:
        chain = engine.get_options_chain(args.ticker, args.expiration)
        puts_df = chain["puts"]

        if puts_df.empty:
            raise ValueError(
                f"No put contracts found for ticker '{args.ticker}' at expiration '{args.expiration}'."
            )

        puts_df = _prepare_option_contracts(
            puts_df,
            require_contract_symbol=False,
        )

        if puts_df.empty:
            raise ValueError(
                f"No valid put contracts found for ticker '{args.ticker}' "
                f"at expiration '{args.expiration}'."
            )

        strike_tolerance = 1e-6
        matches = puts_df[(puts_df["strike"] - args.strike).abs() <= strike_tolerance].copy()
        if matches.empty:
            nearby = puts_df.assign(
                distance_to_target=(puts_df["strike"] - args.strike).abs()
            ).sort_values(by=["distance_to_target", "openInterest", "volume"], ascending=[True, False, False])
            nearby_strikes = nearby["strike"].head(10).tolist()
            raise ValueError(
                f"No put contract found for ticker '{args.ticker}' with strike {args.strike} "
                f"and expiration '{args.expiration}'. Closest available strikes: {nearby_strikes}"
            )

        best_match = matches.sort_values(
            by=["openInterest", "volume"],
            ascending=[False, False],
        ).iloc[0]
        bid = _coerce_optional_non_negative_float(best_match.get("bid"))
        ask = _coerce_optional_non_negative_float(best_match.get("ask"))
        last_price = _coerce_optional_non_negative_float(
            best_match.get("lastPrice")
        )
        quote_metrics = _calculate_quote_metrics(bid, ask)
        premium_quote_status = quote_metrics.quote_status

        if quote_metrics.mid_price is not None:
            premium = quote_metrics.mid_price
            premium_source = "bid_ask_midpoint"

            if quote_metrics.quote_status == "wide":
                premium_warning = (
                    "The bid-ask spread exceeds 20% of the midpoint, "
                    "so the midpoint may not be executable."
                )

        elif last_price is not None and last_price > 0:
            premium = last_price
            premium_source = "last_price"

            if quote_metrics.quote_status == "crossed":
                premium_warning = (
                    "The bid-ask quote was crossed, so the last traded "
                    "price was used and may be stale."
                )
            else:
                premium_warning = (
                    "A usable two-sided bid-ask quote was unavailable, "
                    "so the last traded price was used and may be stale."
                )

        else:
            raise ValueError(
                f"No usable premium quote found for ticker '{args.ticker}' "
                f"with strike {args.strike} and expiration "
                f"'{args.expiration}'. Bid, ask, and last price are "
                "unavailable or non-positive."
            )

    if premium is None or premium >= args.strike:
        raise ValueError(
            f"Premium for ticker '{args.ticker}' must be positive "
            "and less than the strike."
        )

    expiration_date = date.fromisoformat(args.expiration)
    today = date.today()
    days_to_expiration = (expiration_date - today).days

    if days_to_expiration <= 0:
        raise ValueError(
            f"Expiration '{args.expiration}' must be in the future."
        )

    break_even = cash_secured_put_break_even(args.strike, premium)
    max_profit = cash_secured_put_max_profit(premium, args.contract_size)
    max_loss = cash_secured_put_max_loss(
        args.strike,
        premium,
        args.contract_size,
    )
    cash_required = cash_secured_put_cash_required(args.strike, args.contract_size)
    simple_ret = simple_return_on_secured_cash(premium, args.strike)
    annualized_ret = annualized_return(simple_ret, days_to_expiration)

    distance_to_strike_pct = (spot_price - args.strike) / spot_price
    distance_to_break_even_pct = (spot_price - break_even) / spot_price

    return CashSecuredPutOutput(
        ticker=args.ticker.upper(),
        spot_price=spot_price,
        spot_price_as_of=spot_snapshot.as_of,
        strike=args.strike,
        expiration=args.expiration,
        days_to_expiration=days_to_expiration,
        premium=float(premium),
        premium_source=premium_source,
        premium_quote_status=premium_quote_status,
        premium_warning=premium_warning,
        break_even_price=break_even,
        max_profit_dollars=max_profit,
        max_loss_dollars=max_loss,
        limitations=list(CSP_LIMITATIONS),
        cash_required_dollars=cash_required,
        simple_return=simple_ret,
        annualized_return=annualized_ret,
        distance_to_strike_pct=distance_to_strike_pct,
        distance_to_break_even_pct=distance_to_break_even_pct,
        contract_size=args.contract_size,
        source="yfinance",
    )
