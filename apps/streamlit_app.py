import json

import requests
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = "http://127.0.0.1:8000"
API_KEY = os.getenv("COPILOT_API_KEY", "")


st.set_page_config(page_title="AI Investment Copilot", layout="wide")

st.title("AI Investment Copilot")
st.markdown("Ask investment questions and watch the agent think in real time.")


with st.sidebar:
    st.header("Ask the Copilot")
    user_query = st.text_area(
        "Enter query:",
        placeholder="Is it a good time to write a cash-secured put on ORCL?",
    )
    run_button = st.button("Run Analysis")


answer_container = st.container()
thoughts_container = st.container()
tools_container = st.container()
trace_container = st.expander("View Final Trace")


def stream_sse_events(query: str):
    response = requests.post(
        f"{API_BASE_URL}/analyze/stream",
        json={"query": query},
        headers={"X-API-Key": API_KEY},
        stream=True,
        timeout=120,
    )
    current_event = None
    current_data_lines: list[str] = []

    for raw_line in response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue

        line = raw_line.strip()

        if not line:
            if current_event and current_data_lines:
                data_str = "\n".join(current_data_lines)
                yield current_event, json.loads(data_str)
            current_event = None
            current_data_lines = []
            continue

        if line.startswith("event:"):
            current_event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            current_data_lines.append(line.removeprefix("data:").strip())


if run_button and user_query:
    final_trace = []
    latest_answer = None

    answer_placeholder = answer_container.empty()
    thoughts_placeholder = thoughts_container.empty()
    tools_placeholder = tools_container.empty()

    thought_lines: list[str] = []
    tool_lines: list[str] = []

    answer_placeholder.info("Streaming analysis...")

    try:
        for event_name, event_data in stream_sse_events(user_query):
            if event_name == "start":
                thought_lines.append(
                    f"Started analysis for query: `{event_data['query']}`"
                )
                thoughts_placeholder.markdown(
                    "**Live Thoughts**\n\n" + "\n\n".join(thought_lines)
                )

            elif event_name == "thought":
                final_trace.append(event_data)
                thought_lines.append(
                    f"Step {event_data['step']}: {event_data['thought']}"
                )
                thoughts_placeholder.markdown(
                    "**Live Thoughts**\n\n" + "\n\n".join(thought_lines)
                )

            elif event_name == "tool_call":
                tool_lines.append(
                    f"Calling `{event_data['tool_name']}` with args `{event_data['tool_args_json']}`"
                )
                tools_placeholder.markdown(
                    "**Tool Executions**\n\n" + "\n\n".join(tool_lines)
                )

            elif event_name == "tool_result":
                final_trace.append(event_data)

                if event_data["success"]:
                    tool_lines.append(
                        f"Completed `{event_data['tool_name']}` successfully."
                    )
                else:
                    tool_lines.append(
                        f"Tool `{event_data['tool_name']}` failed: {event_data['error']}"
                    )

                tools_placeholder.markdown(
                    "**Tool Executions**\n\n" + "\n\n".join(tool_lines)
                )

            elif event_name == "final_answer":
                latest_answer = event_data["answer"]
                final_trace = event_data["trace"]
                answer_placeholder.success(latest_answer)

            elif event_name == "error":
                error_message = event_data.get("message") or event_data.get("error") or "Unknown error"
                answer_placeholder.error(error_message)
                if "trace" in event_data:
                    final_trace = event_data["trace"]

        with trace_container:
            st.json(final_trace)

    except requests.RequestException as exc:
        answer_placeholder.error(f"Request failed: {exc}")