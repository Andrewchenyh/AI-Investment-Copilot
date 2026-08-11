import re

import pytest

from evals.concept_patterns import (
    ANSWER_CONCEPT_PATTERNS,
    ANSWER_CONCEPT_PATTERN_TEXT,
)


def concept_matches(concept_name: str, answer: str) -> bool:
    return any(
        pattern.search(answer) is not None
        for pattern in ANSWER_CONCEPT_PATTERNS[concept_name]
    )


def test_compiled_catalog_matches_text_catalog() -> None:
    assert ANSWER_CONCEPT_PATTERNS.keys() == (
        ANSWER_CONCEPT_PATTERN_TEXT.keys()
    )

    for concept_name, pattern_texts in (
        ANSWER_CONCEPT_PATTERN_TEXT.items()
    ):
        compiled_patterns = ANSWER_CONCEPT_PATTERNS[concept_name]

        assert pattern_texts
        assert all(pattern.strip() for pattern in pattern_texts)
        assert tuple(
            pattern.pattern
            for pattern in compiled_patterns
        ) == pattern_texts
        assert all(
            pattern.flags & re.IGNORECASE
            for pattern in compiled_patterns
        )


@pytest.mark.parametrize(
    ("answer", "concept_name"),
    [
        (
            "As of 2026-08-07, ORCL closed at 147.02.",
            "spot_price",
        ),
        (
            "The stock price of MSFT is 499.99.",
            "spot_price",
        ),
        (
            "The option uses an exercise price of $170.",
            "strike",
        ),
        (
            "The contract expires next Friday.",
            "expiration",
        ),
        (
            "The 2026-08-21 145.00 strike put offers a midpoint.",
            "expiration",
        ),
        (
            "The 2026-08-21 $145-strike put offers a midpoint.",
            "expiration",
        ),
        (
            "Cash-Secured Put Analysis (Strike 500, Exp 2026-08-19)",
            "expiration",
        ),
        (
            "Selected contract: Exp. 2026-08-19, strike $500.",
            "expiration",
        ),
        (
            "The selected contract has 32 days to expiration.",
            "selected_dte",
        ),
        (
            "The option has 32 DTE.",
            "selected_dte",
        ),
        (
            "Simple Return: 6.69% over 31 days.",
            "selected_dte",
        ),
        (
            "The position provides a credit received of $3.60.",
            "premium",
        ),
        (
            "Several premiums are available in the selected sample.",
            "premium",
        ),
        (
            "Its break–even price is $136.40.",
            "break_even",
        ),
        (
            "$14,200 USD is required to collateralize the contract.",
            "cash_required",
        ),
        (
            "This position requires $17,000 in cash.",
            "cash_required",
        ),
        (
            "The RSI (14) is currently neutral.",
            "rsi_14",
        ),
        (
            "The 14-period RSI is currently neutral.",
            "rsi_14",
        ),
        (
            "The 50-day simple moving average is $309.79.",
            "sma_50",
        ),
        (
            "The SMA-50 is $309.79.",
            "sma_50",
        ),
        (
            "The 30-day annualized volatility is 60.59%.",
            "volatility_measure",
        ),
        (
            "The calculation uses a 30 trading-day sample.",
            "lookback_period",
        ),
        (
            "The result is based on 30 trading days of data.",
            "lookback_period",
        ),
        (
            "ORCL offers a better risk buffer than MSFT.",
            "comparison",
        ),
        (
            "No market data is available for FAKEFAKE.",
            "data_unavailable",
        ),
        (
            "I am unable to retrieve a valid quote.",
            "data_unavailable",
        ),
        (
            "The system could not find any price data for this ticker.",
            "data_unavailable",
        ),
        (
            "The system couldn't fetch valid market data.",
            "data_unavailable",
        ),
        (
            "No price data could be retrieved for FAKEFAKE.",
            "data_unavailable",
        ),
        (
            "No market data could be fetched for this ticker.",
            "data_unavailable",
        ),
        (
            "No market data, including current price or technical "
            "indicators, is available for this ticker.",
            "data_unavailable",
        ),
        (
            "No data, such as a current quote, was found for FAKEFAKE.",
            "data_unavailable",
        ),
    ],
)
def test_concept_patterns_accept_expected_language_variants(
    answer: str,
    concept_name: str,
) -> None:
    assert concept_matches(concept_name, answer)


@pytest.mark.parametrize(
    ("answer", "concept_name"),
    [
        (
            "The price could move significantly.",
            "spot_price",
        ),
        (
            "The requested range is 30 to 60 days.",
            "selected_dte",
        ),
        (
            "Expiration: September 11, 2026.",
            "selected_dte",
        ),
        (
            "As of 2026-08-10, ORCL is trading at $149.80.",
            "expiration",
        ),
        (
            "The expected return is 10%.",
            "expiration",
        ),
        (
            "Exp 30 days was requested.",
            "expiration",
        ),
        (
            "Market data is available for ORCL.",
            "data_unavailable",
        ),
        (
            "I could not find a favorable contract.",
            "data_unavailable",
        ),
        (
            "I am unable to analyze this unclear request.",
            "data_unavailable",
        ),
        (
            "No market data, including current price, was requested.",
            "data_unavailable",
        ),
        (
            "Both tickers have option contracts.",
            "comparison",
        ),
        (
            "The RSI is currently neutral.",
            "rsi_14",
        ),
        (
            "The moving average is rising.",
            "sma_50",
        ),
    ],
)
def test_concept_patterns_reject_missing_concepts(
    answer: str,
    concept_name: str,
) -> None:
    assert not concept_matches(concept_name, answer)
