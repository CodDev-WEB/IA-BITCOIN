import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta  # Biblioteca para análise técnica avançada
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA-QUANT TERMINAL PRO", layout="wide", initial_sidebar_state="collapsed")

# Estilo CSS para Terminal Profissional
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; background-color: #0b0e11; }
    .metric-card { 
        background-color: #181a20; padding: 20px; border-radius: 10px; 
        border: 1px solid #2b2f36; text-align: center;
    }
    .value { font-size: 1.8rem; font-weight: bold; font-family: 'Courier New', monospace; color: #00ffcc; }
    .label { color: #848e9c; font-size: 0.8rem; letter-spacing: 1px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO 1: CONEXÃO COM A EXCHANGE ---
@st.cache_resource
def conectar_mexc():
    """Estabelece conexão com o mercado de Futuros da MEXC."""
    return ccxt.mexc({
        'apiKey': st.secrets["API_KEY"],
        'secret': st.secrets["SECRET_KEY"],
        'options': {'defaultType': 'swap'}, # Define mercado de Futuros Perpétuos
        'enableRateLimit': True
    })

mexc = conectar_mexc()

# --- FUNÇÃO 2: MOTOR DE INTELIGÊNCIA (IA QUANT) ---
def processar_ia_quant(symbol):
    """Analisa tendências usando Médias Móveis e RSI."""
    try:
        # Busca velas de 1 minuto
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        # Cálculo de Indicadores Técnicos
        df['EMA_FAST'] = ta.ema(df['close'], length=9)
        df['EMA_SLOW'] = ta.ema(df['close'], length=21)
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Lógica de Decisão (Crossover + RSI)
        # Compra: EMA Rápida cruza acima da Lenta + RSI abaixo de 40 (sobrevendido)
        if last_row['EMA_FAST'] > last_row['EMA_SLOW'] and prev_row['EMA_FAST'] <= prev_row['EMA_SLOW'] and last_row['RSI'] < 50:
            return "COMPRA (LONG)", "#00ffcc", "buy"
        
        # Venda: EMA Rápida cruza abaixo da Lenta + RSI acima de 60 (sobrecomprado)
        elif last_row['EMA_FAST'] < last_row['EMA_SLOW'] and prev_row['EMA_FAST'] >= prev_row['EMA_SLOW'] and last_row['RSI'] > 50:
            return "VENDA (SHORT)", "#ff4d4d", "sell"
        
        return "AGUARDANDO SINAL", "#848e9c", None
    except Exception as e:
        return f"ERRO IA: {str(e)}", "#848e9c", None

# --- FUNÇÃO 3: EXECUTOR DE ORDENS ---
def executar_trade_real(acao, par, alavancagem, volume_usd):
    """Envia ordens a mercado para a corretora."""
    try:
        symbol_futures = f"{par.split('/')[0]}/USDT:USDT"
        
        # 1. Ajusta alavancagem
        mexc.set_leverage(alavancagem, symbol_futures)
        
        # 2. Busca preço atual para calcular quantidade
        ticker = mexc.fetch_ticker(symbol_futures)
        price = ticker['last']
        
        # 3. Calcula quantidade (Margem * Alavancagem / Preço)
        qty = (volume_usd * alavancagem) / price
        
        if acao == 'buy':
            order = mexc.create_market_buy_order(symbol_futures, qty)
        else:
            order = mexc.create_market_sell_order(symbol_futures, qty)
            
        return f"✅ SUCESSO: {acao.upper()} {qty:.4f} @ {price}"
    except Exception as e:
        return f"❌ FALHA: {str(e)}"

# --- INTERFACE DO USUÁRIO (FRONTEND) ---
with st.sidebar:
    st.header("🎮 CONTROLE DO ROBÔ")
    par_ativo = st.selectbox("PAR DE FUTUROS", ["BTC/USDT", "ETH/USDT"])
    alavancagem_sel = st.slider("ALAVANCAGEM", 1, 50, 10)
    capital_por_trade = st.number_input("MARGEM POR TRADE (USD)", value=20)
    st.divider()
    modo_real = st.toggle("ATIVAR EXECUÇÃO REAL", value=False)
    st.info("O robô usa cruzamento de EMA 9/21 + RSI para entradas.")

st.title("⚡ GEN-QUANT AI PRO TERMINAL")

# Widget TradingView Estático
st.components.v1.html(f"""
    <div id="tv-chart" style="height:400px;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{par_ativo.replace('/','')}.P","interval":"1","theme":"dark","container_id":"tv-chart"}});</script>
""", height=400)

# --- FRAGMENTO DE ALTA FREQUÊNCIA (DASHBOARD DINÂMICO) ---
@st.fragment(run_every=3)
def atualizar_dashboard(par):
    symbol_formatted = f"{par.split('/')[0]}/USDT:USDT"
    sinal_txt, cor_sinal, acao_trade = processar_ia_quant(symbol_formatted)
    
    # Busca preço em tempo real
    ticker = mexc.fetch_ticker(symbol_formatted)
    
    # Linha de métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-card'><div class='label'>PREÇO ATUAL</div><div class='value'>$ {ticker['last']:,.2f}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><div class='label'>IA SIGNAL</div><div class='value' style='color:{cor_sinal}'>{sinal_txt}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><div class='label'>MODO</div><div class='value' style='color:#f0b90b'>{'AUTOMÁTICO' if modo_real else 'SIMULAÇÃO'}</div></div>", unsafe_allow_html=True)

    # Lógica de Execução
    if modo_real and acao_trade:
        if 'last_trade_time' not in st.session_state or (time.time() - st.session_state.last_trade_time > 60):
            res_log = executar_trade_real(acao_trade, par, alavancagem_sel, capital_por_trade)
            st.session_state.log_historico = res_log
            st.session_state.last_trade_time = time.time()
            st.toast(res_log)

# Inicia Monitoramento
if 'log_historico' not in st.session_state: st.session_state.log_historico = "Aguardando sinal..."
atualizar_dashboard(par_ativo)

st.divider()
st.subheader("📝 REGISTRO DE OPERAÇÕES")
st.code(st.session_state.log_historico)
