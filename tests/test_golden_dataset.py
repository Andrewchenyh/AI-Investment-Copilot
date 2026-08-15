import json
from pathlib import Path

import pytest

from evals.load_golden import load_golden_queries
from tools.setup_registry import build_tool_registry


EXPECTED_GOLDEN_QUERY_IDS = {
    "csp_orcl_vague",
    "csp_orcl_explicit_strike",
    "csp_orcl_explicit_dte_window",
    "csp_msft_vague",
    "csp_nvda_explicit_strike",
    "technical_aapl_rsi_sma",
    "volatility_orcl",
    "compare_orcl_msft_csp",
    "invalid_fake_ticker",
    "ambiguous_company_name",
}

SUCCESSFUL_CSP_QUERY_IDS = {
    "csp_orcl_vague",
    "csp_orcl_explicit_strike",
    "csp_orcl_explicit_dte_window",
    "csp_msft_vague",
    "csp_nvda_explicit_strike",
    "compare_orcl_msft_csp",
    "ambiguous_company_name",
}

CORE_CSP_CONCEPTS = {
    "spot_price",
    "strike",
    "expiration",
    "premium",
    "break_even",
    "cash_required",
}


def test_golden_dataset_has_expected_ids() -> None:
    records = load_golden_queries()
    ids = [record["id"] for record in records]

    assert len(ids) == len(EXPECTED_GOLDEN_QUERY_IDS)
    assert set(ids) == EXPECTED_GOLDEN_QUERY_IDS


def test_technical_analysis_query_uses_registered_tool_contract() -> None:
    records_by_id = {
        record["id"]: record
        for record in load_golden_queries()
    }
    technical_record = records_by_id["technical_aapl_rsi_sma"]

    assert technical_record["required_tool_calls"] == [
        {
            "tool_name": "analyze_technical_indicators",
            "args_subset": {"ticker": "AAPL"},
            "outcome": "success",
            "min_calls": 1,
        }
    ]
    assert "placeholder" not in technical_record["notes"].lower()


def test_case_specific_answer_contracts_use_registered_semantics() -> None:
    records_by_id = {
        record["id"]: record
        for record in load_golden_queries()
    }

    dte_record = records_by_id[
        "csp_orcl_explicit_dte_window"
    ]
    assert "selected_dte" in dte_record[
        "required_answer_concepts"
    ]

    oracle_record = records_by_id["ambiguous_company_name"]
    assert oracle_record["required_answer_literals"] == []
    assert oracle_record["required_answer_literal_groups"] == [
        ["Oracle", "ORCL"],
    ]


def test_successful_csp_queries_require_core_financial_concepts() -> None:
    records_by_id = {
        record["id"]: record
        for record in load_golden_queries()
    }

    for record_id in sorted(SUCCESSFUL_CSP_QUERY_IDS):
        concept_names = set(
            records_by_id[record_id][
                "required_answer_concepts"
            ]
        )

        missing_concepts = CORE_CSP_CONCEPTS - concept_names
        assert not missing_concepts, (
            f"{record_id} is missing core CSP concepts: "
            f"{sorted(missing_concepts)}"
        )


def test_all_golden_tool_references_are_registered() -> None:
    records = load_golden_queries()
    registered_tools = set(build_tool_registry().list_tool_names())
    referenced_tools = {
        requirement["tool_name"]
        for record in records
        for requirement in record["required_tool_calls"]
    }

    assert referenced_tools <= registered_tools


