import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="IA-QUANT TERMINAL PRO", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; background-color: #0b0e11; }
    .metric-card { 
        background-color: #181a20; padding: 20px; border-radius: 10px; 
        border: 1px solid #2b2f36; text-align: center;
    }
    .value { font-size: 1.8rem; font-weight: bold; font-family: 'Courier New', monospace; color: #00ffcc; }
    .label { color: #848e9c; font-size: 0.85rem; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO COM API MEXC (FUTUROS) ---
@st.cache_resource
def get_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True,
        'adjustForTimeDifference': True
    })

mexc = get_mexc()

# --- 3. MOTOR DE INTELIGÊNCIA TÉCNICA ---
def calcular_sinal_ia(symbol):
    try:
        # Busca histórico para análise
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=60)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        # EMA (Tendência)
        df['ema_fast'] = df['close'].ewm(span=9).mean()
        df['ema_slow'] = df['close'].ewm(span=21).mean()
        
        # RSI (Força)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        ultimo = df.iloc[-1]
        
        # Lógica de Decisão
        if ultimo['rsi'] < 32 and ultimo['ema_fast'] > ultimo['ema_slow']:
            return "COMPRA (LONG)", "#00ffcc", "buy"
        elif ultimo['rsi'] > 68 and ultimo['ema_fast'] < ultimo['ema_slow']:
            return "VENDA (SHORT)", "#ff4d4d", "sell"
        else:
            return "AGUARDANDO", "#848e9c", None
    except:
        return "SINCRONIZANDO", "#848e9c", None

# --- 4. FUNÇÃO DE EXECUÇÃO DE ORDENS ---
def executar_trade(lado, par, alavancagem, usd):
    try:
        symbol_f = f"{par.split('/')[0]}/USDT:USDT"
        mexc.set_leverage(alavancagem, symbol_f)
        ticker = mexc.fetch_ticker(symbol_f)
        qty = (usd * alavancagem) / ticker['last']
        
        if lado == 'buy':
            mexc.create_market_buy_order(symbol_f, qty)
        elif lado == 'sell':
            mexc.create_market_sell_order(symbol_f, qty)
            
        return f"✅ {lado.upper()} Executado: {qty:.4f} @ {ticker['last']}"
    except Exception as e:
        return f"❌ Erro na Ordem: {str(e)}"

# --- 5. INTERFACE DO USUÁRIO ---
with st.sidebar:
    st.header("⚙️ COCKPIT IA")
    par_sel = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT"])
    alavancagem = st.slider("ALAVANCAGEM", 1, 50, 10)
    banca_trade = st.number_input("VALOR USD", value=50)
    st.divider()
    bot_ready = st.toggle("🚀 EXECUTOR ATIVO", value=False)

st.title("⚡ GEN-QUANT AI PRO")

# Gráfico Estático (Carrega uma vez)
st.components.v1.html(f"""
    <div id="chart" style="height:420px;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{par_sel.replace('/','')}.P","interval":"1","theme":"dark","container_id":"chart"}});</script>
""", height=420)

# --- 6. FRAGMENTO DE ALTA FREQUÊNCIA ---
@st.fragment(run_every=2)
def monitor_ia(par):
    if 'log_txt' not in st.session_state: st.session_state.log_txt = "Analisando fluxo..."
    
    symbol_f = f"{par.split('/')[0]}/USDT:USDT"
    sinal, cor, acao = calcular_sinal_ia(symbol_f)
    
    ticker = mexc.fetch_ticker(symbol_f)
    
    # Layout de Métricas
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='metric-card'><p class='label'>PREÇO</p><div class='value'>$ {ticker['last']:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><p class='label'>SINAL IA</p><div class='value' style='color:{cor}'>{sinal}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><p class='label'>STATUS</p><div class='value' style='color:#f0b90b'>{'LIVE' if bot_ready else 'SCAN'}</div></div>", unsafe_allow_html=True)

    # Lógica de Execução Real
    if bot_ready and acao:
        res = executar_trade(acao, par, alavancagem, banca_trade)
        st.session_state.log_txt = res
        st.toast(res)

monitor_ia(par_sel)

st.divider()
st.subheader("📝 REGISTRO DE OPERAÇÕES")
st.code(st.session_state.log_txt)
