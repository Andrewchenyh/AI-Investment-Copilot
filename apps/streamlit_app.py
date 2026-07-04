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