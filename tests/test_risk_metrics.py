import pytest

from analysis.risk_metrics import (
    annualized_return,
    cash_secured_put_break_even,
    cash_secured_put_cash_required,
    cash_secured_put_max_loss,
    cash_secured_put_max_profit,
    cash_secured_put_profit_at_expiration,
    simple_return_on_secured_cash,
)


def test_cash_secured_put_break_even() -> None:
    assert cash_secured_put_break_even(strike=100, premium=3.5) == 96.5


def test_cash_secured_put_max_profit() -> None:
    assert cash_secured_put_max_profit(premium=2.25, contract_size=100) == 225


def test_cash_secured_put_max_loss() -> None:
    assert (
        cash_secured_put_max_loss(
            strike=180,
            premium=3.30,
            contract_size=100,
        )
        == 17670
    )


def test_cash_secured_put_cash_required() -> None:
    assert cash_secured_put_cash_required(strike=150, contract_size=100) == 15000


@pytest.mark.parametrize(
    ("underlying_price", "expected_profit"),
    [
        (200.0, 330.0),
        (180.0, 330.0),
        (176.7, 0.0),
        (170.0, -670.0),
        (0.0, -17_670.0),
    ],
)
def test_cash_secured_put_profit_at_expiration(
    underlying_price: float,
    expected_profit: float,
) -> None:
    result = cash_secured_put_profit_at_expiration(
        underlying_price=underlying_price,
        strike=180.0,
        premium=3.30,
        contract_size=100,
    )

    assert result == pytest.approx(
        expected_profit,
        abs=1e-9,
    )


def test_cash_secured_put_payoff_matches_existing_risk_metrics() -> None:
    strike = 180.0
    premium = 3.30
    contract_size = 100
    break_even = cash_secured_put_break_even(strike, premium)

    assert cash_secured_put_profit_at_expiration(
        underlying_price=strike,
        strike=strike,
        premium=premium,
        contract_size=contract_size,
    ) == cash_secured_put_max_profit(premium, contract_size)

    assert cash_secured_put_profit_at_expiration(
        underlying_price=break_even,
        strike=strike,
        premium=premium,
        contract_size=contract_size,
    ) == pytest.approx(0.0, abs=1e-9)

    assert cash_secured_put_profit_at_expiration(
        underlying_price=0.0,
        strike=strike,
        premium=premium,
        contract_size=contract_size,
    ) == -cash_secured_put_max_loss(
        strike,
        premium,
        contract_size,
    )


@pytest.mark.parametrize(
    ("overrides", "error_message"),
    [
        ({"underlying_price": -1.0}, "underlying_price must be non-negative"),
        ({"strike": 0.0}, "strike must be positive"),
        ({"premium": 0.0}, "premium must be positive"),
        ({"premium": 180.0}, "premium must be less than strike"),
        ({"contract_size": 0}, "contract_size must be positive"),
    ],
)
def test_cash_secured_put_profit_rejects_invalid_inputs(
    overrides: dict,
    error_message: str,
) -> None:
    inputs = {
        "underlying_price": 180.0,
        "strike": 180.0,
        "premium": 3.30,
        "contract_size": 100,
    }
    inputs.update(overrides)

    with pytest.raises(ValueError, match=error_message):
        cash_secured_put_profit_at_expiration(**inputs)


def test_simple_return_on_secured_cash() -> None:
    result = simple_return_on_secured_cash(premium=3, strike=100)
    assert result == 0.03


def test_simple_return_requires_positive_strike() -> None:
    with pytest.raises(ValueError, match="Strike must be positive"):
        simple_return_on_secured_cash(premium=3, strike=0)


def test_annualized_return() -> None:
    result = annualized_return(simple_return=0.02, days_to_expiration=30)
    assert result == pytest.approx(0.2433333333)


def test_annualized_return_requires_positive_dte() -> None:
    with pytest.raises(ValueError, match="days_to_expiration must be positive"):
        annualized_return(simple_return=0.02, days_to_expiration=0)
