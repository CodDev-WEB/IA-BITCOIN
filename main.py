import streamlit as st
import ccxt
import pandas as pd
import time
import numpy as np

# --- 1. SETUP DE INTERFACE ---
st.set_page_config(page_title="V42 // OMNI-QUANT", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #010409; color: #e6edf3; }
    header {visibility: hidden;}
    .metric-card {
        background: #0d1117; border: 1px solid #30363d; border-radius: 10px;
        padding: 15px; text-align: center;
    }
    .neon-blue { color: #00d4ff; text-shadow: 0 0 10px #00d4ff55; font-weight: bold; }
    .neon-green { color: #39ff14; font-weight: bold; }
    .neon-red { color: #ff3131; font-weight: bold; }
    .terminal-box {
        background: #000; color: #0f0; padding: 12px;
        border-radius: 5px; font-family: monospace; font-size: 0.8rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM ENGINE ---
@st.cache_resource
def init_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = init_mexc()

# --- 3. MOTOR OMNI-ANALYSIS (CRÍTICO) ---
def get_omni_signals(symbol):
    try:
        # A. Busca OHLCV (1m e 3m)
        ohlcv1m = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv1m, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # B. VWAP e Distância
        df['tp'] = (df['h'] + df['l'] + df['c']) / 3
        df['vwap'] = (df['tp'] * df['v']).cumsum() / df['v'].cumsum()
        dist_vwap = ((df['c'].iloc[-1] / df['vwap'].iloc[-1]) - 1) * 100
        
        # C. EMAs 9/21 e RSI Curto (7)
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema21'] = df['c'].ewm(span=21).mean()
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        rsi7 = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        
        # D. Dados Institucionais (Funding & Open Interest)
        params = {'symbol': symbol}
        funding = mexc.fetch_funding_rate(symbol)
        f_rate = funding['fundingRate'] if funding else 0
        
        # E. Order Book (Liquidez Nível 1)
        ob = mexc.fetch_order_book(symbol, limit=5)
        bid_vol = sum([b[1] for b in ob['bids']])
        ask_vol = sum([a[1] for a in ob['asks']])
        book_imbalance = (bid_vol / (bid_vol + ask_vol)) - 0.5

        # F. Velocidade do Preço (Price Velocity)
        velocity = (df['c'].iloc[-1] - df['c'].iloc[-5]) / 5

        # --- SCORE ENGINE (PESOS CRÍTICOS) ---
        score = 0
        # Tendência e Momentum
        if df['ema9'].iloc[-1] > df['ema21'].iloc[-1]: score += 1
        if rsi7 < 30: score += 2 # Sobrevenda extrema
        if rsi7 > 70: score -= 2 # Sobrecompra extrema
        
        # Liquidez e Volume
        if book_imbalance > 0.1: score += 1.5 # Pressão de compra no book
        if book_imbalance < -0.1: score -= 1.5 # Pressão de venda no book
        
        # Distância VWAP (Reversão à média)
        if dist_vwap < -0.5: score += 2 # Muito abaixo da VWAP
        if dist_vwap > 0.5: score -= 2 # Muito acima da VWAP

        # Decisão Final
        action = None
        if score >= 3.5: action = "buy"
        elif score <= -3.5: action = "sell"
        
        return {
            "label": "BUY ALERT" if action == "buy" else "SELL ALERT" if action == "sell" else "NEUTRAL",
            "color": "neon-green" if action == "buy" else "neon-red" if action == "sell" else "white",
            "action": action,
            "price": df['c'].iloc[-1],
            "score": score,
            "vwap_dist": dist_vwap,
            "funding": f_rate
        }
    except Exception as e:
        st.error(f"Erro na análise: {e}")
        return None

# --- 4. EXECUÇÃO DE ALTA FREQUÊNCIA ---
def execute_omni_trade(side, pair, lev, compound_pct, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if m_type == "Isolada" else 2
        mexc.set_leverage(lev, symbol, {'openType': m_code})
        
        bal = mexc.fetch_balance({'type': 'swap'})
        amount = float(bal['USDT']['total']) * (compound_pct / 100)
        
        ticker = mexc.fetch_ticker(symbol)
        qty = (amount * lev) / ticker['last']
        
        order = mexc.create_order(symbol, 'market', side, qty)
        return f"🚀 {side.upper()} EXECUTADO | QTY: {qty:.4f}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("⚙️ OMNI SETTINGS")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 100, 20)
    compound = st.slider("COMPOUND %", 10, 100, 80)
    m_type = st.radio("MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_active = st.toggle("LIGAR IA OMNI-QUANT")

st.title("QUANT-OS V42 // OMNI-ENGINE")

c_main, c_data = st.columns([3, 1])

with c_main:
    st.components.v1.html(f"""
        <div id="tv" style="height:450px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"1","theme":"dark","style":"1","container_id":"tv"}});</script>
    """, height=450)
    
    @st.fragment(run_every=3)
    def position_table():
        try:
            sym_f = f"{asset.split('/')[0]}/USDT:USDT"
            pos = mexc.fetch_positions([sym_f])
            data = [p for p in pos if float(p['contracts']) > 0]
            if data: st.dataframe(pd.DataFrame(data)[['side', 'contracts', 'entryPrice', 'unrealizedPnl', 'percentage']], use_container_width=True)
            else: st.info("Buscando liquidez e desequilíbrio de ordens...")
        except: pass
    position_table()

with c_data:
    st.subheader("🧠 IA BRAIN")
    @st.fragment(run_every=2)
    def brain_engine():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        data = get_omni_signals(sym_f)
        
        if data:
            st.markdown(f"""
                <div class='metric-card'>
                    <div style='color:#8b949e; font-size:12px;'>PREÇO ATUAL</div>
                    <div style='font-size:22px; font-weight:bold;'>$ {data['price']:,.2f}</div>
                    <hr style='border:0.1px solid #30363d;'>
                    <div class='{data['color']}' style='font-size:18px;'>{data['label']}</div>
                    <div style='font-size:12px; color:#00d4ff;'>SCORE: {data['score']}</div>
                    <div style='font-size:11px; color:#8b949e;'>DIST. VWAP: {data['vwap_dist']:.3f}%</div>
                    <div style='font-size:11px; color:#8b949e;'>FUNDING: {data['funding']:.5f}</div>
                </div>
            """, unsafe_allow_html=True)

            if bot_active and data['action']:
                pos = mexc.fetch_positions([sym_f])
                if not any(float(p['contracts']) > 0 for p in pos):
                    res = execute_omni_trade(data['action'], asset, leverage, compound, m_type)
                    st.session_state.log42 = res
                    st.toast(res)
    brain_engine()

st.divider()
if 'log42' not in st.session_state: st.session_state.log42 = "OMNI SYSTEM ONLINE"
st.markdown(f"<div class='terminal-box'><strong>TERMINAL:</strong> {st.session_state.log42}</div>", unsafe_allow_html=True)
