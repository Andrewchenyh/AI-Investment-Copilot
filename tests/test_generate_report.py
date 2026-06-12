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
                    "tool_usage_pass": False,
                },
                "tools_used": ["get_current_price"],
                "judge_score": {
                    "factual_grounding": 3,
                    "reasoning_quality": 2,
                    "hallucination_control": 4,
                    "overall": 3,
                    "rationale": "Missed tools.",
                },
            },
        ],
    }

    report = build_report(run_id=1, payload=payload)

    assert "# AI Investment Copilot Eval Report" in report
    assert "Pass rate: 50.0%" in report
    assert "Factual grounding: 4.00/5" in report
    assert "case_2" in report
    assert "tool_usage_pass" in report