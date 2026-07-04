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

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    div[data-testid="stSidebar"] {
        background-color: #f7f8fa;
    }

    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e6e8eb;
        padding: 0.75rem;
        border-radius: 8px;
    }

    .small-muted {
        color: #687076;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AI Investment Copilot")
st.caption("A tool-using investment research agent with live trace visibility.")

PRESET_QUERIES = {
    "Cash-secured put: ORCL": "Is it a good time to write a cash-secured put on ORCL?",
    "Explicit strike: ORCL $170 put": "Is it a good time to write a $170 cash-secured put on ORCL?",
    "Volatility: ORCL": "What is ORCL recent historical volatility?",
    "Compare puts: ORCL vs MSFT": "Compare ORCL and MSFT for writing cash-secured puts.",
}

with st.sidebar:
    st.header("Analysis")

    preset_label = st.selectbox(
        "Demo query",
        options=list(PRESET_QUERIES.keys()),
    )

    user_query = st.text_area(
        "Ask a question",
        value=PRESET_QUERIES[preset_label],
        height=120,
    )

    session_id = st.text_input("Session ID", value="demo-session")
    run_button = st.button("Run Analysis", type="primary", use_container_width=True)

    st.markdown(
        '<p class="small-muted">Research assistant only. Not financial advice.</p>',
        unsafe_allow_html=True,
    )

main_col, debug_col = st.columns([0.62, 0.38], gap="large")

with main_col:
    st.subheader("Run Summary")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    status_metric = metric_col1.empty()
    trace_metric = metric_col2.empty()
    tool_metric = metric_col3.empty()

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

        if tool_name == "get_options_chain":
            grounded.append(
                {
                    "Metric": "Options expiration",
                    "Value": str(observation.get("expiration", "")),
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


def summarize_tool_result(event_data: dict) -> str:
    tool_name = event_data.get("tool_name")
    observation = event_data.get("observation", {})

    if not event_data.get("success"):
        return f"`{tool_name}` failed: {event_data.get('error')}"

    if tool_name == "get_current_price":
        return (
            f"`get_current_price`: {observation.get('ticker')} "
            f"${observation.get('price', 0):,.2f}"
        )

    if tool_name == "get_historical_volatility":
        return (
            "`get_historical_volatility`: "
            f"{observation.get('annualized_volatility', 0) * 100:.2f}%"
        )

    if tool_name == "get_options_chain":
        return (
            f"`get_options_chain`: {observation.get('contract_count')} contracts, "
            f"exp {observation.get('expiration')}"
        )

    if tool_name == "analyze_cash_secured_put":
        return (
            "`analyze_cash_secured_put`: "
            f"strike ${observation.get('strike', 0):,.2f}, "
            f"premium ${observation.get('premium', 0):,.2f}"
        )

    return f"`{tool_name}` completed."


status_metric.metric("Status", "Idle")
trace_metric.metric("Trace", "None")
tool_metric.metric("Tools", "0")
answer_placeholder.info("Choose a demo query and run the agent.")
grounded_placeholder.caption("Grounded numbers will appear after tool execution.")
trace_id_placeholder.caption("Trace ID will appear here.")
thoughts_placeholder.caption("Live reasoning steps will appear here.")
tools_placeholder.caption("Tool calls and results will appear here.")

if run_button and user_query:
    final_trace: list[dict] = []
    thought_lines: list[str] = []
    tool_lines: list[str] = []
    latest_trace_id = None
    tool_count = 0

    status_metric.metric("Status", "Running")
    trace_metric.metric("Trace", "Pending")
    tool_metric.metric("Tools", "0")
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
                trace_metric.metric("Trace", latest_trace_id[:8])

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
                tool_count += 1
                tool_metric.metric("Tools", str(tool_count))

                tool_lines.append(summarize_tool_result(event_data))
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
                final_trace = event_data["trace"]
                status_metric.metric("Status", "Complete")
                answer_placeholder.success(event_data["answer"])

                grounded_numbers = extract_grounded_numbers(final_trace)
                if grounded_numbers:
                    grounded_placeholder.dataframe(
                        grounded_numbers,
                        use_container_width=True,
                        hide_index=True,
                    )

            elif event_name == "error":
                status_metric.metric("Status", "Error")
                answer_placeholder.error(
                    event_data.get("message", "Unknown streaming error.")
                )
                final_trace = event_data.get("trace", final_trace)

        with trace_expander:
            st.json(final_trace)

    except requests.RequestException as exc:
        status_metric.metric("Status", "Error")
        answer_placeholder.error(f"Request failed: {exc}")