import streamlit as st
import ccxt
import pandas as pd
import time
import requests
from datetime import datetime

# --- CONFIGURAÇÕES DE ACESSO ---
API_KEY = "mx0vglJziCrmexC8ti"
SECRET_KEY = "bec4bc2824914e8bbc01e42cc8d85883"
TELEGRAM_TOKEN = "SEU_TOKEN_AQUI"
TELEGRAM_CHAT_ID = "SEU_ID_AQUI"

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={message}"
        requests.get(url)
    except: pass

st.set_page_config(page_title="IA HUMAN_QUANT V1", layout="wide")

@st.cache_resource
def connect_mexc():
    return ccxt.mexc({'apiKey': API_KEY, 'secret': SECRET_KEY, 'options': {'defaultType': 'swap'}, 'enableRateLimit': True})

mexc = connect_mexc()

# --- CÉREBRO MATEMÁTICO ---
def get_analysis(symbol):
    candles = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=100)
    df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    # Indicadores
    df['ema_fast'] = df['close'].ewm(span=9).mean()
    df['ema_slow'] = df['close'].ewm(span=21).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain/loss)))
    return df

st.title("🤖 IA QUANT - STATUS OPERACIONAL")
bot_on = st.toggle("ATIVAR IA NA NUVEM")

if bot_on:
    send_telegram("🚀 IA Iniciada. Monitorando mercado 24h...")
    while True:
        try:
            pair = "BTC/USDT:USDT"
            df = get_analysis(pair)
            price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            
            # GESTÃO DE BANCA: Lê saldo real
            balance = mexc.fetch_balance()['total']['USDT']
            # Usa 10% do saldo com alavancagem 10x (Configuração Humana de Risco)
            qty = (balance * 0.10 * 10) / price 

            # Lógica de Execução (Simplificada para Nuvem)
            if rsi < 30:
                mexc.create_market_buy_order(pair, qty)
                send_telegram(f"🟢 COMPRA EXECUTADA\nPreço: {price}\nSaldo: {balance} USDT")
                time.sleep(600) # Pausa 10 min após trade

            elif rsi > 70:
                mexc.create_market_sell_order(pair, qty)
                send_telegram(f"🔴 VENDA EXECUTADA\nPreço: {price}\nSaldo: {balance} USDT")
                time.sleep(600)

            time.sleep(30)
        except Exception as e:
            st.error(f"Erro: {e}")
            time.sleep(30)
