from evals.run_golden_eval import (
    evaluate_record,
    extract_tools_used,
    find_missing_answer_concepts,
    find_missing_answer_literals,
    find_unsatisfied_tool_calls,
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


def test_answer_literals_are_case_insensitive_and_report_missing() -> None:
    assert find_missing_answer_literals(
        "The ORCL strike is 170.",
        ["orcl", "170"],
    ) == []
    assert find_missing_answer_literals(
        "The ORCL strike is 170.",
        ["ORCL", "expiration"],
    ) == ["expiration"]
    assert find_missing_answer_literals(
        "The ORCL strike is 1700.",
        ["170"],
    ) == ["170"]


def test_tool_contract_matches_arguments_and_success() -> None:
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

    assert find_unsatisfied_tool_calls(trace, requirements) == []


def test_tool_contract_reports_wrong_args_or_outcome() -> None:
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
    requirement = {
        "tool_name": "get_options_chain",
        "args_subset": {
            "ticker": "ORCL",
            "target_strike": 170,
        },
        "outcome": "success",
        "min_calls": 1,
    }
    expected_diagnostic = {
        **requirement,
        "matched_calls": 0,
    }

    assert find_unsatisfied_tool_calls(
        wrong_args_trace,
        [requirement],
    ) == [expected_diagnostic]
    assert find_unsatisfied_tool_calls(
        wrong_outcome_trace,
        [requirement],
    ) == [expected_diagnostic]


def test_tool_contract_supports_expected_failures_and_any_outcome() -> None:
    trace = [
        {
            "tool_name": "get_current_price",
            "tool_args": {"ticker": "FAKEFAKE"},
            "success": False,
        }
    ]
    failure_requirement = {
        "tool_name": "get_current_price",
        "args_subset": {"ticker": "FAKEFAKE"},
        "outcome": "failure",
        "min_calls": 1,
    }

    assert find_unsatisfied_tool_calls(
        trace,
        [failure_requirement],
    ) == []
    assert find_unsatisfied_tool_calls(
        trace,
        [{**failure_requirement, "outcome": "any"}],
    ) == []


def test_tool_contract_requires_each_ticker_and_minimum_call_count() -> None:
    trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "ORCL"},
            "success": True,
        }
    ]
    orcl_requirement = {
        "tool_name": "get_options_chain",
        "args_subset": {"ticker": "ORCL"},
        "outcome": "success",
        "min_calls": 1,
    }
    msft_requirement = {
        "tool_name": "get_options_chain",
        "args_subset": {"ticker": "MSFT"},
        "outcome": "success",
        "min_calls": 1,
    }

    assert find_unsatisfied_tool_calls(
        trace,
        [orcl_requirement, msft_requirement],
    ) == [{**msft_requirement, "matched_calls": 0}]

    trace.append(
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "MSFT"},
            "success": True,
        }
    )

    assert find_unsatisfied_tool_calls(
        trace,
        [orcl_requirement, msft_requirement],
    ) == []
    assert find_unsatisfied_tool_calls(
        trace,
        [
            {
                "tool_name": "get_options_chain",
                "args_subset": {},
                "outcome": "success",
                "min_calls": 2,
            }
        ],
    ) == []


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

    requirement = {
        "tool_name": "get_options_chain",
        "args_subset": {"ticker": "ORCL"},
        "outcome": "success",
        "min_calls": 1,
    }
    record = {
        "id": "trace_contract_test",
        "category": "test",
        "query": "Analyze ORCL.",
        "required_tool_calls": [requirement],
        "required_answer_literals": ["ORCL"],
        "required_answer_concepts": [
            {"name": "analysis", "alternatives": ["analysis"]}
        ],
    }

    result = evaluate_record(record, FakeAgent())

    assert result["checks"]["required_tool_calls_pass"] is False
    assert result["unsatisfied_tool_calls"] == [
        {**requirement, "matched_calls": 0}
    ]
    assert result["passed"] is False


def test_answer_concepts_accept_alternatives_and_report_missing() -> None:
    concepts = [
        {
            "name": "premium",
            "alternatives": ["premium", "credit received"],
        },
        {
            "name": "expiration",
            "alternatives": ["expiration", "expires", "expiring"],
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


def test_evaluate_record_applies_answer_contracts() -> None:
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
        "id": "answer_contract_test",
        "category": "technical_analysis",
        "query": "Analyze AAPL.",
        "required_tool_calls": [
            {
                "tool_name": "analyze_technical_indicators",
                "args_subset": {"ticker": "AAPL"},
                "outcome": "success",
                "min_calls": 1,
            }
        ],
        "required_answer_literals": ["AAPL", "50-day"],
        "required_answer_concepts": [
            {"name": "rsi", "alternatives": ["RSI"]},
            {
                "name": "moving_average",
                "alternatives": ["50-day", "SMA-50"],
            },
        ],
    }

    result = evaluate_record(record, FakeAgent())

    assert result["checks"]["answer_literals_pass"] is False
    assert result["missing_answer_literals"] == ["50-day"]
    assert result["checks"]["answer_concepts_pass"] is False
    assert result["missing_answer_concepts"] == ["moving_average"]
    assert result["passed"] is False


def test_evaluate_record_isolates_agent_exceptions() -> None:
    class FailingAgent:
        def ask(self, user_query: str, trace_id: str) -> dict:
            raise RuntimeError("provider unavailable")

    record = {
        "id": "agent_error_test",
        "category": "technical_analysis",
        "query": "Analyze AAPL.",
        "required_tool_calls": [
            {
                "tool_name": "analyze_technical_indicators",
                "args_subset": {"ticker": "AAPL"},
                "outcome": "success",
                "min_calls": 1,
            }
        ],
        "required_answer_literals": ["AAPL"],
        "required_answer_concepts": [
            {"name": "rsi", "alternatives": ["RSI"]}
        ],
    }

    result = evaluate_record(record, FailingAgent())

    assert result["status"] == "error"
    assert result["error"] == "RuntimeError: provider unavailable"
    assert result["checks"]["status_pass"] is False
    assert result["missing_answer_literals"] == ["AAPL"]
    assert result["missing_answer_concepts"] == ["rsi"]
    assert result["passed"] is False


def test_evaluate_record_isolates_optional_judge_errors() -> None:
    class FakeAgent:
        def ask(self, user_query: str, trace_id: str) -> dict:
            return {
                "status": "success",
                "answer": "AAPL RSI analysis.",
                "trace": [
                    {
                        "tool_name": "analyze_technical_indicators",
                        "tool_args": {"ticker": "AAPL"},
                        "success": True,
                    }
                ],
            }

    class FailingJudge:
        def score(self, query: str, answer: str, trace: list[dict]):
            raise RuntimeError("judge unavailable")

    record = {
        "id": "judge_error_test",
        "category": "technical_analysis",
        "query": "Analyze AAPL.",
        "required_tool_calls": [
            {
                "tool_name": "analyze_technical_indicators",
                "args_subset": {"ticker": "AAPL"},
                "outcome": "success",
                "min_calls": 1,
            }
        ],
        "required_answer_literals": ["AAPL"],
        "required_answer_concepts": [
            {"name": "rsi", "alternatives": ["RSI"]}
        ],
    }

    result = evaluate_record(
        record,
        FakeAgent(),
        judge=FailingJudge(),  # type: ignore[arg-type]
    )

    assert result["passed"] is True
    assert result["judge_score"] is None
    assert result["judge_error"] == "RuntimeError: judge unavailable"