@pytest.mark.parametrize(
    "invalid_record",
    [
        pytest.param(
            {
                "id": "missing_query",
                "category": "technical_analysis",
                "required_tool_calls": [
                    {"tool_name": "analyze_technical_indicators"}
                ],
                "required_answer_concepts": ["rsi_14"],
                "notes": "Missing the required query field.",
            },
            id="missing-required-field",
        ),
        pytest.param(
            {
                "id": "legacy_field",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "expected_tools": ["analyze_technical_indicators"],
                "required_tool_calls": [
                    {"tool_name": "analyze_technical_indicators"}
                ],
                "required_answer_concepts": ["rsi_14"],
                "notes": "Contains a removed legacy field.",
            },
            id="legacy-field",
        ),
        pytest.param(
            {
                "id": "empty_tool_calls",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "required_tool_calls": [],
                "required_answer_concepts": ["rsi_14"],
                "notes": "Tool contracts cannot be empty.",
            },
            id="empty-tool-calls",
        ),
        pytest.param(
            {
                "id": "empty_answer_concepts",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "required_tool_calls": [
                    {"tool_name": "analyze_technical_indicators"}
                ],
                "required_answer_concepts": [],
                "notes": "Answer concept contracts cannot be empty.",
            },
            id="empty-answer-concepts",
        ),
        pytest.param(
            {
                "id": "unknown_answer_concept",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "required_tool_calls": [
                    {"tool_name": "analyze_technical_indicators"}
                ],
                "required_answer_concepts": ["unknown_concept"],
                "notes": "Concept names must be registered.",
            },
            id="unknown-answer-concept",
        ),
        pytest.param(
            {
                "id": "legacy_concept_object",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "required_tool_calls": [
                    {"tool_name": "analyze_technical_indicators"}
                ],
                "required_answer_concepts": [
                    {
                        "name": "rsi_14",
                        "alternatives": ["RSI 14"],
                    }
                ],
                "notes": "Legacy concept objects are not supported.",
            },
            id="legacy-concept-object",
        ),
        pytest.param(
            {
                "id": "duplicate_answer_concepts",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "required_tool_calls": [
                    {"tool_name": "analyze_technical_indicators"}
                ],
                "required_answer_concepts": ["rsi_14", "rsi_14"],
                "notes": "Concept names must be unique.",
            },
            id="duplicate-answer-concepts",
        ),
        pytest.param(
            {
                "id": "blank_answer_concept",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "required_tool_calls": [
                    {"tool_name": "analyze_technical_indicators"}
                ],
                "required_answer_concepts": ["rsi_14", " "],
                "notes": "Concept names must be nonblank.",
            },
            id="blank-answer-concept",
        ),
        pytest.param(
            {
                "id": "duplicate_literals",
                "category": "technical_analysis",
                "query": "Analyze AAPL.",
                "required_tool_calls": [
                    {"tool_name": "analyze_technical_indicators"}
                ],
                "required_answer_concepts": ["rsi_14"],
                "required_answer_literals": ["AAPL", "aapl"],
                "notes": "Answer literals must be unique.",
            },
            id="duplicate-answer-literals",
        ),
        pytest.param(
            {
                "id": "empty_literal_group",
                "category": "query_understanding",
                "query": "Analyze Oracle.",
                "required_tool_calls": [
                    {"tool_name": "get_current_price"}
                ],
                "required_answer_concepts": ["spot_price"],
                "required_answer_literal_groups": [[]],
                "notes": "Literal groups cannot be empty.",
            },
            id="empty-answer-literal-group",
        ),
        pytest.param(
            {
                "id": "blank_literal_alternative",
                "category": "query_understanding",
                "query": "Analyze Oracle.",
                "required_tool_calls": [
                    {"tool_name": "get_current_price"}
                ],
                "required_answer_concepts": ["spot_price"],
                "required_answer_literal_groups": [
                    ["Oracle", " "]
                ],
                "notes": "Literal alternatives cannot be blank.",
            },
            id="blank-answer-literal-alternative",
        ),
        pytest.param(
            {
                "id": "duplicate_literal_alternatives",
                "category": "query_understanding",
                "query": "Analyze Oracle.",
                "required_tool_calls": [
                    {"tool_name": "get_current_price"}
                ],
                "required_answer_concepts": ["spot_price"],
                "required_answer_literal_groups": [
                    ["ORCL", "orcl"]
                ],
                "notes": "Literal alternatives must be unique.",
            },
            id="duplicate-answer-literal-alternatives",
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
        "required_tool_calls": [
            {"tool_name": "analyze_technical_indicators"}
        ],
        "required_answer_concepts": ["rsi_14"],
        "notes": "A valid record.",
    }
    invalid_record = {
        "id": "invalid_record",
        "category": "technical_analysis",
        "required_tool_calls": [
            {"tool_name": "analyze_technical_indicators"}
        ],
        "required_answer_concepts": ["rsi_14"],
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


def test_loads_structured_expectations(tmp_path: Path) -> None:
    record = {
        "id": "required_call_test",
        "category": "technical_analysis",
        "query": "Analyze AAPL.",
        "required_tool_calls": [
            {
                "tool_name": "analyze_technical_indicators",
                "args_subset": {"ticker": "AAPL"},
            }
        ],
        "required_answer_literals": ["AAPL"],
        "required_answer_literal_groups": [
            ["Apple", "AAPL"]
        ],
        "required_answer_concepts": ["sma_50"],
        "notes": "Tests structured evaluation expectations.",
    }

    golden_path = tmp_path / "required_calls.jsonl"
    golden_path.write_text(
        json.dumps(record) + "\n",
        encoding="utf-8",
    )

    loaded_record = load_golden_queries(golden_path)[0]

    assert loaded_record["required_tool_calls"] == [
        {
            "tool_name": "analyze_technical_indicators",
            "args_subset": {"ticker": "AAPL"},
            "outcome": "success",
            "min_calls": 1,
        }
    ]
    assert loaded_record["required_answer_literals"] == ["AAPL"]
    assert loaded_record["required_answer_literal_groups"] == [
        ["Apple", "AAPL"]
    ]
    assert loaded_record["required_answer_concepts"] == ["sma_50"]
