from agents.stock_agent import StockAgent

agent = StockAgent()

query = "Analyze Apple using RSI 7 and a 50 day moving average"

response = agent.ask(query)

print(response)