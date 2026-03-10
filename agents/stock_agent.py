"""
stock_agent.py

AI agent that interprets user stock queries using the Gemini API
and decides which analysis functions to run.

Responsibilities:
- Parse user intent
- Extract ticker and indicator settings
- Fetch stock data
- Compute technical indicators
- Return structured analysis
"""

import os
import json
import google.generativeai as genai


from tools.market_data import MarketDataEngine
from analysis.stock_analysis import add_all_indicators

class StockAgent:

    def __init__(self):

        # Load Gemini API key
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # Initialize model
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def interpret_query(self, query: str) -> dict:
        """
        Ask Gemini to convert a natural language query
        into structured parameters.
        """

        prompt = f"""
                    You are a financial assistant.

                    Extract structured parameters from the user request.

                    Return JSON with the following fields:

                    ticker: stock ticker
                    sma_window: integer or null
                    ema_window: integer or null
                    rsi_window: integer or null
                    analysis: short description of what the user wants

                    User request:
                    {query}

                    Return ONLY JSON.
                """

        response = self.model.generate_content(prompt)

        try:
            result = json.loads(response.text)
        except Exception:
            raise ValueError("Failed to parse Gemini response")

        return result

    def run_analysis(self, config: dict):
        """
        Run stock analysis using extracted parameters.
        """

        ticker = config.get("ticker")

        sma = config.get("sma_window") or 20
        ema = config.get("ema_window") or 20
        rsi = config.get("rsi_window") or 14

        # Fetch data
        engine = MarketDataEngine()
        data = engine.get_full_stock_data(ticker=ticker)
        df = data["price_date"]

        # Add indicators
        df = add_all_indicators(df, config)

        return df.tail()

    def ask(self, query: str):
        """
        Main entry point for the agent.
        """

        params = self.interpret_query(query)

        result = self.run_analysis(params)

        return {
            "parameters": params,
            "analysis_result": result.to_dict()
        }