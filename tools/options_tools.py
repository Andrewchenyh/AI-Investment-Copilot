from typing import Literal
from datetime import date
from pydantic import BaseModel, Field

from analysis.risk_metrics import (
    annualized_return,
    cash_secured_put_break_even,
    cash_secured_put_cash_required,
    cash_secured_put_max_profit,
    simple_return_on_secured_cash,
)
from tools.market_data import MarketDataEngine


def _coerce_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
    ranked["strike"] = ranked["strike"].astype(float)

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
    strike: float
    last_price: float
    bid: float
    ask: float
    volume: int
    open_interest: int
    implied_volatility: float | None = None
    in_the_money: bool
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
        contracts.append(
            OptionContract(
                contract_symbol=str(row.get("contractSymbol", "")),
                strike=_coerce_float(row.get("strike")),
                last_price=_coerce_float(row.get("lastPrice")),
                bid=_coerce_float(row.get("bid")),
                ask=_coerce_float(row.get("ask")),
                volume=_coerce_int(row.get("volume")),
                open_interest=_coerce_int(row.get("openInterest")),
                implied_volatility=(
                    _coerce_float(row.get("impliedVolatility"))
                    if row.get("impliedVolatility") is not None
                    else None
                ),
                in_the_money=bool(row.get("inTheMoney", False)),
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
        ge=0,
        description="Optional premium to use directly. If omitted, the tool will try to infer it from the option chain."
    )
    contract_size: int = Field(
        default=100,
        gt=0,
        description="Number of shares controlled by one options contract."
    )


class CashSecuredPutOutput(BaseModel):
    ticker: str
    spot_price: float
    strike: float
    expiration: str
    days_to_expiration: int
    premium: float
    break_even_price: float
    max_profit_dollars: float
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

    If premium is not supplied, the tool looks up the matching put contract
    by strike and expiration and uses the contract's mid price when possible,
    otherwise falls back to last price.
    """
    engine = MarketDataEngine()

    price_history = engine.get_price_history(
        ticker=args.ticker,
        period="5d",
        interval="1d",
    )
    if price_history.empty:
        raise ValueError(f"No price data found for ticker '{args.ticker}'.")

    spot_price = float(price_history["Close"].iloc[-1])

    premium = args.premium
    if premium is None:
        chain = engine.get_options_chain(args.ticker, args.expiration)
        puts_df = chain["puts"]

        if puts_df.empty:
            raise ValueError(
                f"No put contracts found for ticker '{args.ticker}' at expiration '{args.expiration}'."
            )

        puts_df = puts_df.copy()
        puts_df["strike"] = puts_df["strike"].astype(float)
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
        bid = _coerce_float(best_match.get("bid"))
        ask = _coerce_float(best_match.get("ask"))
        last_price = _coerce_float(best_match.get("lastPrice"))

        if bid > 0 and ask > 0:
            premium = (bid + ask) / 2
        elif last_price > 0:
            premium = last_price
        else:
            premium = 0.0

    expiration_date = date.fromisoformat(args.expiration)
    today = date.today()
    days_to_expiration = (expiration_date - today).days

    if days_to_expiration <= 0:
        raise ValueError(
            f"Expiration '{args.expiration}' must be in the future."
        )

    break_even = cash_secured_put_break_even(args.strike, premium)
    max_profit = cash_secured_put_max_profit(premium, args.contract_size)
    cash_required = cash_secured_put_cash_required(args.strike, args.contract_size)
    simple_ret = simple_return_on_secured_cash(premium, args.strike)
    annualized_ret = annualized_return(simple_ret, days_to_expiration)

    distance_to_strike_pct = (spot_price - args.strike) / spot_price
    distance_to_break_even_pct = (spot_price - break_even) / spot_price

    return CashSecuredPutOutput(
        ticker=args.ticker.upper(),
        spot_price=spot_price,
        strike=args.strike,
        expiration=args.expiration,
        days_to_expiration=days_to_expiration,
        premium=float(premium),
        break_even_price=break_even,
        max_profit_dollars=max_profit,
        cash_required_dollars=cash_required,
        simple_return=simple_ret,
        annualized_return=annualized_ret,
        distance_to_strike_pct=distance_to_strike_pct,
        distance_to_break_even_pct=distance_to_break_even_pct,
        contract_size=args.contract_size,
        source="yfinance",
    )
