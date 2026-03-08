# 📈 AI Stock Copilot

An AI-powered investment research assistant that helps users understand **stocks, market news, and portfolio risk** through automated data analysis and natural language explanations.

This project combines **financial data pipelines, quantitative analysis, and large language models (LLMs)** to create a practical decision-support tool for investors.

Instead of simply showing numbers, the copilot analyzes market data and **generates clear insights and explanations**.

---

# 🚀 Project Vision

Modern investors face three major challenges:

- Too much **financial data**
- Too much **market news**
- Difficulty understanding **portfolio risk**

AI Stock Copilot aims to solve this by acting as an **intelligent financial research assistant** that can:

- Analyze individual stocks
- Summarize and interpret market news
- Evaluate portfolio risk and diversification

The goal is to build a system that feels closer to a **Bloomberg-style research assistant powered by AI** rather than a simple stock dashboard.

---

# 🧠 Key Features

## 1. Stock Analysis

Analyze any publicly traded company using real market data.

The system retrieves financial data and computes key metrics such as:

- Price history
- Volatility
- Moving averages
- Revenue growth
- Profit margins
- Valuation ratios

The AI then generates a **plain-English investment summary** explaining the company's financial condition and valuation.


---

## 2. Market News Intelligence

Markets move quickly, and understanding **why** a stock moves is often difficult.

The News Intelligence module:

1. Collects recent financial news articles
2. Performs sentiment analysis
3. Generates concise summaries

The AI copilot highlights key developments affecting a company or sector.


---

## 3. Portfolio Analysis

Users can upload or input their investment portfolio.

The system calculates:

- Portfolio return
- Volatility
- Sharpe ratio
- Maximum drawdown
- Sector allocation

It then generates **risk insights and diversification suggestions**.

# 🏗️ System Architecture

The project is designed using a modular architecture so that new tools and analysis modules can be added easily.

```
User Input
   │
   ▼
AI Copilot Agent
   │
   ├── Stock Analysis Module
   ├── News Intelligence Module
   └── Portfolio Analysis Module
   │
   ▼
Financial Data APIs
   │
   ▼
Quantitative Analysis + AI Explanation
   │
   ▼
User Dashboard
```


---

# 🛠️ Tech Stack

### Programming Language

- Python

### Data & Quantitative Analysis

- pandas
- numpy
- scikit-learn
- ta (technical indicators)

### Financial Data

- Yahoo Finance API (via `yfinance`)
- Financial news APIs

### AI & Natural Language Processing

- LLM API (OpenAI / Gemini)
- News summarization
- Sentiment analysis

### Visualization

- Plotly / Matplotlib

### Interface

- Streamlit (interactive dashboard)

---

# 🎯 Project Goals

This project focuses on building a **practical AI-powered financial tool** while demonstrating skills in:

- Data engineering
- Quantitative finance
- Financial data analysis
- Natural language processing
- AI-assisted decision systems

The long-term goal is to expand the copilot with additional capabilities such as:

- AI-powered stock screening
- strategy backtesting
- market event explanation
- automated investment research reports

---

# 📌 Why This Project

Most stock projects focus on **price prediction**, which is often unrealistic and not very useful in practice.

This project instead focuses on **decision support**:

Helping investors **understand markets, evaluate risk, and interpret financial information** more effectively.

---

# ⚠️ Disclaimer

This project is for **educational and research purposes only**.

It does not provide financial advice or investment recommendations.

Always conduct your own research before making investment decisions.

---

# 👤 Author

Andrew Chen
Statistics & Economics  
University of California, Davis
