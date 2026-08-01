from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

from evals.store_results import get_eval_run, list_eval_runs


DEFAULT_REPORT_PATH = Path("evals/reports/latest_eval_report.md")


def get_latest_run_id() -> int:
    runs = list_eval_runs()
    if not runs:
        raise ValueError("No eval runs found.")
    return int(runs[0]["id"])


def average_judge_score(
    results: list[dict[str, Any]],
    key: str,
) -> float | None:
    values = [
        result["judge_score"][key]
        for result in results
        if result.get("judge_score") is not None
    ]

    if not values:
        return None

    return mean(values)


def format_score(score: float | None) -> str:
    if score is None:
        return "N/A"
    return f"{score:.2f}/5"


def get_failed_checks(result: dict[str, Any]) -> list[str]:
    checks = result.get("checks", {})
    return [
        check_name
        for check_name, passed in checks.items()
        if passed is False
    ]


def format_unsatisfied_tool_call(requirement: dict[str, Any]) -> str:
    args_subset = json.dumps(
        requirement.get("args_subset", {}),
        sort_keys=True,
    )
    matched_calls = requirement.get("matched_calls", 0)
    min_calls = requirement.get("min_calls", 1)
    outcome = requirement.get("outcome", "success")

    return (
        f"{requirement['tool_name']}(args_subset={args_subset}, "
        f"outcome={outcome}, matched={matched_calls}/{min_calls})"
    )


def build_report(run_id: int, payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    results = payload["results"]

    avg_factual = average_judge_score(results, "factual_grounding")
    avg_reasoning = average_judge_score(results, "reasoning_quality")
    avg_hallucination = average_judge_score(results, "hallucination_control")
    avg_overall = average_judge_score(results, "overall")

    failed_results = [result for result in results if not result["passed"]]

    lines = [
        "# AI Investment Copilot Eval Report",
        "",
        f"Run ID: {run_id}",
        "",
        "## Summary",
        "",
        f"- Total cases: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Pass rate: {summary['pass_rate']:.1%}",
        "",
        "## LLM Judge Scores",
        "",
        f"- Factual grounding: {format_score(avg_factual)}",
        f"- Reasoning quality: {format_score(avg_reasoning)}",
        f"- Hallucination control: {format_score(avg_hallucination)}",
        f"- Overall: {format_score(avg_overall)}",
        "",
        "## Failed Cases",
        "",
    ]

    if failed_results:
        for result in failed_results:
            failed_checks = ", ".join(get_failed_checks(result)) or "unknown"
            lines.extend(
                [
                    f"### {result['id']}",
                    "",
                    f"- Category: {result['category']}",
                    f"- Query: {result['query']}",
                    f"- Failed checks: {failed_checks}",
                    f"- Tools used: {', '.join(result.get('tools_used', []))}",
                ]
            )

            if result.get("error"):
                lines.append(f"- Agent error: {result['error']}")

            unsatisfied_calls = result.get("unsatisfied_tool_calls", [])
            if unsatisfied_calls:
                formatted_calls = "; ".join(
                    format_unsatisfied_tool_call(requirement)
                    for requirement in unsatisfied_calls
                )
                lines.append(f"- Unsatisfied tool calls: {formatted_calls}")

            missing_literals = result.get("missing_answer_literals", [])
            if missing_literals:
                lines.append(
                    "- Missing answer literals: "
                    f"{', '.join(missing_literals)}"
                )

            missing_concepts = result.get("missing_answer_concepts", [])
            if missing_concepts:
                lines.append(
                    "- Missing answer concepts: "
                    f"{', '.join(missing_concepts)}"
                )

            lines.append("")
    else:
        lines.append("No failed cases.")

    lines.extend(
        [
            "",
            "## Case Results",
            "",
        ]
    )

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        judge_score = result.get("judge_score") or {}
        overall = judge_score.get("overall", "N/A")
        judge_error = result.get("judge_error")

        lines.extend(
            [
                f"### {result['id']} - {status}",
                "",
                f"- Category: {result['category']}",
                f"- Status: {result['status']}",
                f"- Overall judge score: {overall}",
                f"- Tools used: {', '.join(result.get('tools_used', []))}",
            ]
        )
        if judge_error:
            lines.append(f"- Judge error: {judge_error}")
        lines.append("")

    return "\n".join(lines) + "\n"


def write_report(
    run_id: int | None,
    output_path: Path,
) -> Path:
    selected_run_id = run_id if run_id is not None else get_latest_run_id()
    payload = get_eval_run(selected_run_id)

    if payload is None:
        raise ValueError(f"Eval run {selected_run_id} not found.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_report(selected_run_id, payload),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
    )
    args = parser.parse_args()

    report_path = write_report(
        run_id=args.run_id,
        output_path=args.output,
    )

    print(f"Eval report written to: {report_path}")


if __name__ == "__main__":
    main()
