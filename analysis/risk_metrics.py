def cash_secured_put_break_even(strike: float, premium: float) -> float:
    """
    Break-even price for a short cash-secured put at expiration.
    """
    return strike - premium


def cash_secured_put_max_profit(premium: float, contract_size: int = 100) -> float:
    """
    Maximum profit for one short put contract.
    """
    return premium * contract_size


def cash_secured_put_max_loss(
    strike: float,
    premium: float,
    contract_size: int = 100,
) -> float:
    """
    Maximum loss for a short cash-secured put if the underlying falls to zero.
    """
    return (strike - premium) * contract_size


def cash_secured_put_cash_required(strike: float, contract_size: int = 100) -> float:
    """
    Cash required to secure assignment on one short put contract.
    """
    return strike * contract_size


def simple_return_on_secured_cash(
    premium: float,
    strike: float,
) -> float:
    """
    Simple return on secured cash for one contract, expressed as a decimal.
    """
    if strike <= 0:
        raise ValueError("Strike must be positive.")
    return premium / strike


def annualized_return(simple_return: float, days_to_expiration: int) -> float:
    """
    Simple annualized return approximation.
    """
    if days_to_expiration <= 0:
        raise ValueError("days_to_expiration must be positive.")
    return simple_return * (365 / days_to_expiration)


def cash_secured_put_profit_at_expiration(
    underlying_price: float,
    strike: float,
    premium: float,
    contract_size: int = 100,
) -> float:
    """
    Calculate the dollar profit or loss for one short cash-secured
    put contract at expiration.

    Positive values represent profit. Negative values represent loss.
    """
    if underlying_price < 0:
        raise ValueError(
            "underlying_price must be non-negative."
        )

    if strike <= 0:
        raise ValueError("strike must be positive.")

    if premium <= 0:
        raise ValueError("premium must be positive.")

    if premium >= strike:
        raise ValueError(
            "premium must be less than strike."
        )

    if contract_size <= 0:
        raise ValueError(
            "contract_size must be positive."
        )

    intrinsic_value = max(
        strike - underlying_price,
        0.0,
    )

    return (premium - intrinsic_value) * contract_size