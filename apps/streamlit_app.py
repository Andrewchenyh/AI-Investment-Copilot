import json
import os

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("COPILOT_API_KEY", "")


st.set_page_config(
    page_title="AI Investment Copilot",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("AI Investment Copilot")
st.caption("A tool-using investment research agent with live trace visibility.")

with st.sidebar:
    st.header("Analysis")
    user_query = st.text_area(
        "Ask a question",
        placeholder="Is it a good time to write a cash-secured put on ORCL?",
        height=120,
    )
    session_id = st.text_input("Session ID", value="demo-session")
    run_button = st.button("Run Analysis", type="primary", use_container_width=True)

main_col, debug_col = st.columns([0.62, 0.38], gap="large")

with main_col:
    st.subheader("Answer")
    answer_placeholder = st.empty()

    st.subheader("Grounded Numbers")
    grounded_placeholder = st.empty()

with debug_col:
    st.subheader("Debug Trace")
    trace_id_placeholder = st.empty()
    thoughts_placeholder = st.empty()
    tools_placeholder = st.empty()
    trace_expander = st.expander("Raw Trace", expanded=False)


def stream_sse_events(query: str, session_id: str | None = None):
    response = requests.post(
        f"{API_BASE_URL}/analyze/stream",
        json={"query": query, "session_id": session_id},
        headers={"X-API-Key": API_KEY},
        stream=True,
        timeout=180,
    )
    response.raise_for_status()

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
            
            
def extract_grounded_numbers(trace: list[dict]) -> list[dict]:
    grounded = []

    for item in trace:
        observation = item.get("observation")
        tool_name = item.get("tool_name")

        if not isinstance(observation, dict):
            continue

        if tool_name == "get_historical_volatility":
            grounded.append(
                {
                    "Metric": "Historical volatility",
                    "Value": f"{observation.get('annualized_volatility', 0) * 100:.2f}%",
                    "Source": tool_name,
                }
            )

        if tool_name == "get_current_price":
            grounded.append(
                {
                    "Metric": f"{observation.get('ticker', '')} price",
                    "Value": f"${observation.get('price', 0):,.2f}",
                    "Source": tool_name,
                }
            )

        if tool_name == "analyze_cash_secured_put":
            grounded.extend(
                [
                    {
                        "Metric": "Strike",
                        "Value": f"${observation.get('strike', 0):,.2f}",
                        "Source": tool_name,
                    },
                    {
                        "Metric": "Premium",
                        "Value": f"${observation.get('premium', 0):,.2f}",
                        "Source": tool_name,
                    },
                    {
                        "Metric": "Break-even",
                        "Value": f"${observation.get('break_even_price', 0):,.2f}",
                        "Source": tool_name,
                    },
                    {
                        "Metric": "Annualized return",
                        "Value": f"{observation.get('annualized_return', 0) * 100:.2f}%",
                        "Source": tool_name,
                    },
                    {
                        "Metric": "Cash required",
                        "Value": f"${observation.get('cash_required_dollars', 0):,.0f}",
                        "Source": tool_name,
                    },
                ]
            )

    return grounded


if run_button and user_query:
    final_trace: list[dict] = []
    thought_lines: list[str] = []
    tool_lines: list[str] = []
    latest_trace_id = None

    answer_placeholder.info("Streaming analysis from the FastAPI agent...")
    grounded_placeholder.empty()
    trace_id_placeholder.caption("Trace ID: pending")
    thoughts_placeholder.empty()
    tools_placeholder.empty()

    try:
        for event_name, event_data in stream_sse_events(
            query=user_query,
            session_id=session_id,
        ):
            latest_trace_id = event_data.get("trace_id", latest_trace_id)

            if latest_trace_id:
                trace_id_placeholder.code(latest_trace_id)

            if event_name == "start":
                thought_lines.append("Started analysis.")
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
                    f"Calling `{event_data['tool_name']}` with `{event_data['tool_args_json']}`"
                )
                tools_placeholder.markdown(
                    "**Tool Calls**\n\n" + "\n\n".join(tool_lines)
                )

            elif event_name == "tool_result":
                final_trace.append(event_data)

                if event_data.get("success"):
                    tool_lines.append(
                        f"Completed `{event_data['tool_name']}`."
                    )
                else:
                    tool_lines.append(
                        f"`{event_data['tool_name']}` failed: {event_data.get('error')}"
                    )

                tools_placeholder.markdown(
                    "**Tool Calls**\n\n" + "\n\n".join(tool_lines)
                )

                grounded_numbers = extract_grounded_numbers(final_trace)
                if grounded_numbers:
                    grounded_placeholder.dataframe(
                        grounded_numbers,
                        use_container_width=True,
                        hide_index=True,
                    )

            elif event_name == "final_answer":
                latest_trace_id = event_data.get("trace_id", latest_trace_id)
                final_trace = event_data["trace"]
                answer_placeholder.success(event_data["answer"])

                grounded_numbers = extract_grounded_numbers(final_trace)
                if grounded_numbers:
                    grounded_placeholder.dataframe(
                        grounded_numbers,
                        use_container_width=True,
                        hide_index=True,
                    )

            elif event_name == "error":
                answer_placeholder.error(
                    event_data.get("message", "Unknown streaming error.")
                )
                final_trace = event_data.get("trace", final_trace)

        with trace_expander:
            st.json(final_trace)

    except requests.RequestException as exc:
        answer_placeholder.error(f"Request failed: {exc}")