# AI Investment Copilot

> An agentic stock analysis system built on a **ReAct (Reason + Act) loop** — not a chatbot wrapper. The agent reasons about your query, selects and executes financial tools, observes results, and iterates until it can ground a final answer in real data.

---

## What it does

Ask a question like *"Is it a good time to write a cash-secured put on MSFT?"* and the agent autonomously:

1. Reasons about what information it needs
2. Calls the appropriate financial tools (price, volatility, options chain, quant metrics)
3. Observes each result and decides the next step
4. Produces a final answer cited entirely from tool outputs — no hallucinated numbers

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────┐
│             FastAPI Backend             │
│  POST /analyze  │  POST /compare        │
│  GET /history/{session_id}              │
└────────────────┬────────────────────────┘
                 │  SSE stream
                 ▼
┌─────────────────────────────────────────┐
│           ReAct Agent Loop              │
│  reason → select tool → execute →      │
│  observe → repeat or finalize          │
│                                         │
│  Guardrails: max iterations, tool       │
│  registry, timeout/retry, grounding     │
└──────┬────────────────────────┬─────────┘
       │                        │
       ▼                        ▼
┌─────────────┐        ┌────────────────┐
│  Tool Layer │        │  Redis Cache   │
│  (Pydantic  │        │  price history │
│   schemas)  │        │  quotes, chain │
└─────────────┘        └────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│             Tool Registry                │
│  get_price_history                       │
│  get_current_price                       │
│  get_options_chain                       │
│  get_historical_volatility               │
│  compute_momentum                        │
│  compute_statistical_divergence          │
│  compute_cash_secured_put_metrics  ★     │
│  compute_covered_call_metrics      ★     │
└──────────────────────────────────────────┘

★ Quant tools combining spot, vol, premium, break-even,
  annualized yield, and OTM probability
```

The Streamlit frontend runs in **client-only mode** — it calls the FastAPI backend over HTTP/SSE and contains no agent logic.

---

## Key Features

### ReAct Agent Loop
The agent follows a strict Reason → Act → Observe cycle with guardrails: a maximum iteration count, an explicit allowed-tool registry, invalid tool handling, and a rule that the final answer must cite tool outputs only. No hardcoded analysis sequences.

### Strict Tool Contracts
Every tool has a Pydantic input and output schema. The agent cannot pass malformed arguments or silently swallow bad responses — schema violations surface immediately as structured errors.

### Options / Quant Tools
`analyze_cash_secured_put_opportunity` is the standout tool. Given a ticker, strike, and expiry, it combines:
- Current spot price
- Implied or historical volatility
- Premium and break-even
- Annualized yield
- Probability of the option finishing OTM (profitable for the seller)

### SSE Streaming
The backend emits a structured event stream so the frontend can render agent progress in real time:

```
event: thought
event: tool_call_started
event: tool_call_finished
event: final_answer
```

### Redis Caching & Rate Limiting
Repeated ticker lookups hit Redis instead of the data provider. Rate limiting is enforced at 10 requests/min per API key.

---

## Evaluation

AI Investment Copilot includes a layered evaluation system designed to test both deterministic financial calculations and LLM behavior.

### Evaluation Layers

**1. Deterministic Unit Tests**
The financial calculation layer is tested with `pytest`, including:
- cash-secured put payoff metrics
- annualized return calculations
- technical indicators such as SMA, EMA, MACD, Bollinger Bands, and RSI
- mocked tool wrappers for market-data and options-analysis tools

**2. Golden Dataset**
A curated golden dataset of benchmark investment queries covers:
- cash-secured put analysis
- explicit strike preservation
- explicit expiration preservation
- volatility questions
- ticker comparison
- invalid ticker handling
- ambiguous company-name queries

**3. Deterministic Agent Checks**
The eval runner executes golden queries and checks:
- whether expected tools were used
- whether explicit user constraints were preserved
- whether required concepts appeared in the final answer
- whether forbidden behavior appeared

**4. LLM-as-Judge Scoring**
A secondary judge model scores final answers against the tool trace on:
- factual grounding
- reasoning quality
- hallucination control
- overall answer quality

The judge is instructed to evaluate only against the provided tool trace, not external market knowledge.

**5. Eval Persistence and Reports**
Eval runs can be saved to a local SQLite database and converted into Markdown reports for inspection and portfolio documentation.

### Running Evaluations

Run deterministic tests:

```bash
pytest
```

Run the golden eval suite with judge scoring and persistence:

```bash
python -m evals.run_golden_eval --limit 10 --judge --save-db
```

List saved eval runs:

```bash
python -m evals.list_runs
```

Generate a Markdown report from the latest saved run:

```bash
python -m evals.generate_report
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent | ReAct loop, Gemini (LLM backbone) |
| API | FastAPI, SSE, Pydantic v2 |
| Caching / Rate limiting | Redis |
| Frontend | Streamlit (client-only mode) |
| Data validation | Pydantic schemas on all tool I/O |
| Testing | pytest, LLM-as-judge eval |
| Persistence | PostgreSQL |

