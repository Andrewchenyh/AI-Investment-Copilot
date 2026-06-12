from evals.run_golden_eval import (
    avoids_forbidden_terms,
    contains_all_expected_tools,
    contains_required_mentions,
    extract_tools_used,
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