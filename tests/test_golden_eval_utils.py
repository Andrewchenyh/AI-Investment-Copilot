from evals.run_golden_eval import (
    avoids_forbidden_terms,
    contains_all_expected_tools,
    contains_required_mentions,
    extract_tools_used,
    contains_required_tool_calls,
    evaluate_record,
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


def test_contains_required_mentions_is_case_insensitive() -> None:
    assert contains_required_mentions(
        "The ORCL strike is 170.",
        ["orcl", "170"],
    )


def test_avoids_forbidden_terms() -> None:
    assert avoids_forbidden_terms(
        "This is an educational analysis.",
        ["guaranteed profit"],
    )
    assert not avoids_forbidden_terms(
        "This has guaranteed profit.",
        ["guaranteed profit"],
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
    failed_trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {
                "ticker": "ORCL",
                "target_strike": 175,
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
        failed_trace,
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


def test_evaluate_record_applies_required_tool_calls() -> None:
    class FakeAgent:
        def ask(self, query: str, trace_id: str) -> dict:
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
        "forbidden": [],
    }

    result = evaluate_record(record, FakeAgent())

    assert result["checks"]["tool_usage_pass"] is True
    assert result["checks"]["required_tool_calls_pass"] is False
    assert result["passed"] is False