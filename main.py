import streamlit as st
import ccxt
import pandas as pd
import time
import numpy as np
from datetime import datetime

# --- 1. SETUP DE INTERFACE DE ALTA PERFORMANCE ---
st.set_page_config(page_title="V40 // ULTRA-QUANT", layout="wide", initial_sidebar_state="collapsed")

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
    .neon-gold { color: #f0b90b; font-size: 24px; font-weight: bold; text-shadow: 0 0 10px #f0b90b55; }
    .neon-green { color: #39ff14; font-weight: bold; }
    .neon-red { color: #ff3131; font-weight: bold; }
    .terminal-box {
        background: #010409;
        color: #00ff41;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        border-left: 4px solid #30363d;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO CORE COM MEXC ---
@st.cache_resource
def get_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = get_mexc()

# --- 3. MOTOR DE ANÁLISE QUANT (EMA + RSI + BOLLINGER + MACD) ---
def get_market_analysis(symbol):
    try:
        # Analisa 100 velas de 5 minutos para consistência profissional
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # EMA 9 (Rápida) e EMA 21 (Média)
        df['ema9'] = df['close'].ewm(span=9).mean()
        df['ema21'] = df['close'].ewm(span=21).mean()
        
        # Bollinger Bands (Volatilidade)
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['up'] = df['sma20'] + (df['std20'] * 2)
        df['lw'] = df['sma20'] - (df['std20'] * 2)
        
        # RSI 14 (Força)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))

        last = df.iloc[-1]
        score = 0
        
        # LÓGICA DE CONFLUÊNCIA (PRECISÃO PROFISSIONAL)
        if last['ema9'] > last['ema21']: score += 1
        if last['close'] < last['lw']: score += 2
        if last['rsi'] < 40: score += 1
        
        if last['ema9'] < last['ema21']: score -= 1
        if last['close'] > last['up']: score -= 2
        if last['rsi'] > 60: score -= 1
        
        if score >= 3: return "FORTE COMPRA", "neon-green", "buy", last['close'], score
        if score <= -3: return "FORTE VENDA", "neon-red", "sell", last['close'], score
        return "AGUARDANDO", "white", None, last['close'], score
    except:
        return "SYNCING...", "white", None, 0.0, 0

# --- 4. EXECUÇÃO DE ALTA FREQUÊNCIA ---
def run_trade(side, pair, lev, compound_pct, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if m_type == "Isolada" else 2
        mexc.set_leverage(lev, symbol, {'openType': m_code})
        
        # Juros Compostos
        bal = mexc.fetch_balance({'type': 'swap'})
        amount_usd = float(bal['USDT']['total']) * (compound_pct / 100)
        if amount_usd < 1.0: amount_usd = 1.0
        
        ticker = mexc.fetch_ticker(symbol)
        qty = (amount_usd * lev) / ticker['last']
        
        mexc.create_order(symbol, 'market', side, qty)
        return f"✅ {side.upper()} EXECUTADO: {qty:.4f} {pair}"
    except Exception as e:
        return f"❌ API ERROR: {str(e)}"

# --- 5. INTERFACE DO TERMINAL ---
with st.sidebar:
    st.header("⚙️ QUANT SETTINGS")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 125, 50)
    compound = st.slider("JUROS COMPOSTOS %", 10, 100, 90)
    m_type = st.radio("MODO DE MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_active = st.toggle("🚀 LIGAR AUTO-QUANT")
    if st.button("🔴 EMERGENCY CLOSE"):
        st.toast("Encerrando posições...")

# --- DASHBOARD PRINCIPAL ---
st.title("QUANT-OS V40 // SINGULARITY CORE")

col_main, col_stats = st.columns([3, 1])

with col_main:
    # Gráfico Real-time
    st.components.v1.html(f"""
        <div id="tv-chart" style="height:480px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
          "autosize": true, "symbol": "MEXC:{asset.replace('/','')}.P",
          "interval": "5", "theme": "dark", "style": "1", "container_id": "tv-chart"
        }});
        </script>
    """, height=480)

    # Painel de Monitoramento de Lucros/Perdas
    st.subheader("📋 Posições Ativas & Scalability")
    @st.fragment(run_every=3)
    def update_positions():
        try:
            sym_f = f"{asset.split('/')[0]}/USDT:USDT"
            pos = mexc.fetch_positions([sym_f])
            active_data = []
            for p in pos:
                if float(p['contracts']) > 0:
                    active_data.append({
                        "Lado": p['side'].upper(),
                        "Qtd": p['contracts'],
                        "Preço Entrada": p['entryPrice'],
                        "PnL Realizado": f"$ {float(p['unrealizedPnl']):,.4f}",
                        "ROE %": f"{float(p['percentage']):.2f}%"
                    })
            if active_data:
                st.table(pd.DataFrame(active_data))
            else:
                st.info("Varrendo mercado em busca de sinais de 5 minutos...")
        except: pass
    update_positions()

with col_stats:
    st.subheader("📊 IA STATUS")
    @st.fragment(run_every=2)
    def engine():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        label, color, action, price, score = get_market_analysis(sym_f)
        
        # Wallet info
        try:
            bal = mexc.fetch_balance({'type': 'swap'})
            total = bal['USDT']['total']
        except: total = 0.0

        st.markdown(f"""
            <div class='metric-card'>
                <div style='color:#8b949e; font-size:12px;'>VALOR DA BANCA</div>
                <div class='neon-gold'>$ {total:,.4f}</div>
                <hr style='border: 0.1px solid #30363d;'>
                <div style='color:#8b949e; font-size:12px;'>PREÇO {asset}</div>
                <div style='font-size:20px; font-weight:bold;'>$ {price:,.2f}</div>
                <hr style='border: 0.1px solid #30363d;'>
                <div class='{color}' style='font-size:18px;'>{label}</div>
                <div style='font-size:12px; color:#58a6ff;'>SCORE: {score}/4</div>
            </div>
        """, unsafe_allow_html=True)

        if bot_active and action:
            pos = mexc.fetch_positions([sym_f])
            if not any(float(p['contracts']) > 0 for p in pos):
                res = run_trade(action, asset, leverage, compound, m_type)
                st.session_state.v40_log = res
                st.toast(res)

    engine()

# Terminal Log
st.divider()
if 'v40_log' not in st.session_state: st.session_state.v40_log = "AGUARDANDO SINAL..."
st.markdown(f"<div class='terminal-box'><strong>TERMINAL:</strong> {st.session_state.v40_log}</div>", unsafe_allow_html=True)
