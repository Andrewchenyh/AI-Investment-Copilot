from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from agents.react_agent import ReActAgent
from evals.concept_patterns import ANSWER_CONCEPT_PATTERNS
from evals.judge import GeminiJudge
from evals.load_golden import load_golden_queries
from evals.store_results import save_eval_run
from tools.setup_registry import build_tool_registry

DEFAULT_OUTPUT_PATH = Path("evals/results/latest_golden_eval.json")


class EvaluationAgent(Protocol):
    def ask(self, user_query: str, trace_id: str) -> dict[str, Any]: ...


def _argument_values_match(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.casefold() == expected.casefold()

    return actual == expected


def _tool_call_matches(
    trace_item: dict[str, Any],
    expectation: dict[str, Any],
) -> bool:
    if trace_item.get("tool_name") != expectation["tool_name"]:
        return False

    outcome = expectation.get("outcome", "success")
    success = trace_item.get("success")

    if outcome == "success" and success is not True:
        return False

    if outcome == "failure" and success is not False:
        return False

    expected_args = expectation.get("args_subset", {})
    actual_args = trace_item.get("tool_args")

    if expected_args and not isinstance(actual_args, dict):
        return False

    return all(
        key in actual_args
        and _argument_values_match(actual_args[key], expected_value)
        for key, expected_value in expected_args.items()
    )


def extract_tools_used(trace: list[dict[str, Any]]) -> list[str]:
    tools: list[str] = []

    for item in trace:
        tool_name = item.get("tool_name")
        if isinstance(tool_name, str):
            tools.append(tool_name)

    return tools


def find_unsatisfied_tool_calls(
    trace: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unsatisfied: list[dict[str, Any]] = []

    for requirement in requirements:
        matching_calls = sum(
            1
            for trace_item in trace
            if _tool_call_matches(trace_item, requirement)
        )

        if matching_calls < requirement.get("min_calls", 1):
            unsatisfied.append(
                {
                    **requirement,
                    "matched_calls": matching_calls,
                }
            )

    return unsatisfied


def find_missing_answer_literals(
    answer: str,
    required_literals: list[str],
) -> list[str]:
    return [
        literal
        for literal in required_literals
        if re.search(
            rf"(?<!\w){re.escape(literal)}(?!\w)",
            answer,
            flags=re.IGNORECASE,
        )
        is None
    ]


def find_missing_answer_concepts(
    answer: str,
    concepts: list[str],
) -> list[str]:
    missing_concepts: list[str] = []

    for concept_name in concepts:
        patterns = ANSWER_CONCEPT_PATTERNS[
            concept_name
        ]
        concept_found = any(
            pattern.search(answer) is not None
            for pattern in patterns
        )

        if not concept_found:
            missing_concepts.append(concept_name)

    return missing_concepts


def evaluate_record(
    record: dict[str, Any],
    agent: EvaluationAgent,
    judge: GeminiJudge | None = None,
) -> dict[str, Any]:
    try:
        result = agent.ask(record["query"], trace_id=str(uuid4()))
    except Exception as exc:
        result = {
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
            "trace": [],
        }

    answer = result.get("answer") or ""
    trace = result.get("trace") or []
    tools_used = extract_tools_used(trace)

    required_tool_calls = record["required_tool_calls"]
    required_answer_literals = record.get(
        "required_answer_literals",
        [],
    )
    required_answer_concepts = record["required_answer_concepts"]

    unsatisfied_tool_calls = find_unsatisfied_tool_calls(
        trace,
        required_tool_calls,
    )
    required_tool_calls_pass = not unsatisfied_tool_calls
    missing_answer_literals = find_missing_answer_literals(
        answer,
        required_answer_literals,
    )
    answer_literals_pass = not missing_answer_literals
    missing_answer_concepts = find_missing_answer_concepts(
        answer,
        required_answer_concepts,
    )
    answer_concepts_pass = not missing_answer_concepts
    status_pass = result.get("status") == "success"

    passed = all(
        [
            status_pass,
            required_tool_calls_pass,
            answer_literals_pass,
            answer_concepts_pass,
        ]
    )

    judge_score = None
    judge_error = None
    if judge is not None and answer:
        try:
            judge_score = judge.score(
                query=record["query"],
                answer=answer,
                trace=trace,
            ).model_dump()
        except Exception as exc:
            judge_error = f"{type(exc).__name__}: {exc}"

    return {
        "id": record["id"],
        "category": record["category"],
        "query": record["query"],
        "status": result.get("status"),
        "error": result.get("message"),
        "passed": passed,
        "checks": {
            "status_pass": status_pass,
            "required_tool_calls_pass": required_tool_calls_pass,
            "answer_literals_pass": answer_literals_pass,
            "answer_concepts_pass": answer_concepts_pass,
        },
        "tools_used": tools_used,
        "required_tool_calls": required_tool_calls,
        "unsatisfied_tool_calls": unsatisfied_tool_calls,
        "answer": answer,
        "required_answer_literals": required_answer_literals,
        "missing_answer_literals": missing_answer_literals,
        "required_answer_concepts": required_answer_concepts,
        "missing_answer_concepts": missing_answer_concepts,
        "trace": trace,
        "judge_score": judge_score,
        "judge_error": judge_error,
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result["passed"])

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total else 0,
    }


def run_eval(
    limit: int | None,
    output_path: Path,
    use_judge: bool = False,
) -> dict[str, Any]:

    judge = GeminiJudge() if use_judge else None
    records = load_golden_queries()
    if limit is not None:
        records = records[:limit]

    registry = build_tool_registry()
    agent = ReActAgent(tool_registry=registry, max_steps=8)

    results = [
        evaluate_record(record, agent, judge=judge)
        for record in records
    ]
    summary = summarize_results(results)

    payload = {
        "summary": summary,
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Run LLM-as-judge scoring for each result.",
    )
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="Persist this eval run to the local SQLite eval database.",
    )
    args = parser.parse_args()

    payload = run_eval(
        limit=args.limit,
        output_path=args.output,
        use_judge=args.judge,
    )
    if args.save_db:
        run_id = save_eval_run(payload)
        print(f"Saved eval run to SQLite with id: {run_id}")
    summary = payload["summary"]

    print(
        f"Golden eval complete: "
        f"{summary['passed']}/{summary['total']} passed "
        f"({summary['pass_rate']:.1%})"
    )
    print(f"Results written to: {args.output}")


if __name__ == "__main__":
    main()
