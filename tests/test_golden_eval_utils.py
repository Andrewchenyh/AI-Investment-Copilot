from evals.run_golden_eval import (
    contains_all_expected_tools,
    contains_required_mentions,
    extract_tools_used,
    contains_required_tool_calls,
    evaluate_record,
    find_missing_answer_concepts,
)


def test_extract_tools_used() -> None:
    trace = [
        {"step": 1, "thought": "Need price"},
        {"tool_name": "get_current_price", "observation": {}},
        {"tool_name": "get_options_chain", "observation": {}},
    ]

    assert extract_tools_used(trace) == [
        "get_current_price",
        "get_options_chain",
    ]


def test_contains_all_expected_tools() -> None:
    assert contains_all_expected_tools(
        ["get_current_price", "get_options_chain"],
        ["get_current_price"],
    )
    assert not contains_all_expected_tools(
        ["get_current_price"],
        ["get_current_price", "get_options_chain"],
    )


def test_contains_required_mentions_is_case_insensitive() -> None:
    assert contains_required_mentions(
        "The ORCL strike is 170.",
        ["orcl", "170"],
    )
    assert not contains_required_mentions(
        "The ORCL strike is 170.",
        ["orcl", "expiration"],
    )


def test_required_tool_calls_match_arguments_and_success() -> None:
    trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {
                "ticker": "orcl",
                "option_type": "put",
                "target_strike": 170.0,
            },
            "success": True,
        }
    ]
    requirements = [
        {
            "tool_name": "get_options_chain",
            "args_subset": {
                "ticker": "ORCL",
                "target_strike": 170,
            },
            "outcome": "success",
            "min_calls": 1,
        }
    ]

    assert contains_required_tool_calls(trace, requirements)


def test_required_tool_calls_reject_wrong_args_or_outcome() -> None:
    wrong_args_trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {
                "ticker": "ORCL",
                "target_strike": 175,
            },
            "success": True,
        }
    ]
    wrong_outcome_trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {
                "ticker": "ORCL",
                "target_strike": 170,
            },
            "success": False,
        }
    ]
    requirements = [
        {
            "tool_name": "get_options_chain",
            "args_subset": {
                "ticker": "ORCL",
                "target_strike": 170,
            },
            "outcome": "success",
            "min_calls": 1,
        }
    ]

    assert not contains_required_tool_calls(
        wrong_args_trace,
        requirements,
    )
    assert not contains_required_tool_calls(
        wrong_outcome_trace,
        requirements,
    )


def test_required_tool_calls_support_expected_failures() -> None:
    trace = [
        {
            "tool_name": "get_current_price",
            "tool_args": {"ticker": "FAKEFAKE"},
            "success": False,
        }
    ]
    requirements = [
        {
            "tool_name": "get_current_price",
            "args_subset": {"ticker": "FAKEFAKE"},
            "outcome": "failure",
            "min_calls": 1,
        }
    ]

    assert contains_required_tool_calls(trace, requirements)
    any_outcome_requirements = [
        {
            **requirements[0],
            "outcome": "any",
        }
    ]
    assert contains_required_tool_calls(trace, any_outcome_requirements)


def test_required_tool_calls_require_each_expected_ticker() -> None:
    trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "ORCL"},
            "success": True,
        }
    ]
    requirements = [
        {
            "tool_name": "get_options_chain",
            "args_subset": {"ticker": "ORCL"},
        },
        {
            "tool_name": "get_options_chain",
            "args_subset": {"ticker": "MSFT"},
        },
    ]

    assert not contains_required_tool_calls(trace, requirements)

    trace.append(
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "MSFT"},
            "success": True,
        }
    )

    assert contains_required_tool_calls(trace, requirements)
    assert contains_required_tool_calls(
        trace,
        [
            {
                "tool_name": "get_options_chain",
                "outcome": "success",
                "min_calls": 2,
            }
        ],
    )


def test_evaluate_record_applies_required_tool_calls() -> None:
    class FakeAgent:
        def ask(self, user_query: str, trace_id: str) -> dict:
            return {
                "status": "success",
                "answer": "ORCL analysis completed.",
                "trace": [
                    {
                        "tool_name": "get_options_chain",
                        "tool_args": {"ticker": "ORCL"},
                        "success": False,
                    }
                ],
            }

    record = {
        "id": "trace_contract_test",
        "category": "test",
        "query": "Analyze ORCL.",
        "expected_tools": ["get_options_chain"],
        "required_tool_calls": [
            {
                "tool_name": "get_options_chain",
                "args_subset": {"ticker": "ORCL"},
                "outcome": "success",
                "min_calls": 1,
            }
        ],
        "must_preserve": [],
        "must_mention": [],
    }

    result = evaluate_record(record, FakeAgent())

    assert result["checks"]["tool_usage_pass"] is True
    assert result["checks"]["required_tool_calls_pass"] is False
    assert result["passed"] is False


def test_answer_concepts_accept_alternatives_and_report_missing() -> None:
    concepts = [
        {
            "name": "premium",
            "alternatives": [
                "premium",
                "credit received",
            ],
        },
        {
            "name": "expiration",
            "alternatives": [
                "expiration",
                "expires",
                "expiring",
            ],
        },
    ]

    assert find_missing_answer_concepts(
        "The trade provides a credit received of $1.78.",
        concepts,
    ) == ["expiration"]

    assert find_missing_answer_concepts(
        "The trade provides a $1.78 credit received "
        "and expires next Friday.",
        concepts,
    ) == []


def test_evaluate_record_applies_answer_concepts() -> None:
    class FakeAgent:
        def ask(self, user_query: str, trace_id: str) -> dict:
            return {
                "status": "success",
                "answer": "AAPL RSI is currently neutral.",
                "trace": [
                    {
                        "tool_name": "analyze_technical_indicators",
                        "tool_args": {"ticker": "AAPL"},
                        "success": True,
                    },
                ],
            }

    record = {
        "id": "answer_concept_test",
        "category": "technical_analysis",
        "query": "Analyze AAPL.",
        "expected_tools": ["analyze_technical_indicators"],
        "required_tool_calls": [],
        "required_answer_concepts": [
            {
                "name": "rsi",
                "alternatives": ["RSI"],
            },
            {
                "name": "moving_average",
                "alternatives": ["50-day", "SMA-50"],
            },
        ],
        "must_preserve": [],
        "must_mention": [],
    }

    result = evaluate_record(record, FakeAgent())

    assert result["checks"]["tool_usage_pass"] is True
    assert result["checks"]["answer_concepts_pass"] is False
    assert result["missing_answer_concepts"] == ["moving_average"]
    assert result["passed"] is False
