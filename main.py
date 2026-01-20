import streamlit as st
import ccxt
import pandas as pd
import time
import numpy as np
from datetime import datetime

# --- 1. SETUP DE INTERFACE ---
st.set_page_config(page_title="V41 // HYPER-SCALPER", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    header {visibility: hidden;}
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .neon-gold { color: #f0b90b; font-size: 26px; font-weight: bold; text-shadow: 0 0 10px #f0b90b55; }
    .neon-green { color: #39ff14; font-weight: bold; }
    .neon-red { color: #ff3131; font-weight: bold; }
    .terminal-box {
        background: #010409;
        color: #00ff41;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        border-left: 4px solid #f0b90b;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO CORE ---
@st.cache_resource
def get_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = get_mexc()

# --- 3. MOTOR DE ANÁLISE HYPER (EMA 3/8 + RSI + BOLLINGER) ---
def get_hyper_analysis(symbol):
    try:
        # Puxa 100 velas (Timeframe de 1m ou 5m conforme selecionado)
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # --- ATUALIZAÇÃO: EMA 3 (Gatilho) e EMA 8 (Tendência Curta) ---
        df['ema3'] = df['close'].ewm(span=3).mean()
        df['ema8'] = df['close'].ewm(span=8).mean()
        
        # Bollinger Bands para reversão rápida
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['up'] = df['sma20'] + (df['std20'] * 2)
        df['lw'] = df['sma20'] - (df['std20'] * 2)
        
        # RSI 7 (Rápido para Scalping)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))

        last = df.iloc[-1]
        score = 0
        
        # LÓGICA DE CONFLUÊNCIA V41
        # Compra: EMA3 acima da 8 + Preço nas bandas + RSI baixo
        if last['ema3'] > last['ema8']: score += 1
        if last['close'] < last['lw']: score += 2
        if last['rsi'] < 30: score += 1
        
        # Venda: EMA3 abaixo da 8 + Preço nas bandas + RSI alto
        if last['ema3'] < last['ema8']: score -= 1
        if last['close'] > last['up']: score -= 2
        if last['rsi'] > 70: score -= 1
        
        if score >= 3: return "HYPER COMPRA", "neon-green", "buy", last['close'], score
        if score <= -3: return "HYPER VENDA", "neon-red", "sell", last['close'], score
        return "MONITORANDO", "white", None, last['close'], score
    except:
        return "SYNCING...", "white", None, 0.0, 0

# --- 4. EXECUÇÃO DE ORDENS ---
def execute_order(side, pair, lev, compound_pct, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if m_type == "Isolada" else 2
        mexc.set_leverage(lev, symbol, {'openType': m_code})
        
        bal = mexc.fetch_balance({'type': 'swap'})
        amount_usd = float(bal['USDT']['total']) * (compound_pct / 100)
        if amount_usd < 1.0: amount_usd = 1.0
        
        ticker = mexc.fetch_ticker(symbol)
        qty = (amount_usd * lev) / ticker['last']
        
        mexc.create_order(symbol, 'market', side, qty)
        return f"🔥 {side.upper()} DISPARADO: {qty:.4f} {pair}"
    except Exception as e:
        return f"❌ ERRO: {str(e)}"

# --- 5. DASHBOARD ---
with st.sidebar:
    st.header("⚡ HYPER CONTROL")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 125, 50)
    compound = st.slider("COMPOUND %", 10, 100, 95)
    m_type = st.radio("MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_active = st.toggle("LIGAR IA HYPER-SCALPER")

st.title("QUANT-OS V41 // HYPER-SCALPER (EMA 3/8)")

col1, col2 = st.columns([3, 1])

with col1:
    st.components.v1.html(f"""
        <div id="tv-chart" style="height:480px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
          "autosize": true, "symbol": "MEXC:{asset.replace('/','')}.P",
          "interval": "1", "theme": "dark", "style": "1", "container_id": "tv-chart"
        }});
        </script>
    """, height=480)

    # Monitor de Posições
    @st.fragment(run_every=3)
    def update_pos():
        try:
            sym_f = f"{asset.split('/')[0]}/USDT:USDT"
            pos = mexc.fetch_positions([sym_f])
            active_data = [p for p in pos if float(p['contracts']) > 0]
            if active_data:
                st.table(pd.DataFrame(active_data)[['side', 'contracts', 'entryPrice', 'unrealizedPnl', 'percentage']])
            else:
                st.info("Aguardando cruzamento das EMAs 3/8...")
        except: pass
    update_pos()

with col2:
    st.subheader("📡 LIVE FEED")
    @st.fragment(run_every=2)
    def live_feed():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        label, color, action, price, score = get_hyper_analysis(sym_f)
        
        try:
            bal = mexc.fetch_balance({'type': 'swap'})
            total = bal['USDT']['total']
        except: total = 0.0

        st.markdown(f"""
            <div class='metric-card'>
                <div style='color:#8b949e; font-size:12px;'>BANCA ATUAL</div>
                <div class='neon-gold'>$ {total:,.4f}</div>
                <hr style='border: 0.1px solid #30363d;'>
                <div style='color:#8b949e; font-size:12px;'>SINAL EMA 3/8</div>
                <div class='{color}' style='font-size:20px;'>{label}</div>
                <div style='font-size:12px; color:#58a6ff;'>SCORE: {score}/4</div>
            </div>
        """, unsafe_allow_html=True)

        if bot_active and action:
            pos = mexc.fetch_positions([sym_f])
            if not any(float(p['contracts']) > 0 for p in pos):
                res = execute_order(action, asset, leverage, compound, m_type)
                st.session_state.v41_log = res
                st.toast(res)
    live_feed()

st.divider()
if 'v41_log' not in st.session_state: st.session_state.v41_log = "AGUARDANDO OPORTUNIDADE"
st.markdown(f"<div class='terminal-box'><strong>TERMINAL:</strong> {st.session_state.v41_log}</div>", unsafe_allow_html=True)
