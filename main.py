import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="V45.1 // OMNI-QUANT", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #010409; color: #e6edf3; }
    header {visibility: hidden;}
    .metric-card {
        background: #0d1117; border: 1px solid #30363d; border-radius: 10px;
        padding: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .neon-gold { color: #f0b90b; font-weight: bold; text-shadow: 0 0 10px #f0b90b55; }
    .neon-green { color: #39ff14; font-weight: bold; }
    .neon-red { color: #ff3131; font-weight: bold; }
    .terminal-box {
        background: #000; color: #00ff41; padding: 12px;
        border-radius: 5px; font-family: 'Courier New', monospace; font-size: 0.8rem;
        border-left: 4px solid #f0b90b;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM ENGINE MEXC ---
@st.cache_resource
def init_exchange():
    try:
        return ccxt.mexc({
            'apiKey': st.secrets["API_KEY"],
            'secret': st.secrets["SECRET_KEY"],
            'options': {'defaultType': 'swap', 'adjustForTimeDifference': True},
            'enableRateLimit': True
        })
    except Exception as e:
        st.error(f"Erro ao conectar API: {e}")
        return None

mexc = init_exchange()

# --- 3. MOTOR DE ANÁLISE OMNI ---
def get_omni_signals(symbol):
    try:
        # Busca OHLCV
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # VWAP
        df['tp'] = (df['h'] + df['l'] + df['c']) / 3
        df['vwap'] = (df['tp'] * df['v']).cumsum() / df['v'].cumsum()
        dist_vwap = ((df['c'].iloc[-1] / df['vwap'].iloc[-1]) - 1) * 100
        
        # EMAs 3 e 8
        df['ema3'] = df['c'].ewm(span=3).mean()
        df['ema8'] = df['c'].ewm(span=8).mean()
        
        # RSI 7
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        rs = gain / (loss + 1e-9) # Evita divisão por zero
        rsi7 = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Order Book Imbalance
        ob = mexc.fetch_order_book(symbol, limit=10)
        bid_vol = sum([b[1] for b in ob['bids']])
        ask_vol = sum([a[1] for a in ob['asks']])
        imbalance = (bid_vol / (bid_vol + ask_vol)) - 0.5
        
        score = 0
        if df['ema3'].iloc[-1] > df['ema8'].iloc[-1]: score += 1
        if imbalance > 0.1: score += 1
        if rsi7 < 35: score += 1
        if dist_vwap < -0.2: score += 1

        if df['ema3'].iloc[-1] < df['ema8'].iloc[-1]: score -= 1
        if imbalance < -0.1: score -= 1
        if rsi7 > 65: score -= 1
        if dist_vwap > 0.2: score -= 1

        action = 'buy' if score >= 3 else 'sell' if score <= -3 else None
        
        return {
            "action": action, "price": df['c'].iloc[-1], "score": score,
            "rsi": rsi7, "vwap_dist": dist_vwap, "imbalance": imbalance,
            "exit_long": (rsi7 > 80 or df['c'].iloc[-1] < df['ema3'].iloc[-1]),
            "exit_short": (rsi7 < 20 or df['c'].iloc[-1] > df['ema3'].iloc[-1])
        }
    except:
        return None

# --- 4. FUNÇÕES DE EXECUÇÃO ---
def execute_trade(side, pair, lev, compound_pct, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if m_type == "Isolada" else 2
        mexc.set_leverage(int(lev), symbol, {'openType': m_code})

        bal = mexc.fetch_balance({'type': 'swap'})
        amount_usd = float(bal['USDT']['free']) * (compound_pct / 100)
        
        if amount_usd < 5.0: return "❌ Mínimo não atingido ($5)"

        ticker = mexc.fetch_ticker(symbol)
        raw_qty = (amount_usd * lev) / ticker['last']
        qty = mexc.amount_to_precision(symbol, raw_qty)

        mexc.create_market_order(symbol, side, qty)
        return f"🔥 {side.upper()} ABERTO | Qtd: {qty}"
    except Exception as e:
        return f"❌ ERRO: {str(e)}"

def close_position(symbol):
    try:
        pos = mexc.fetch_positions([symbol])
        for p in pos:
            if float(p['contracts']) > 0:
                side = 'sell' if p['side'] == 'long' else 'buy'
                mexc.create_market_order(symbol, side, p['contracts'])
                return "💰 LUCRO REALIZADO"
        return None
    except: return None

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("⚡ OMNI CONTROL")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 125, 50)
    compound = st.slider("COMPOUND %", 10, 100, 90)
    m_type = st.radio("MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_active = st.toggle("ATIVAR IA OMNI-QUANT")

st.title("V45.1 // OMNI-QUANT (FIXED)")

col_main, col_data = st.columns([3, 1])

with col_main:
    st.components.v1.html(f"""
        <div id="tv" style="height:400px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"1","theme":"dark","style":"1","container_id":"tv"}});</script>
    """, height=400)
    
    st.subheader("📋 Gestão de Posições")
    @st.fragment(run_every=2)
    def manage_orders():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        signals = get_omni_signals(sym_f)
        if signals:
            try:
                pos = mexc.fetch_positions([sym_f])
                active = [p for p in pos if float(p['contracts']) > 0]
                if active:
                    p = active[0]
                    st.success(f"{p['side'].upper()} | ROE: {p['percentage']}% | PnL: ${p['unrealizedPnl']}")
                    if (p['side'] == 'long' and signals['exit_long']) or (p['side'] == 'short' and signals['exit_short']):
                        res = close_position(sym_f)
                        st.session_state.log_final = res
                        st.toast(res)
                else:
                    if bot_active and signals['action']:
                        res = execute_trade(signals['action'], asset, leverage, compound, m_type)
                        st.session_state.log_final = res
                        st.toast(res)
            except: pass
    manage_orders()

with col_data:
    st.subheader("📊 STATUS")
    @st.fragment(run_every=2)
    def update_stats():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        s = get_omni_signals(sym_f)
        try:
            bal = mexc.fetch_balance({'type': 'swap'})
            total = bal['USDT']['total']
            st.markdown(f"<div class='metric-card'>BANCA: <span class='neon-gold'>$ {total:,.4f}</span></div>", unsafe_allow_html=True)
        except: pass
        if s:
            st.markdown(f"""
                <div class='metric-card'>
                    <div class='{"neon-green" if s["score"] > 0 else "neon-red" if s["score"] < 0 else "white"}'>{s["action"].upper() if s["action"] else "NEUTRAL"}</div>
                    <div style='font-size:12px;'>SCORE: {s["score"]} | RSI: {s["rsi"]:.1f}</div>
                </div>
            """, unsafe_allow_html=True)
    update_stats()

if 'log_final' not in st.session_state: st.session_state.log_final = "ONLINE"
st.markdown(f"<div class='terminal-box'>LOG: {st.session_state.log_final}</div>", unsafe_allow_html=True)
