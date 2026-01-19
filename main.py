from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import ccxt
import pandas as pd

app = FastAPI()

# Permite que o seu site (Frontend) acesse os dados do motor (Backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão MEXC
mexc = ccxt.mexc({
    'apiKey': 'SUA_API_KEY',
    'secret': 'SEU_SECRET',
    'options': {'defaultType': 'swap'}
})

@app.get("/api/market")
async def get_market():
    symbol = "BTC/USDT:USDT"
    ticker = mexc.fetch_ticker(symbol)
    # Aqui você pode processar sua lógica de IA e enviar o veredito
    return {
        "price": f"{ticker['last']:,.2f}",
        "change": f"{ticker['percentage']}%",
        "high": ticker['high'],
        "timestamp": ticker['datetime'],
        "ai_signal": "COMPRA" if ticker['last'] < ticker['low'] * 1.01 else "AGUARDANDO"
    }

# Para rodar localmente: uvicorn main:app --reload