---

## Project Structure

agents/     Agent orchestration and reasoning loops

tools/      Tool implementations and registry

analysis/   Financial analysis and risk calculations

api/        FastAPI backend and authentication

apps/       Streamlit frontend

evals/      Golden dataset evaluation framework

tests/      Unit and integration tests

```
.
├── agents/
│   ├── react_agent.py
│   ├── stock_agent.py
│   └── schemas.py
├── analysis/
│   ├── stock_analysis.py
│   └── risk_metrics.py
├── api/
│   ├── app.py
│   ├── service.py
│   ├── auth.py
│   └── rate_limit.py
├── apps/
│   └── streamlit_app.py
├── evals/
│   ├── golden_queries.jsonl
│   ├── judge.py
│   ├── run_golden_eval.py
│   └── generate_report.py
├── tools/
│   ├── market_data.py
│   ├── options_tools.py
│   ├── cache.py
│   └── registry.py
└── tests/
```

---

## Roadmap

This project is under active development. Phases 1 and 2 are complete; Phase 3 is currently in progress.

| Phase | Goal | Status |
|---|---|---|
| 1 | ReAct agent loop, tool contracts, quant tools, guardrails | ✅ Complete |
| 2 | FastAPI backend, SSE streaming, Redis, API hygiene | ✅ Complete |
| 3 | Deterministic tests, golden dataset (40 prompts), judge-based eval, Postgres persistence | ✅ Complete |
| 4 | Docker, Terraform (ECS Fargate + ALB), GitHub Actions CI/CD | 🔄 In progress |
| 5 | Distributed tracing, structured JSON logs, latency metrics (p50/p95) | 📋 Planned |
| 6 | Polished demo UI, debug side panel (live thoughts, tool traces), architecture diagram | 📋 Planned |

---

## Getting Started

> **Note:** Full setup instructions will be added in Phase 4 alongside Docker and environment config. In the meantime, the steps below cover local development.

**Prerequisites:** Python 3.11+, Redis

```bash
git clone https://github.com/Andrewchenyh/ai-investment-copilot
cd ai-investment-copilot
pip install -r requirements.txt
```

Set environment variables:

```bash
GEMINI_API_KEY=...
REDIS_URL=redis://localhost:6379
```

Start the backend:

```bash
uvicorn app.api.main:app --reload
```

Start the frontend:

```bash
streamlit run apps/streamlit_app.py
```

---

## Why this project

Most LLM finance demos hardcode an analysis sequence and dress it up as an agent. This one isn't. The ReAct loop decides at runtime which tools to call, in what order, based on the specific query. The eval framework (Phase 3) is being built to measure whether that actually produces better answers — and to catch regressions as the model or prompts change.

---

## Author

**Andrew Chen** · Statistics & Economics, UC Davis  
[LinkedIn](https://www.linkedin.com/in/andrew-yihanchen) · [GitHub](https://github.com/Andrewchenyh)
