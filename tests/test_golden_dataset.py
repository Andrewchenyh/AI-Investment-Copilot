import json
from pathlib import Path

import pytest
from evals.load_golden import load_golden_queries
from tools.setup_registry import build_tool_registry


def test_load_golden_queries() -> None:
    records = load_golden_queries()

    assert len(records) >= 10
    assert all("id" in record for record in records)
    assert all("query" in record for record in records)
    assert all("expected_tools" in record for record in records)
    assert all(record["tier"] in {"core", "stress"} for record in records)


def test_golden_query_ids_are_unique() -> None:
    records = load_golden_queries()
    ids = [record["id"] for record in records]

    assert len(ids) == len(set(ids))


def test_technical_analysis_golden_query_uses_registered_tool() -> None:
    records = load_golden_queries()
    records_by_id = {record["id"]: record for record in records}

    technical_record = records_by_id["technical_aapl_rsi_sma"]

    assert technical_record["expected_tools"] == [
        "analyze_technical_indicators"
    ]
    assert "placeholder" not in technical_record["notes"].lower()


def test_all_golden_tool_references_are_registered() -> None:
    records = load_golden_queries()
    registered_tools = set(build_tool_registry().list_tool_names())

    referenced_tools = {
        tool_name
        for record in records
        for field_name in ("expected_tools", "optional_tools")
        for tool_name in record.get(field_name, [])
    }

    assert referenced_tools <= registered_tools


@pytest.mark.parametrize(
    "invalid_record",
    [
        pytest.param(
            {
                "id": "missing_query",
                "category": "technical_analysis",
                "expected_tools": ["analyze_technical_indicators"],
                "notes": "Missing the required query field.",
            },
            id="missing-required-field",
        ),
        pytest.param(
            {
                "id": "misspelled_field",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "expected_tool": ["analyze_technical_indicators"],
                "expected_tools": ["analyze_technical_indicators"],
                "notes": "Contains an unknown field.",
            },
            id="unknown-field",
        ),
        pytest.param(
            {
                "id": "overlapping_tools",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "expected_tools": ["analyze_technical_indicators"],
                "optional_tools": ["analyze_technical_indicators"],
                "notes": "The same tool cannot have both roles.",
            },
            id="overlapping-tool-roles",
        ),
    ],
)
def test_load_golden_queries_rejects_invalid_schema(
    tmp_path: Path,
    invalid_record: dict,
) -> None:
    golden_path = tmp_path / "invalid_golden.jsonl"
    golden_path.write_text(
        json.dumps(invalid_record) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"Invalid golden query schema on line 1",
    ):
        load_golden_queries(golden_path)


def test_schema_error_reports_correct_jsonl_line(tmp_path: Path) -> None:
    valid_record = {
        "id": "valid_record",
        "category": "technical_analysis",
        "query": "Analyze AAPL.",
        "expected_tools": ["analyze_technical_indicators"],
        "notes": "A valid record.",
    }
    invalid_record = {
        "id": "invalid_record",
        "category": "technical_analysis",
        "expected_tools": ["analyze_technical_indicators"],
        "notes": "Missing query.",
    }

    golden_path = tmp_path / "mixed_golden.jsonl"
    golden_path.write_text(
        "\n".join(
            [
                json.dumps(valid_record),
                json.dumps(invalid_record),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"Invalid golden query schema on line 2",
    ):
        load_golden_queries(golden_path)


def test_loads_required_tool_call_expectations(tmp_path: Path) -> None:
    record = {
        "id": "required_call_test",
        "category": "technical_analysis",
        "query": "Analyze AAPL.",
        "expected_tools": ["analyze_technical_indicators"],
        "required_tool_calls": [
            {
                "tool_name": "analyze_technical_indicators",
                "args_subset": {"ticker": "AAPL"},
            }
        ],
        "notes": "Tests trace-aware tool requirements.",
    }

    golden_path = tmp_path / "required_calls.jsonl"
    golden_path.write_text(
        json.dumps(record) + "\n",
        encoding="utf-8",
    )

    loaded_record = load_golden_queries(golden_path)[0]
    requirement = loaded_record["required_tool_calls"][0]

    assert requirement == {
        "tool_name": "analyze_technical_indicators",
        "args_subset": {"ticker": "AAPL"},
        "outcome": "success",
        "min_calls": 1,
    }