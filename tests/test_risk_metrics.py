import pytest

from analysis.risk_metrics import (
    annualized_return,
    cash_secured_put_break_even,
    cash_secured_put_cash_required,
    cash_secured_put_max_loss,
    cash_secured_put_max_profit,
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
