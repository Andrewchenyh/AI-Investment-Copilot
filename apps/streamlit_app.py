import os

import requests
import streamlit as st
from dotenv import load_dotenv

from apps.activity_timeline import describe_activity_event
from apps.grounded_evidence import build_grounded_evidence
from apps.sse_client import (
    SSEProtocolError,
    parse_sse_lines,
    require_terminal_event,
    validate_event_payloads,
)

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
        padding-top: 4rem;
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

    .eyebrow {
        color: #0f766e;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        margin-bottom: 0.35rem;
    }

    .hero-copy {
        color: #5f6874;
        font-size: 1.08rem;
        line-height: 1.6;
        max-width: 780px;
        margin-bottom: 1rem;
    }

    .capability-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 1.75rem;
    }

    .capability-chip {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        border-radius: 999px;
        color: #065f46;
        font-size: 0.84rem;
        font-weight: 600;
        padding: 0.35rem 0.7rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="eyebrow">AGENTIC INVESTMENT RESEARCH</p>',
    unsafe_allow_html=True,
)
st.title("AI Investment Copilot")
st.markdown(
    """
    <p class="hero-copy">
        An evidence-grounded research agent that selects financial tools,
        evaluates market and options data, and streams every observable
        action behind its answer.
    </p>
    <div class="capability-row">
        <span class="capability-chip">Tool-using ReAct agent</span>
        <span class="capability-chip">Market-data provenance</span>
        <span class="capability-chip">Quote-quality safeguards</span>
        <span class="capability-chip">Streaming activity trace</span>
    </div>
    """,
    unsafe_allow_html=True,
)

PRESET_QUERIES = {
    "Cash-secured put: ORCL": (
        "Is it a good time to write a cash-secured put on ORCL?"
    ),
    "Explicit strike: ORCL $170 put": (
        "Is it a good time to write a $170 cash-secured put on ORCL?"
    ),
    "Technical indicators: AAPL": (
        "Analyze AAPL using RSI 14 and 50-day moving average."
    ),
    "Volatility: ORCL": (
        "What is ORCL recent historical volatility?"
    ),
}

with st.sidebar:
    st.header("Try the Copilot")

    preset_label = st.selectbox(
        "Demo scenario",
        options=list(PRESET_QUERIES.keys()),
    )

    user_query = st.text_area(
        "Ask a question",
        value=PRESET_QUERIES[preset_label],
        height=120,
    )

    run_button = st.button(
        "Run Analysis",
        type="primary",
        use_container_width=True,
    )

    with st.expander("Advanced"):
        session_id = st.text_input(
            "Session ID",
            value="demo-session",
        )
        st.caption(
            "The session ID groups saved analysis history."
        )

    st.caption(
        "Research assistance only—not financial advice."
    )

main_col, debug_col = st.columns([0.62, 0.38], gap="large")

with main_col:
    st.subheader("Run Summary")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    status_metric = metric_col1.empty()
    evidence_metric = metric_col2.empty()
    tool_metric = metric_col3.empty()

    st.subheader("Answer")
    answer_placeholder = st.empty()

    st.subheader("Grounded Evidence")
    grounded_placeholder = st.empty()

with debug_col:
    st.subheader("Analysis Activity")
    trace_id_placeholder = st.empty()
    activity_placeholder = st.empty()
    trace_expander = st.expander(
        "Developer Trace",
        expanded=False,
    )


def stream_sse_events(query: str, session_id: str | None = None):
    response = requests.post(
        f"{API_BASE_URL}/analyze/stream",
        json={"query": query, "session_id": session_id},
        headers={"X-API-Key": API_KEY},
        stream=True,
        timeout=180,
    )
    response.raise_for_status()

    yield from require_terminal_event(
        validate_event_payloads(
            parse_sse_lines(
                response.iter_lines(decode_unicode=True)
            )
        )
    )


status_metric.metric("Status", "Idle")
evidence_metric.metric("Evidence", "0")
tool_metric.metric("Tools", "0")
answer_placeholder.info("Choose a demo query and run the agent.")
grounded_placeholder.caption(
    "Financial evidence and provenance will appear after tool execution."
)
trace_id_placeholder.caption("Trace ID will appear here.")
activity_placeholder.caption("Agent actions and tool results will appear here.")

if run_button and user_query:
    final_trace: list[dict] = []
    activity_lines: list[str] = []
    latest_trace_id = None
    tool_count = 0

    status_metric.metric("Status", "Running")
    evidence_metric.metric("Evidence", "0")
    tool_metric.metric("Tools", "0")
    answer_placeholder.info("Streaming analysis from the FastAPI agent...")
    grounded_placeholder.empty()
    trace_id_placeholder.caption("Trace ID: pending")
    activity_placeholder.empty()

    try:
        for event_name, event_data in stream_sse_events(
            query=user_query,
            session_id=session_id,
        ):
            latest_trace_id = event_data.get("trace_id", latest_trace_id)

            activity_message = describe_activity_event(
                event_name,
                event_data,
            )

            if activity_message is not None:
                activity_lines.append(activity_message)
                activity_placeholder.markdown(
                    "\n".join(
                        f"- {line}"
                        for line in activity_lines
                    )
                )

            if latest_trace_id:
                trace_id_placeholder.code(latest_trace_id)

            if event_name == "thought":
                final_trace.append(event_data)

            elif event_name == "tool_result":
                final_trace.append(event_data)
                tool_count += 1
                tool_metric.metric("Tools", str(tool_count))

                grounded_evidence = build_grounded_evidence(final_trace)
                evidence_metric.metric(
                    "Evidence",
                    str(len(grounded_evidence)),
                )
                if grounded_evidence:
                    grounded_placeholder.dataframe(
                        grounded_evidence,
                        use_container_width=True,
                        hide_index=True,
                    )

            elif event_name == "final_answer":
                final_trace = event_data["trace"]
                status_metric.metric("Status", "Complete")
                answer_placeholder.success(event_data["answer"])

                grounded_evidence = build_grounded_evidence(final_trace)
                evidence_metric.metric(
                    "Evidence",
                    str(len(grounded_evidence)),
                )
                if grounded_evidence:
                    grounded_placeholder.dataframe(
                        grounded_evidence,
                        use_container_width=True,
                        hide_index=True,
                    )

            elif event_name == "error":
                status_metric.metric("Status", "Error")
                answer_placeholder.error(event_data["message"])
                final_trace = event_data.get("trace", final_trace)

        with trace_expander:
            st.json(final_trace)

    except requests.Timeout:
        status_metric.metric("Status", "Error")
        answer_placeholder.error(
            "The analysis request timed out. Please try again."
        )

    except requests.RequestException:
        status_metric.metric("Status", "Error")
        answer_placeholder.error(
            "The analysis service is currently unavailable. "
            "Please try again."
        )

    except SSEProtocolError:
        status_metric.metric("Status", "Error")
        answer_placeholder.error(
            "The analysis stream returned invalid data. "
            "Please retry the request."
        )
