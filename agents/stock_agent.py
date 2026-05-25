import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pydantic import BaseModel, Field
from typing import List
from google import genai
from tools.market_data import MarketDataEngine
from analysis.stock_analysis import add_all_indicators
from dotenv import load_dotenv

# Define the expected JSON structure using Pydantic
class StockQuerySchema(BaseModel):
    ticker: str
    sma_windows: List[int] | None = None
    ema_windows: List[int] | None = None
    rsi_windows: List[int] | None = None
    bb_windows: List[int] | None = None

class StockAgent:
    def __init__(self):
        load_dotenv() 
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.5-flash" 
        self.engine = MarketDataEngine()
        
    def interpret_query(self, query: str) -> StockQuerySchema:
        """
        Uses Gemini's response_schema to guarantee valid JSON output.
        """
       
        prompt = f"""
                    You are a financial analysis assistant.

                    Extract structured parameters from the user's request.

                    Rules:
                    - Always return a valid ticker symbol.
                    - If no indicator windows are specified, use defaults.
                    - Windows should be integers.

                    Defaults:
                    SMA: [20]
                    EMA: [20]
                    RSI: [14]
                    Bollinger Bands: [20]

                    User request:
                    {query}
                """
        
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': StockQuerySchema,
            },
        )
        
        return StockQuerySchema.model_validate_json(response.text) # type: ignore

    def run_analysis(self, params: StockQuerySchema):
        data = self.engine.get_full_stock_data(ticker=params.ticker)
        df = data["price_data"]

        df = add_all_indicators(df, params.model_dump())      
        
        return df.tail(1)

    def ask(self, query: str):
        try:
            params = self.interpret_query(query)
            result = self.run_analysis(params)
            return {"status": "success", "ticker": params.ticker, "data": result.to_dict()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        

# Test run
if __name__ == '__main__':
    agent = StockAgent()
    query = "Analyze Apple using RSI 7 and a 50 day moving average"
    response = agent.ask(query)
    print(response)
    
