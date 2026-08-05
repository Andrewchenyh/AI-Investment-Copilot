from typing import Any


def describe_activity_event(
    event_name: str,
    event_data: dict[str, Any],
) -> str | None:
    if event_name == "start":
        return "Analysis started."

    if event_name == "thought":
        if event_data["action_type"] == "final_answer":
            return (
                f"Step {event_data['step']}: "
                "Synthesizing the grounded response."
            )

        return None

    if event_name == "tool_call":
        return (
            f"Step {event_data['step']}: Running "
            f"`{event_data['tool_name']}`."
        )

    if event_name == "tool_result":
        tool_name = event_data["tool_name"]

        if event_data["success"]:
            return f"`{tool_name}` completed successfully."

        return (
            f"`{tool_name}` could not complete; "
            "the agent is adjusting its approach."
        )

    if event_name == "final_answer":
        return "Analysis completed."

    if event_name == "error":
        return "Analysis stopped before completion."

    return None