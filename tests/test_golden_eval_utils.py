import pytest

from evals.run_golden_eval import (
    evaluate_record,
    evaluate_records,
    extract_tools_used,
    find_missing_answer_concepts,
    find_missing_answer_literals,
    find_unsatisfied_answer_literal_groups,
    find_unsatisfied_tool_calls,
)


def evaluation_record(record_id: str) -> dict:
    return {
        "id": record_id,
        "category": "test",
        "query": f"Analyze {record_id}.",
        "required_tool_calls": [],
        "required_answer_literals": [],
        "required_answer_concepts": ["spot_price"],
    }


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


@pytest.mark.parametrize(
    "answer",
    [
        "Oracle is trading at 151.05.",
        "ORCL is trading at 151.05.",
        "orcl is trading at 151.05.",
    ],
)
def test_answer_literal_group_accepts_any_alternative(
    answer: str,
) -> None:
    assert find_unsatisfied_answer_literal_groups(
        answer,
        [["Oracle", "ORCL"]],
    ) == []


def test_answer_literal_groups_require_one_match_from_every_group() -> None:
    groups = [
        ["Oracle", "ORCL"],
        ["Microsoft", "MSFT"],
    ]

    assert find_unsatisfied_answer_literal_groups(
        "ORCL is trading at 151.05.",
        groups,
    ) == [["Microsoft", "MSFT"]]


@pytest.mark.parametrize(
    ("answer", "expected_pass", "expected_unsatisfied"),
    [
        ("ORCL current price is 151.05.", True, []),
        ("Oracle current price is 151.05.", True, []),
        (
            "The company current price is 151.05.",
            False,
            [["Oracle", "ORCL"]],
        ),
    ],
)
def test_evaluate_record_applies_answer_literal_groups(
    answer: str,
    expected_pass: bool,
    expected_unsatisfied: list[list[str]],
) -> None:
    class FakeAgent:
        def ask(self, user_query: str, trace_id: str) -> dict:
            return {
                "status": "success",
                "answer": answer,
                "trace": [],
            }

    record = {
        "id": "literal_group_test",
        "category": "query_understanding",
        "query": "Analyze Oracle.",
        "required_tool_calls": [],
        "required_answer_literals": [],
        "required_answer_literal_groups": [["Oracle", "ORCL"]],
        "required_answer_concepts": ["spot_price"],
    }

    result = evaluate_record(record, FakeAgent())

    assert result["checks"]["answer_literals_pass"] is expected_pass
    assert result["required_answer_literal_groups"] == [
        ["Oracle", "ORCL"]
    ]
    assert result["unsatisfied_answer_literal_groups"] == (
        expected_unsatisfied
    )
    assert result["passed"] is expected_pass


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
                "answer": "ORCL current price analysis completed.",
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
        "required_answer_concepts": ["spot_price"],
    }

    result = evaluate_record(record, FakeAgent())

    assert result["checks"]["required_tool_calls_pass"] is False
    assert result["unsatisfied_tool_calls"] == [
        {**requirement, "matched_calls": 0}
    ]
    assert result["passed"] is False


def test_answer_concepts_accept_patterns_and_report_missing() -> None:
    concepts = ["premium", "expiration"]

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
                "answer": "AAPL RSI 14 is currently neutral.",
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
        "required_answer_concepts": ["rsi_14", "sma_50"],
    }

    result = evaluate_record(record, FakeAgent())

    assert result["checks"]["answer_literals_pass"] is False
    assert result["missing_answer_literals"] == ["50-day"]
    assert result["checks"]["answer_concepts_pass"] is False
    assert result["missing_answer_concepts"] == ["sma_50"]
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
        "required_answer_concepts": ["rsi_14"],
    }

    result = evaluate_record(record, FailingAgent())

    assert result["status"] == "error"
    assert result["error"] == "RuntimeError: provider unavailable"
    assert result["checks"]["status_pass"] is False
    assert result["missing_answer_literals"] == ["AAPL"]
    assert result["missing_answer_concepts"] == ["rsi_14"]
    assert result["passed"] is False


def test_evaluate_record_isolates_optional_judge_errors() -> None:
    class FakeAgent:
        def ask(self, user_query: str, trace_id: str) -> dict:
            return {
                "status": "success",
                "answer": "AAPL RSI 14 analysis.",
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
        "required_answer_concepts": ["rsi_14"],
    }

    result = evaluate_record(
        record,
        FakeAgent(),
        judge=FailingJudge(),  # type: ignore[arg-type]
    )

    assert result["passed"] is True
    assert result["judge_score"] is None
    assert result["judge_error"] == "RuntimeError: judge unavailable"


def test_evaluate_records_sleeps_only_between_cases(capsys) -> None:
    class FakeAgent:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def ask(self, user_query: str, trace_id: str) -> dict:
            self.queries.append(user_query)
            return {
                "status": "success",
                "answer": "The current price is available.",
                "trace": [],
            }

    agent = FakeAgent()
    sleep_calls: list[float] = []
    records = [
        evaluation_record("first"),
        evaluation_record("second"),
        evaluation_record("third"),
    ]

    results = evaluate_records(
        records,
        agent,
        delay_seconds=2.5,
        sleep_fn=sleep_calls.append,
    )

    assert [result["id"] for result in results] == [
        "first",
        "second",
        "third",
    ]
    assert agent.queries == [
        "Analyze first.",
        "Analyze second.",
        "Analyze third.",
    ]
    assert sleep_calls == [2.5, 2.5]
    assert capsys.readouterr().out.count("Waiting 2.5s") == 2


def test_evaluate_records_skips_zero_delay() -> None:
    class FakeAgent:
        def ask(self, user_query: str, trace_id: str) -> dict:
            return {
                "status": "success",
                "answer": "The current price is available.",
                "trace": [],
            }

    def fail_if_called(delay_seconds: float) -> None:
        raise AssertionError(
            f"sleep called unexpectedly with {delay_seconds}"
        )

    results = evaluate_records(
        [
            evaluation_record("first"),
            evaluation_record("second"),
        ],
        FakeAgent(),
        delay_seconds=0,
        sleep_fn=fail_if_called,
    )

    assert len(results) == 2


def test_evaluate_records_continues_after_failed_case() -> None:
    class IntermittentAgent:
        def __init__(self) -> None:
            self.call_count = 0

        def ask(self, user_query: str, trace_id: str) -> dict:
            self.call_count += 1
            if self.call_count == 1:
                raise RuntimeError("provider unavailable")

            return {
                "status": "success",
                "answer": "The current price is available.",
                "trace": [],
            }

    sleep_calls: list[float] = []
    results = evaluate_records(
        [
            evaluation_record("failed"),
            evaluation_record("successful"),
        ],
        IntermittentAgent(),
        delay_seconds=1,
        sleep_fn=sleep_calls.append,
    )

    assert [result["passed"] for result in results] == [
        False,
        True,
    ]
    assert sleep_calls == [1]


@pytest.mark.parametrize(
    "delay_seconds",
    [
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_evaluate_records_rejects_invalid_delay(
    delay_seconds: float,
) -> None:
    class UnusedAgent:
        def ask(self, user_query: str, trace_id: str) -> dict:
            raise AssertionError("agent should not be called")

    with pytest.raises(
        ValueError,
        match="delay_seconds must be finite and non-negative",
    ):
        evaluate_records(
            [evaluation_record("unused")],
            UnusedAgent(),
            delay_seconds=delay_seconds,
            sleep_fn=lambda _: None,
        )
