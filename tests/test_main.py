from uuid import UUID

import main as cli


def test_main_passes_a_trace_id_to_the_agent(monkeypatch, capsys) -> None:
    registry = object()
    captured: dict[str, object] = {}

    class FakeAgent:
        def __init__(self, tool_registry, max_steps: int) -> None:
            captured["registry"] = tool_registry
            captured["max_steps"] = max_steps

        def ask(self, query: str, trace_id: str) -> dict:
            captured["query"] = query
            captured["trace_id"] = trace_id
            return {
                "status": "success",
                "answer": "A grounded test answer.",
                "trace": [],
            }

    monkeypatch.setattr(cli, "build_tool_registry", lambda: registry)
    monkeypatch.setattr(cli, "ReActAgent", FakeAgent)

    cli.main()

    UUID(str(captured["trace_id"]))
    assert captured["registry"] is registry
    assert captured["max_steps"] == 6
    assert captured["query"] == (
        "Is it a good time to write a cash-secured put on orcl?"
    )

    output = capsys.readouterr().out
    assert "success" in output
    assert "A grounded test answer." in output
