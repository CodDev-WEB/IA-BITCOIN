import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# --- 1. SETUP VISUAL ---
st.set_page_config(page_title="QUANT-OS V31 // FINAL", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background: #010409; color: #e0e0e0; }
    header {visibility: hidden;}
    .glass-card {
        background: rgba(13, 17, 23, 0.9);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 10px;
    }
    .neon-green { color: #00ff9d; text-shadow: 0 0 10px #00ff9d55; }
    .neon-red { color: #ff3366; text-shadow: 0 0 10px #ff336655; }
    .value { font-size: 1.5rem; font-weight: bold; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def connect_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = connect_mexc()

# --- 3. MOTOR DE ANÁLISE (SCALPER PRO) ---
def get_scalper_analysis(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # Médias Rápidas
        df['ema5'] = df['close'].ewm(span=5).mean()
        df['ema13'] = df['close'].ewm(span=13).mean()
        
        # Bollinger para saída rápida
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['upper'] = df['sma20'] + (df['std20'] * 2)
        df['lower'] = df['sma20'] - (df['std20'] * 2)
        
        # RSI Curto
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))

        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 0
        if last['ema5'] > last['ema13'] and last['rsi'] < 60: score += 2
        if last['close'] < last['lower']: score += 2
        
        if last['ema5'] < last['ema13'] and last['rsi'] > 40: score -= 2
        if last['close'] > last['upper']: score -= 2
        
        if score >= 2: return "COMPRA", "neon-green", "buy", last['close']
        if score <= -2: return "VENDA", "neon-red", "sell", last['close']
        
        return "NEUTRO", "value", None, last['close']
    except:
        return "ERRO", "value", None, 0.0

# --- 4. FUNÇÃO DE EXECUÇÃO CORRIGIDA (FIX MEXC) ---
def execute_trade(side, pair, lev, margin):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        
        # --- FIX PARA O ERRO DE POSITIONID / OPENTYPE ---
        # openType: 1 = ISOLADA, 2 = CRUZADA
        mexc.set_leverage(lev, sym, {'openType': 1}) 
        
        ticker = mexc.fetch_ticker(sym)
        price = ticker['last']
        qty = (margin * lev) / price
        
        # Criar a ordem
        order = mexc.create_market_order(sym, side, qty)
        return f"✅ {side.upper()} OK: {qty:.4f} @ {price}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("⚡ SCALPER V31")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    lev_val = st.slider("ALAVANCAGEM", 1, 100, 20)
    margin_val = st.number_input("MARGEM ($)", value=20)
    st.divider()
    bot_on = st.toggle("LIGAR ROBÔ")
    if st.button("FECHAR TUDO", use_container_width=True):
        st.warning("Comando enviado!")

st.title("QUANT-OS // V31 FINAL")

# Gráfico
st.components.v1.html(f"""
    <div id="tv-chart" style="height:380px;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{"autosize":true, "symbol":"MEXC:{asset.replace('/','')}.P", "interval":"1", "theme":"dark", "container_id":"tv-chart"}});
    </script>
""", height=380)

# --- 6. CORE ENGINE ---
@st.fragment(run_every=2)
def core():
    sym_f = f"{asset.split('/')[0]}/USDT:USDT"
    
    # Wallet
    try:
        bal = mexc.fetch_balance({'type': 'swap'})
        total = bal['USDT']['total']
    except:
        total = 0.0
        
    # Análise
    txt, color, action, price = get_scalper_analysis(sym_f)
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='glass-card'><div class='label'>EQUITY</div><div class='value'>$ {total:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='glass-card'><div class='label'>PREÇO</div><div class='value'>$ {price:,.2f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='glass-card'><div class='label'>SINAL IA</div><div class='value {color}'>{txt}</div></div>", unsafe_allow_html=True)

    if bot_on and action:
        # Cooldown de 60s
        if 'last_run' not in st.session_state or (time.time() - st.session_state.last_run > 60):
            res = execute_trade(action, asset, lev_val, margin_val)
            st.session_state.last_run = time.time()
            st.session_state.log_v31 = res
            st.toast(res)

if 'log_v31' not in st.session_state: st.session_state.log_v31 = "Aguardando sinal..."
core()

st.divider()
st.code(f"> TERMINAL: {st.session_state.log_v31}")
