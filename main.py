from agents.react_agent import ReActAgent
from tools.setup_registry import build_tool_registry


def main() -> None:
    registry = build_tool_registry()
    agent = ReActAgent(tool_registry=registry, max_steps=6)

    query = "Is it a good time to write a cash-secured put on orcl?"
    response = agent.ask(query)

    print(response["status"])
    if response["status"] == "success":
        print("\nFINAL ANSWER:\n")
        print(response["answer"])
    else:
        print("\nERROR:\n")
        print(response["message"])

    print("\nTRACE:\n")
    for item in response["trace"]:
        print(item)


if __name__ == "__main__":
    main()