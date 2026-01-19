import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE INTERFACE CYBER-SCALPER ---
st.set_page_config(page_title="TURBO SCALPER V28", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background: #020202; color: #ffffff; }
    header {visibility: hidden;}
    .scalp-card {
        background: rgba(10, 10, 15, 0.9);
        border: 1px solid #333;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,255,157,0.1);
    }
    .neon-text { font-family: 'Courier New', monospace; font-weight: bold; }
    .label { font-size: 0.7rem; color: #555; text-transform: uppercase; }
    .value { font-size: 1.4rem; color: #fff; }
    .buy-signal { color: #00ff9d; text-shadow: 0 0 10px #00ff9d55; }
    .sell-signal { color: #ff3366; text-shadow: 0 0 10px #ff336655; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO DIRETA (MEXC FUTURES) ---
@st.cache_resource
def connect():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = connect()

# --- 3. MOTOR SCALPER (M1 - ESTRATÉGIA AGRESSIVA) ---
def get_scalper_intelligence(symbol):
    try:
        # Puxa apenas as últimas 30 velas de 1 minuto (Alta Velocidade)
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=30)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # Indicadores de Curto Prazo (Scalping)
        df['ema_fast'] = df['close'].ewm(span=5).mean()  # Média ultra rápida
        df['ema_slow'] = df['close'].ewm(span=13).mean() # Média de confirmação
        
        # RSI Curto (7 períodos) para identificar topos e fundos rápidos
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))

        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # LÓGICA SCALPER:
        # ENTRADA COMPRA: EMA 5 cruza acima da 13 + RSI saindo da zona de 30
        if last['ema_fast'] > last['ema_slow'] and prev['ema_fast'] <= prev['ema_slow'] and last['rsi'] < 50:
            return "SCALP BUY (LONG)", "buy-signal", "buy", last['close'], last['rsi']
        
        # ENTRADA VENDA: EMA 5 cruza abaixo da 13 + RSI saindo da zona de 70
        elif last['ema_fast'] < last['ema_slow'] and prev['ema_fast'] >= prev['ema_slow'] and last['rsi'] > 50:
            return "SCALP SELL (SHORT)", "sell-signal", "sell", last['close'], last['rsi']
            
        return "MONITORANDO...", "label", None, last['close'], last['rsi']
    except:
        return "SYNC...", "label", None, 0.0, 50.0

# --- 4. EXECUÇÃO DE ALTA VELOCIDADE ---
def execute_quick_trade(side, pair, lev, margin):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        mexc.set_leverage(lev, sym)
        ticker = mexc.fetch_ticker(sym)
        price = ticker['last']
        qty = (margin * lev) / price
        
        # Abre a ordem a mercado
        mexc.create_market_order(sym, side, qty)
        return f"SCALP {side.upper()} @ {price} | VOL: {qty:.3f}"
    except Exception as e:
        return f"ERRO: {e}"

# --- 5. INTERFACE DO TERMINAL ---
with st.sidebar:
    st.markdown("### ⚡ TURBO SCALPER SETTINGS")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT"])
    lev = st.slider("ALAVANCAGEM", 1, 100, 50) # Scalpers usam alavancagem alta
    trade_margin = st.number_input("MARGEM POR TIRO ($)", value=25)
    st.divider()
    bot_active = st.toggle("🚨 ACTIVAR SCALPER AUTOMÁTICO", value=False)
    st.info("Modo Scalper: Entradas baseadas em EMA 5/13 + RSI 7.")

st.title("⚡ TURBO-QUANT SCALPER")

# Gráfico de 1 Minuto (Obrigatório para Scalping)
st.components.v1.html(f"""
    <div id="tv-chart" style="height:350px;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{
        "autosize": true, "symbol": "MEXC:{asset.replace('/','')}.P",
        "interval": "1", "theme": "dark", "style": "1", "container_id": "tv-chart", "hide_side_toolbar": true
    }});
    </script>
""", height=350)

# --- 6. SCALPER CORE ENGINE ---
@st.fragment(run_every=2) # Atualização a cada 2 segundos
def run_scalper():
    sym_f = f"{asset.split('/')[0]}/USDT:USDT"
    
    # Wallet Status
    bal = mexc.fetch_balance({'type': 'swap'})
    equity = bal['USDT']['total']
    available = bal['USDT']['free']
    
    # AI Analysis
    msg, style, action, price, rsi_val = get_scalper_intelligence(sym_f)
    
    # Display Dashboard
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='scalp-card'><div class='label'>EQUITY</div><div class='value'>$ {equity:,.2f}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='scalp-card'><div class='label'>IA SIGNAL</div><div class='value {style}'>{msg}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='scalp-card'><div class='label'>PREÇO</div><div class='value'>$ {price:,.2f}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='scalp-card'><div class='label'>RSI-7</div><div class='value'>{rsi_val:.1f}</div></div>", unsafe_allow_html=True)

    # Lógica de Execução Instantânea
    if bot_active and action:
        # Cooldown curto de 30 segundos (Scalper precisa de agilidade)
        if 'last_scalp' not in st.session_state or (time.time() - st.session_state.last_scalp > 30):
            if available >= trade_margin:
                res = execute_quick_trade(action, asset, lev, trade_margin)
                st.session_state.last_scalp = time.time()
                st.session_state.scalp_log = res
                st.toast(res, icon="🔥")

if 'scalp_log' not in st.session_state: st.session_state.scalp_log = "AGUARDANDO OPORTUNIDADE..."

run_scalper()

st.divider()
st.subheader("📟 SCALPER TERMINAL LOG")
st.code(f"> {st.session_state.scalp_log}")
