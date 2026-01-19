from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import ccxt
import pandas as pd

app = FastAPI()

# Permite que o site acesse os dados
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

mexc = ccxt.mexc({
    'apiKey': 'SUA_API_KEY',
    'secret': 'SEU_SECRET',
    'options': {'defaultType': 'swap'}
})

@app.get("/api/data")
async def get_data():
    symbol = "BTC/USDT:USDT"
    ticker = mexc.fetch_ticker(symbol)
    # Aqui você pode adicionar sua lógica de RSI/Bollinger
    return {
        "price": ticker['last'],
        "high": ticker['high'],
        "low": ticker['low'],
        "timestamp": ticker['datetime']
    }

# Para rodar: uvicorn app:app --reload
