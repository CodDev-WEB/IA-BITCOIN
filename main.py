import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="QUANT-OS V34 // FULL", layout="wide", initial_sidebar_state="collapsed")

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
    .neon-green { color: #00ff9d; }
    .neon-red { color: #ff3366; }
    .value { font-size: 1.6rem; font-weight: bold; font-family: monospace; }
    .label { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM A EXCHANGE ---
@st.cache_resource
def connect_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = connect_mexc()

# --- 3. MOTOR DE ANÁLISE IA (TODAS AS ESTRATÉGIAS) ---
def get_ia_signals(symbol):
    try:
        # Puxa 100 velas para ter histórico suficiente para as médias e Bollinger
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # Médias para tendência curta
        df['ema5'] = df['close'].ewm(span=5).mean()
        df['ema13'] = df['close'].ewm(span=13).mean()
        
        # Bollinger para reversão (Lucro de Pombo)
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['up'] = df['sma20'] + (df['std20'] * 2)
        df['lw'] = df['sma20'] - (df['std20'] * 2)
        
        # RSI 7 para momentum rápido
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))

        last = df.iloc[-1]
        score = 0
        
        # Lógica de Pontuação (Confluência)
        if last['ema5'] > last['ema13']: score += 1
        if last['close'] < last['lw']: score += 2
        if last['rsi'] < 40: score += 1
        
        if last['ema5'] < last['ema13']: score -= 1
        if last['close'] > last['up']: score -= 2
        if last['rsi'] > 60: score -= 1
        
        if score >= 2: return "COMPRA (LONG)", "neon-green", "buy", last['close'], score
        if score <= -2: return "VENDA (SHORT)", "neon-red", "sell", last['close'], score
        return "AGUARDANDO", "white", None, last['close'], score
    except Exception as e:
        return f"ERRO: {str(e)}", "white", None, 0, 0

# --- 4. EXECUÇÃO COM CORREÇÃO DEFINITIVA DE LEVERAGE ---
def execute_trade_full(side, pair, lev, margin, margin_type):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if margin_type == "Isolada" else 2
        
        # A MEXC exige configurar a alavancagem antes de cada tipo de operação
        # PositionType 1 = Long, 2 = Short. Configuramos ambos para garantir.
        try:
            mexc.set_leverage(lev, sym, {'openType': m_code, 'positionType': 1})
            mexc.set_leverage(lev, sym, {'openType': m_code, 'positionType': 2})
        except:
            pass # Ignora se a exchange já estiver configurada

        ticker = mexc.fetch_ticker(sym)
        price = ticker['last']
        qty = (margin * lev) / price
        
        # Ordem a mercado
        mexc.create_market_order(sym, side, qty)
        return f"🚀 {side.upper()} ABERTO | {qty:.4f} {pair} @ {price}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

def close_all_positions(pair):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        positions = mexc.fetch_positions([sym])
        count = 0
        for p in positions:
            if float(p['contracts']) > 0:
                side = 'sell' if p['side'] == 'long' else 'buy'
                mexc.create_market_order(sym, side, p['contracts'])
                count += 1
        return f"✅ {count} POSIÇÃO(ÕES) ENCERRADA(S)"
    except Exception as e:
        return f"❌ ERRO AO FECHAR: {str(e)}"

# --- 5. INTERFACE DO USUÁRIO ---
with st.sidebar:
    st.header("🕹️ COMANDO V34")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 100, 20)
    margin_usd = st.number_input("MARGEM ($)", value=20)
    margin_choice = st.radio("MODO DE MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_enabled = st.toggle("LIGAR IA EXECUTORA")
    if st.button("🔴 FECHAR TUDO AGORA", use_container_width=True):
        st.toast(close_all_positions(asset))

st.title("QUANT-OS V34 // FULL INTEGRITY")

# --- 6. MOTOR DE PROCESSAMENTO (FRAGMENTADO PARA VELOCIDADE) ---
@st.fragment(run_every=2)
def singularity_core():
    sym_f = f"{asset.split('/')[0]}/USDT:USDT"
    
    # Busca dados de conta
    try:
        bal = mexc.fetch_balance({'type': 'swap'})
        wallet = bal['USDT']['total']
        available = bal['USDT']['free']
    except:
        wallet, available = 0.0, 0.0
    
    # Busca Sinais da IA
    label, color, action, price, score = get_ia_signals(sym_f)
    
    # Dashboard Visual
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='glass-card'><div class='label'>EQUITY</div><div class='value'>$ {wallet:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='glass-card'><div class='label'>PREÇO {asset}</div><div class='value'>$ {price:,.2f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='glass-card'><div class='label'>SINAL IA</div><div class='value {color}'>{label}</div></div>", unsafe_allow_html=True)

    # Lógica de Controle de Posição
    if bot_enabled:
        # Verifica se existe posição aberta
        try:
            pos = mexc.fetch_positions([sym_f])
            in_trade = any(float(p['contracts']) > 0 for p in pos)
            
            # 1. ENTRADA: Se não estiver em trade e a IA der sinal forte
            if not in_trade and action:
                res = execute_trade_full(action, asset, leverage, margin_usd, margin_choice)
                st.session_state.log_v34 = res
                st.toast(res)
            
            # 2. SAÍDA (LUCRO DE POMBO): Se estiver em trade e o sinal enfraquecer
            elif in_trade:
                # Se o score voltar para neutro ou inverter, fecha para garantir lucro
                if (action is None) or (score == 0):
                    res = close_all_positions(asset)
                    st.session_state.log_v34 = f"SAÍDA IA: {res}"
                    st.toast("LUCRO REALIZADO")
        except:
            pass

# Inicializa Log
if 'log_v34' not in st.session_state: st.session_state.log_v34 = "SISTEMA ONLINE - AGUARDANDO IA"

singularity_core()

st.divider()
st.code(f"> TERMINAL LOG: {st.session_state.log_v34}")
