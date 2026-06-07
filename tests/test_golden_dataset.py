from evals.load_golden import load_golden_queries


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