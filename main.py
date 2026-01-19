import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE LAYOUT ---
st.set_page_config(page_title="IA-QUANT PRO V20", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; background-color: #0b0e11; }
    .metric-card { 
        background-color: #181a20; padding: 20px; border-radius: 10px; 
        border: 1px solid #2b2f36; text-align: center;
    }
    .value { font-size: 1.8rem; font-weight: bold; font-family: 'Courier New', monospace; color: #00ffcc; }
    .label { color: #848e9c; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO COM A API ---
@st.cache_resource
def get_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = get_mexc()

# --- 3. MOTOR DE INTELIGÊNCIA (ANÁLISE TÉCNICA) ---
def analisar_ia(df):
    """
    Simula o pensamento de uma IA Quantitativa usando indicadores técnicos.
    """
    # Médias Móveis (Tendência)
    df['ema_fast'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # RSI (Índice de Força Relativa - Exaustão)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    ultimo_preço = df['close'].iloc[-1]
    rsi_atual = df['rsi'].iloc[-1]
    ema_f = df['ema_fast'].iloc[-1]
    ema_s = df['ema_slow'].iloc[-1]
    
    # LÓGICA DE DECISÃO IA
    if rsi_atual < 30 and ema_f > ema_s:
        return "COMPRA (LONG)", "#00ffcc"  # Sobrevendido + Cruzamento de alta
    elif rsi_atual > 70 and ema_f < ema_s:
        return "VENDA (SHORT)", "#ff4d4d"  # Sobrecomprado + Cruzamento de baixa
    else:
        return "AGUARDANDO SINAL", "#848e9c"

# --- 4. FUNÇÃO DE EXECUÇÃO ---
def executar_ordem(lado, par, alavancagem, usd):
    try:
        symbol = f"{par.split('/')[0]}/USDT:USDT"
        mexc.set_leverage(alavancagem, symbol)
        ticker = mexc.fetch_ticker(symbol)
        qty = (usd * alavancagem) / ticker['last']
        
        if lado == 'buy':
            mexc.create_market_buy_order(symbol, qty)
        else:
            mexc.create_market_sell_order(symbol, qty)
            
        return f"✅ {lado.upper()} executado: {qty:.4f} {symbol}"
    except Exception as e:
        return f"❌ Erro: {str(e)}"

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("⚙️ CONFIGURAÇÃO")
    par_selecionado = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT"])
    alavancagem = st.slider("ALAVANCAGEM", 1, 50, 10)
    valor_trade = st.number_input("USD POR TRADE", value=50)
    bot_ligado = st.toggle("🚨 EXECUTOR ATIVO", value=False)

st.title("⚡ GEN-QUANT AI EXECUTOR V20")

# Gráfico TradingView
st.components.v1.html(f"""
    <div id="tv-chart" style="height:400px;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{par_selecionado.replace('/','')}.P","interval":"1","theme":"dark","container_id":"tv-chart"}});</script>
""", height=400)

# --- 6. FRAGMENTO DE EXECUÇÃO ---
@st.fragment(run_every=3)
def motor_ia(par):
    symbol_f = f"{par.split('/')[0]}/USDT:USDT"
    if 'logs' not in st.session_state: st.session_state.logs = "Iniciando análise..."

    try:
        # Busca velas de 1 minuto para a IA analisar
        ohlcv = mexc.fetch_ohlcv(symbol_f, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        sinal, cor = analisar_ia(df)
        preco = df['close'].iloc[-1]
        rsi_val = df['rsi'].iloc[-1]

        # Painel Visual
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-card'><p class='label'>PREÇO</p><div class='value'>$ {preco:,.2f}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card'><p class='label'>SINAL IA (RSI+EMA)</p><div class='value' style='color:{cor}'>{sinal}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><p class='label'>RSI (14)</p><div class='value' style='color:#f0b90b'>{rsi_val:.2f}</div></div>", unsafe_allow_html=True)

        # Execução Automática
        if bot_ligado:
            if "COMPRA" in sinal:
                st.session_state.logs = executar_ordem('buy', par, alavancagem, valor_trade)
            elif "VENDA" in sinal:
                st.session_state.logs = executar_ordem('sell', par, alavancagem, valor_trade)

    except Exception as e:
        st.caption("Aguardando dados...")

motor_ia(par_selecionado)

st.divider()
st.code(st.session_state.logs)
