from evals.load_golden import load_golden_queries
from tools.setup_registry import build_tool_registry


def test_load_golden_queries() -> None:
    records = load_golden_queries()

    assert len(records) >= 10
    assert all("id" in record for record in records)
    assert all("query" in record for record in records)
    assert all("expected_tools" in record for record in records)


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