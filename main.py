import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# --- 1. SETUP DE INTERFACE INSTITUCIONAL (CYBER-TRADER) ---
st.set_page_config(page_title="QUANT-OS V30 // SINGULARITY", layout="wide", initial_sidebar_state="collapsed")

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
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .neon-blue { color: #00f3ff; text-shadow: 0 0 10px #00f3ff55; font-family: monospace; }
    .neon-green { color: #00ff9d; text-shadow: 0 0 10px #00ff9d55; font-family: monospace; }
    .neon-red { color: #ff3366; text-shadow: 0 0 10px #ff336655; font-family: monospace; }
    .label { font-size: 0.7rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
    .value { font-size: 1.5rem; font-weight: bold; }
    iframe { border-radius: 12px !important; border: 1px solid #30363d !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO CORE (MEXC FUTURES) ---
@st.cache_resource
def connect_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = connect_mexc()

# --- 3. MOTOR DE INTELIGÊNCIA ARTIFICIAL (OMNI-ANALYSIS) ---
def get_master_analysis(symbol):
    try:
        # Puxa 1m e 15m para confluência
        m1 = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        m15 = mexc.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        
        df1 = pd.DataFrame(m1, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        df15 = pd.DataFrame(m15, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # --- ESTRATÉGIA A: EMA RIBBON (9, 21, 50) ---
        df1['ema9'] = df1['close'].ewm(span=9).mean()
        df1['ema21'] = df1['close'].ewm(span=21).mean()
        df1['ema50'] = df1['close'].ewm(span=50).mean()
        
        # --- ESTRATÉGIA B: BOLLINGER BANDS (20, 2) ---
        df1['sma20'] = df1['close'].rolling(20).mean()
        df1['std20'] = df1['close'].rolling(20).std()
        df1['upper_bb'] = df1['sma20'] + (df1['std20'] * 2)
        df1['lower_bb'] = df1['sma20'] - (df1['std20'] * 2)
        
        # --- ESTRATÉGIA C: RSI RÁPIDO (7) ---
        delta = df1['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        df1['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        # --- ESTRATÉGIA D: TENDÊNCIA MACRO (M15) ---
        df15['ema_trend'] = df15['close'].ewm(span=20).mean()

        last1 = df1.iloc[-1]
        prev1 = df1.iloc[-2]
        last15 = df15.iloc[-1]
        
        # --- SISTEMA DE PONTUAÇÃO DE CONFLUÊNCIA ---
        score = 0
        
        # Pontos Compra
        if last1['ema9'] > last1['ema21']: score += 1 # Cruzamento positivo
        if last1['close'] > last15['ema_trend']: score += 1 # Confluência macro
        if last1['close'] < last1['lower_bb']: score += 2 # Reversão de fundo (Scalp)
        if last1['rsi'] < 35: score += 1 # Sobrevenda
        
        # Pontos Venda
        if last1['ema9'] < last1['ema21']: score -= 1
        if last1['close'] < last15['ema_trend']: score -= 1
        if last1['close'] > last1['upper_bb']: score -= 2 # Reversão de topo (Scalp)
        if last1['rsi'] > 65: score -= 1

        # Decisão
        if score >= 3: return "FORTE COMPRA (SCALP)", "neon-green", "buy", last1['close'], score
        if score <= -3: return "FORTE VENDA (SCALP)", "neon-red", "sell", last1['close'], score
        
        return "AGUARDANDO CONFLUÊNCIA", "label", None, last1['close'], score
    except:
        return "SINCRONIZANDO...", "label", None, 0.0, 0

# --- 4. EXECUÇÃO E CONTROLE ---
def run_order(side, pair, lev, margin):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        mexc.set_leverage(lev, sym)
        ticker = mexc.fetch_ticker(sym)
        qty = (margin * lev) / ticker['last']
        mexc.create_market_order(sym, side, qty)
        return f"✅ {side.upper()} EXECUTADO: {qty:.4f} @ {ticker['last']}"
    except Exception as e:
        return f"❌ ERRO: {str(e)}"

def panic_close_all(pair):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        positions = mexc.fetch_positions([sym])
        for p in positions:
            if float(p['contracts']) > 0:
                side = 'sell' if p['side'] == 'long' else 'buy'
                mexc.create_market_order(sym, side, p['contracts'])
        return "🚨 TODAS AS POSIÇÕES ENCERRADAS!"
    except Exception as e:
        return f"ERRO AO FECHAR: {e}"

# --- 5. INTERFACE DO UTILIZADOR ---
with st.sidebar:
    st.markdown("### ⚙️ MASTER CONTROL")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT", "DOGE/USDT"])
    leverage = st.slider("ALAVANCAGEM (X)", 1, 100, 20)
    margin_usd = st.number_input("MARGEM POR TRADE ($)", value=25)
    st.divider()
    auto_pilot = st.toggle("🚀 ACTIVAR IA EXECUTORA", value=False)
    st.divider()
    if st.button("🔴 PANIC BUTTON: CLOSE ALL", use_container_width=True):
        st.error(panic_close_all(asset))

st.title("SINGULARITY // V30 QUANT-TERMINAL")

# TradingView - Otimizado para Scalping (1 Minuto)
st.components.v1.html(f"""
    <div id="tv-chart" style="height:400px;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{
        "autosize": true, "symbol": "MEXC:{asset.replace('/','')}.P",
        "interval": "1", "timezone": "Etc/UTC", "theme": "dark", "style": "1",
        "locale": "pt", "enable_publishing": false, "hide_top_toolbar": false, "container_id": "tv-chart"
    }});
    </script>
""", height=400)

# --- 6. CORE MONITOR (REAL-TIME FRAGMENT) ---
@st.fragment(run_every=2)
def singularity_engine():
    sym_f = f"{asset.split('/')[0]}/USDT:USDT"
    
    # 1. Dados de Carteira
    bal = mexc.fetch_balance({'type': 'swap'})
    equity = bal['USDT']['total']
    available = bal['USDT']['free']
    
    # 2. Análise Omni
    signal, signal_class, action, price, score = get_master_analysis(sym_f)
    
    # 3. Dashboard Visual
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    with row1_c1:
        st.markdown(f"<div class='glass-card'><div class='label'>EQUITY TOTAL</div><div class='value neon-blue'>$ {equity:,.2f}</div></div>", unsafe_allow_html=True)
    with row1_c2:
        st.markdown(f"<div class='glass-card'><div class='label'>PREÇO ATUAL</div><div class='value'>$ {price:,.2f}</div></div>", unsafe_allow_html=True)
    with row1_c3:
        st.markdown(f"<div class='glass-card'><div class='label'>SCORE CONFLUÊNCIA</div><div class='value' style='color:#f0b90b'>{score} PTS</div></div>", unsafe_allow_html=True)

    st.markdown(f"<div class='glass-card' style='margin-top:10px;'><div class='label'>DECISÃO IA</div><div class='value {signal_class}' style='font-size:2rem;'>{signal}</div></div>", unsafe_allow_html=True)

    # 4. Lógica de Disparo
    if auto_pilot and action:
        # Cooldown de 45 segundos para scalping de alta frequência
        if 'last_op' not in st.session_state or (time.time() - st.session_state.last_op > 45):
            if available >= margin_usd:
                res = run_order(action, asset, leverage, margin_usd)
                st.session_state.last_op = time.time()
                st.session_state.master_log = res
                st.toast(res, icon="⚡")
            else:
                st.toast("SALDO INSUFICIENTE", icon="❌")

# Inicialização de logs
if 'master_log' not in st.session_state: st.session_state.master_log = "INICIALIZANDO SISTEMA OMNI..."

singularity_engine()

st.divider()
st.subheader("📟 TERMINAL LOG")
st.code(f"> {st.session_state.master_log}")
