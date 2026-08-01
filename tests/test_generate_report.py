from evals.generate_report import build_report


def test_build_report_contains_summary() -> None:
    payload = {
        "summary": {
            "total": 2,
            "passed": 1,
            "failed": 1,
            "pass_rate": 0.5,
        },
        "results": [
            {
                "id": "case_1",
                "category": "cash_secured_put",
                "query": "Query 1",
                "status": "success",
                "passed": True,
                "checks": {
                    "status_pass": True,
                },
                "tools_used": ["get_current_price"],
                "judge_score": {
                    "factual_grounding": 5,
                    "reasoning_quality": 4,
                    "hallucination_control": 5,
                    "overall": 4,
                    "rationale": "Good.",
                },
            },
            {
                "id": "case_2",
                "category": "comparison",
                "query": "Query 2",
                "status": "success",
                "passed": False,
                "checks": {
                    "status_pass": True,
                    "required_tool_calls_pass": False,
                    "answer_literals_pass": False,
                    "answer_concepts_pass": False,
                },
                "tools_used": ["get_current_price"],
                "unsatisfied_tool_calls": [
                    {
                        "tool_name": "get_options_chain",
                        "args_subset": {"ticker": "MSFT"},
                        "outcome": "success",
                        "min_calls": 1,
                        "matched_calls": 0,
                    }
                ],
                "missing_answer_literals": ["MSFT"],
                "missing_answer_concepts": ["premium"],
                "judge_score": {
                    "factual_grounding": 3,
                    "reasoning_quality": 2,
                    "hallucination_control": 4,
                    "overall": 3,
                    "rationale": "Missed tools.",
                },
                "judge_error": "RuntimeError: judge timeout",
            },
        ],
    }

    report = build_report(run_id=1, payload=payload)

    assert "# AI Investment Copilot Eval Report" in report
    assert "Pass rate: 50.0%" in report
    assert "Factual grounding: 4.00/5" in report
    assert "case_2" in report
    assert "required_tool_calls_pass" in report
    assert "get_options_chain" in report
    assert "matched=0/1" in report
    assert "Missing answer literals: MSFT" in report
    assert "Missing answer concepts: premium" in report
    assert "Judge error: RuntimeError: judge timeout" in report
