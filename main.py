import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE INTERFACE ULTRA-PREMIUM ---
st.set_page_config(
    page_title="QUANT-OS V27 // THE VAULT", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Estilização CSS: Glassmorphism, Neon e Deep Space
st.markdown("""
    <style>
    .stApp { background: #050505; color: #e0e0e0; }
    header {visibility: hidden;}
    
    .glass-card {
        background: rgba(20, 20, 25, 0.8);
        border: 1px solid rgba(0, 243, 255, 0.2);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        margin-bottom: 10px;
    }
    
    .label { font-size: 0.7rem; letter-spacing: 2px; color: #666; text-transform: uppercase; margin-bottom: 8px; }
    .value { font-size: 1.6rem; font-family: 'Courier New', monospace; font-weight: bold; color: #fff; }
    
    .neon-green { color: #00ff9d; text-shadow: 0 0 10px rgba(0, 255, 157, 0.4); }
    .neon-red { color: #ff3366; text-shadow: 0 0 10px rgba(255, 51, 102, 0.4); }
    .neon-blue { color: #00f3ff; text-shadow: 0 0 10px rgba(0, 243, 255, 0.4); }
    
    iframe { border-radius: 15px !important; border: 1px solid #1a1a1a !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM A EXCHANGE (MEXC FUTURES) ---
@st.cache_resource
def connect_exchange():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True,
        'adjustForTimeDifference': True
    })

mexc = connect_exchange()

# --- 3. MOTOR DE INTELIGÊNCIA (ANÁLISE M1 + M15) ---
def get_institutional_signal(symbol):
    try:
        # Busca dados de 1 minuto e 15 minutos
        m1_data = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=60)
        m15_data = mexc.fetch_ohlcv(symbol, timeframe='15m', limit=60)
        
        df1 = pd.DataFrame(m1_data, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        df15 = pd.DataFrame(m15_data, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # Indicadores Nativos (Sem bibliotecas extras)
        df1['ema_fast'] = df1['close'].ewm(span=9).mean()
        df1['ema_slow'] = df1['close'].ewm(span=21).mean()
        df15['ema_trend'] = df15['close'].ewm(span=20).mean()
        
        # RSI Manual
        delta = df1['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df1['rsi'] = 100 - (100 / (1 + (gain / loss)))

        last1 = df1.iloc[-1]
        last15 = df15.iloc[-1]
        
        # LÓGICA DE CONFLUÊNCIA ELITE
        # Compra: M1 cruza acima + Preço acima da tendência M15 + RSI saudável
        if last1['ema_fast'] > last1['ema_slow'] and last1['close'] > last15['ema_trend'] and last1['rsi'] < 65:
            return "BUY CONFIRMED", "neon-green", "buy", last1['close'], last1['rsi']
        
        # Venda: M1 cruza abaixo + Preço abaixo da tendência M15 + RSI saudável
        elif last1['ema_fast'] < last1['ema_slow'] and last1['close'] < last15['ema_trend'] and last1['rsi'] > 35:
            return "SELL CONFIRMED", "neon-red", "sell", last1['close'], last1['rsi']
            
        return "WAITING FLOW", "label", None, last1['close'], last1['rsi']
    except Exception as e:
        return f"SYNCING...", "label", None, 0.0, 50.0

# --- 4. GESTÃO DE CARTEIRA ---
def get_account_stats():
    try:
        bal = mexc.fetch_balance({'type': 'swap'})
        return bal['USDT']['total'], bal['USDT']['free']
    except:
        return 0.0, 0.0

# --- 5. EXECUÇÃO PROTEGIDA ---
def execute_institutional_order(side, pair, lev, margin):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        mexc.set_leverage(lev, sym)
        ticker = mexc.fetch_ticker(sym)
        price = ticker['last']
        qty = (margin * lev) / price
        
        # Envia Ordem a Mercado
        mexc.create_market_order(sym, side, qty)
        return f"EXECUTED: {side.upper()} {qty:.4f} {pair} @ {price}"
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- 6. UI: PAINEL DE CONTROLE ---
with st.sidebar:
    st.markdown("### 🛡️ RISK CONTROL")
    asset = st.selectbox("ASSET", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    leverage = st.slider("LEVERAGE", 1, 100, 20)
    margin_per_trade = st.number_input("MARGIN ($)", value=50)
    st.divider()
    is_active = st.toggle("🚀 ARM SYSTEM (REAL MONEY)", value=False)
    st.caption("Ao ativar, a IA executará ordens reais baseadas na confluência M1/M15.")

st.title("QUANT-OS V27 // THE VAULT")

# Gráfico TradingView (Estático)
st.components.v1.html(f"""
    <div id="tv-chart" style="height:420px; border-radius:15px; overflow:hidden;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{
        "autosize": true, "symbol": "MEXC:{asset.replace('/','')}.P",
        "interval": "1", "theme": "dark", "style": "1", "container_id": "tv-chart"
    }});
    </script>
""", height=420)

# --- 7. CORE ENGINE (FRAGMENTO) ---
@st.fragment(run_every=2)
def institutional_engine(selected_asset):
    sym_f = f"{selected_asset.split('/')[0]}/USDT:USDT"
    
    # Busca Dados
    total_eq, free_eq = get_account_stats()
    signal_msg, signal_class, action, price, rsi_val = get_institutional_signal(sym_f)
    
    # Layout de Métricas
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    with row1_c1:
        st.markdown(f"<div class='glass-card'><div class='label'>EQUITY TOTAL</div><div class='value neon-blue'>$ {total_eq:,.2f}</div></div>", unsafe_allow_html=True)
    with row1_c2:
        st.markdown(f"<div class='glass-card'><div class='label'>DISPONÍVEL</div><div class='value'>$ {free_eq:,.2f}</div></div>", unsafe_allow_html=True)
    with row1_c3:
        st.markdown(f"<div class='glass-card'><div class='label'>MARKET PRICE</div><div class='value'>$ {price:,.2f}</div></div>", unsafe_allow_html=True)
        
    row2_c1, row2_c2, row2_c3 = st.columns(3)
    with row2_c1:
        st.markdown(f"<div class='glass-card'><div class='label'>IA SIGNAL (M1+M15)</div><div class='value {signal_class}'>{signal_msg}</div></div>", unsafe_allow_html=True)
    with row2_c2:
        st.markdown(f"<div class='glass-card'><div class='label'>RSI (14)</div><div class='value'>{rsi_val:.1f}</div></div>", unsafe_allow_html=True)
    with row2_c3:
        st.markdown(f"<div class='glass-card'><div class='label'>SYSTEM STATUS</div><div class='value' style='color:#f0b90b;'>{'ACTIVE' if is_active else 'STANDBY'}</div></div>", unsafe_allow_html=True)

    # Lógica de Disparo Real
    if is_active and action:
        # Cooldown de 2 minutos para evitar ordens duplicadas no mesmo sinal
        if 'last_trade_time' not in st.session_state or (time.time() - st.session_state.last_trade_time > 120):
            if free_eq >= margin_per_trade:
                res = execute_institutional_order(action, selected_asset, leverage, margin_per_trade)
                st.session_state.last_trade_time = time.time()
                st.session_state.terminal_output = res
                st.toast(res, icon="⚡")
            else:
                st.toast("SALDO INSUFICIENTE", icon="❌")

# Inicialização de Log
if 'terminal_output' not in st.session_state: st.session_state.terminal_output = "SYSTEM INITIALIZED. WAITING FOR CONFLUENCE..."

institutional_engine(asset)

st.divider()
st.subheader("📝 INSTITUTIONAL LOG")
st.code(f"> {st.session_state.terminal_output}")
