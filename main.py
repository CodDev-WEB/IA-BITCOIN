import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO "ELITE" (VISUAL CYBERPUNK) ---
st.set_page_config(page_title="QUANT-OS ELITE", layout="wide", initial_sidebar_state="collapsed")

# CSS Avançado: Fundo gradiente, Cartões de Vidro (Glassmorphism), Fontes Mono
st.markdown("""
    <style>
    /* Fundo Deep Space */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #0b0e11 0%, #000000 90%);
        color: #e0e0e0;
    }
    
    /* Remover barras padrão do Streamlit */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Cartões "Glassmorphism" (Efeito de Vidro) */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        text-align: center;
        transition: transform 0.2s;
    }
    .glass-card:hover {
        border: 1px solid rgba(0, 240, 255, 0.3);
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.1);
    }

    /* Tipografia Elite */
    .label {
        font-family: 'Segoe UI', sans-serif;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #8b949e;
        margin-bottom: 5px;
    }
    .value {
        font-family: 'Courier New', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #fff;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
    }
    .neon-green { color: #00ff9d; text-shadow: 0 0 10px rgba(0, 255, 157, 0.4); }
    .neon-red { color: #ff3366; text-shadow: 0 0 10px rgba(255, 51, 102, 0.4); }
    .neon-blue { color: #00f3ff; text-shadow: 0 0 10px rgba(0, 243, 255, 0.4); }
    
    /* Ajuste de Gráfico */
    iframe { border-radius: 12px !important; border: 1px solid #2d2d2d; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO BANCÁRIA (API) ---
@st.cache_resource
def connect_bank():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'}, # CRUCIAL: MODO FUTUROS
        'enableRateLimit': True
    })

mexc = connect_bank()

# --- 3. INTELIGÊNCIA MATEMÁTICA (NATIVA) ---
def get_market_intelligence(symbol):
    try:
        # Puxa dados brutos
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=60)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        # Matemática Financeira (Sem bibliotecas externas)
        df['ema_fast'] = df['close'].ewm(span=9).mean()
        df['ema_slow'] = df['close'].ewm(span=21).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Algoritmo de Decisão
        status = "NEUTRO"
        cor = "#8b949e"
        acao = None
        
        # Lógica Sniper: Cruzamento + Confirmação RSI
        if last['ema_fast'] > last['ema_slow'] and prev['ema_fast'] <= prev['ema_slow'] and last['rsi'] < 60:
            status = "COMPRA AGRESSIVA"
            cor = "neon-green"
            acao = "buy"
        elif last['ema_fast'] < last['ema_slow'] and prev['ema_fast'] >= prev['ema_slow'] and last['rsi'] > 40:
            status = "VENDA FORTE"
            cor = "neon-red"
            acao = "sell"
            
        return status, cor, acao, last['close'], last['rsi']
    except:
        return "SYNC...", "#fff", None, 0.0, 50.0

# --- 4. GESTÃO DE CARTEIRA (NOVA FUNÇÃO) ---
def get_wallet_status():
    try:
        # Pega saldo ESPECÍFICO de Futuros (Swap)
        balance = mexc.fetch_balance({'type': 'swap'})
        usdt_total = balance['USDT']['total']
        usdt_free = balance['USDT']['free']
        usdt_used = balance['USDT']['used']
        return usdt_total, usdt_free, usdt_used
    except Exception as e:
        return 0.0, 0.0, 0.0

# --- 5. EXECUÇÃO DE ALTA FREQUÊNCIA ---
def execute_order(side, pair, lev, amount_usd):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        mexc.set_leverage(lev, sym)
        ticker = mexc.fetch_ticker(sym)
        price = ticker['last']
        qty = (amount_usd * lev) / price # Qty em Moeda
        
        if side == 'buy':
            mexc.create_market_buy_order(sym, qty)
        else:
            mexc.create_market_sell_order(sym, qty)
        return f"ORDEM EXECUTADA: {side.upper()} | ${amount_usd} @ {price}"
    except Exception as e:
        return f"ERRO EXECUÇÃO: {e}"

# --- 6. INTERFACE ELITE (LAYOUT) ---

# Sidebar Minimalista
with st.sidebar:
    st.markdown("## ⚙️ SYSTEM CONTROL")
    active_pair = st.selectbox("ASSET", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    leverage = st.slider("LEVERAGE (x)", 1, 100, 20)
    risk_usd = st.number_input("MARGIN PER TRADE ($)", value=100)
    st.divider()
    system_arm = st.toggle("⚠️ ARM SYSTEM (REAL MONEY)", value=False)

st.title("QUANT-OS // ELITE TERMINAL")

# Container do Gráfico (Fixo)
st.components.v1.html(f"""
    <div id="tv_chart" style="height:480px; border-radius:12px; overflow:hidden;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{
        "autosize": true,
        "symbol": "MEXC:{active_pair.replace('/','')}.P",
        "interval": "1",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#000000",
        "enable_publishing": false,
        "hide_top_toolbar": false,
        "container_id": "tv_chart"
    }});
    </script>
""", height=480)

# --- 7. FRAGMENTO "CORE" (ATUALIZAÇÃO TOTAL) ---
@st.fragment(run_every=2)
def live_core(symbol):
    sym_fmt = f"{symbol.split('/')[0]}/USDT:USDT"
    
    # 1. Puxa Saldo em Tempo Real
    total, free, used = get_wallet_status()
    
    # 2. Puxa Inteligência de Mercado
    signal, color_class, action, price, rsi_val = get_market_intelligence(sym_fmt)
    
    # --- LINHA 1: CARTEIRA (WALLET) ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='label'>EQUITY TOTAL (USDT)</div>
            <div class='value neon-blue'>$ {total:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='label'>DISPONÍVEL</div>
            <div class='value'>$ {free:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='label'>EM ORDEM (MARGEM)</div>
            <div class='value' style='color:#ffcc00;'>$ {used:,.2f}</div>
        </div>""", unsafe_allow_html=True)

    # --- LINHA 2: MERCADO (MARKET DATA) ---
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='label'>PREÇO ATUAL</div>
            <div class='value'>$ {price:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='label'>INTELIGÊNCIA ARTIFICIAL</div>
            <div class='value {color_class}'>{signal}</div>
        </div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='label'>RSI INDEX</div>
            <div class='value'>{rsi_val:.1f}</div>
        </div>""", unsafe_allow_html=True)

    # --- LÓGICA DE TIRO (EXECUÇÃO) ---
    if system_arm and action:
        # Check simples para não floodar ordens (1 min cooldown)
        if 'last_shot' not in st.session_state or (time.time() - st.session_state.last_shot > 60):
            # Validação de Saldo
            if free >= risk_usd:
                log = execute_order(action, symbol, leverage, risk_usd)
                st.toast(log, icon="⚡")
                st.session_state.terminal_log = f"[{datetime.now().strftime('%H:%M:%S')}] {log}"
                st.session_state.last_shot = time.time()
            else:
                st.toast("SALDO INSUFICIENTE PARA OPERAR", icon="❌")

# Inicialização de Estado
if 'terminal_log' not in st.session_state: st.session_state.terminal_log = "SYSTEM READY..."

# Inicia o Core
live_core(active_pair)

# Rodapé: Terminal Log
st.markdown("---")
st.markdown(f"<div style='color:#444; font-family:monospace;'>TERMINAL_LOG: > {st.session_state.terminal_log}</div>", unsafe_allow_html=True)
