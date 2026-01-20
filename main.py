import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# --- 1. INTERFACE ELITE V32 ---
st.set_page_config(page_title="QUANT-OS V32 // COMMANDER", layout="wide", initial_sidebar_state="collapsed")

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
    .neon-green { color: #00ff9d; text-shadow: 0 0 10px #00ff9d55; }
    .neon-red { color: #ff3366; text-shadow: 0 0 10px #ff336655; }
    .neon-blue { color: #00f3ff; text-shadow: 0 0 10px #00f3ff55; }
    .value { font-size: 1.6rem; font-weight: bold; font-family: 'Courier New', monospace; }
    .label { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO BANCÁRIA ---
@st.cache_resource
def connect_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = connect_mexc()

# --- 3. MOTOR DE INTELIGÊNCIA OMNI ---
def get_ia_analysis(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # Indicadores de Scalping
        df['ema5'] = df['close'].ewm(span=5).mean()
        df['ema13'] = df['close'].ewm(span=13).mean()
        
        # Bollinger para Alvos
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['upper'] = df['sma20'] + (df['std20'] * 2)
        df['lower'] = df['sma20'] - (df['std20'] * 2)
        
        # RSI 7 (Rápido)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))

        last = df.iloc[-1]
        
        score = 0
        # Regras de Entrada
        if last['ema5'] > last['ema13']: score += 1
        if last['close'] < last['lower']: score += 2
        if last['rsi'] < 40: score += 1
        
        if last['ema5'] < last['ema13']: score -= 1
        if last['close'] > last['upper']: score -= 2
        if last['rsi'] > 60: score -= 1
        
        if score >= 2: return "LONG", "neon-green", "buy", last['close'], score
        if score <= -2: return "SHORT", "neon-red", "sell", last['close'], score
        
        return "NEUTRO", "value", None, last['close'], score
    except:
        return "SYNCING...", "value", None, 0.0, 0

# --- 4. FUNÇÕES DE EXECUÇÃO ---
def execute_trade(side, pair, lev, margin, margin_type):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        # 1 = ISOLADA, 2 = CRUZADA
        m_code = 1 if margin_type == "Isolada" else 2
        
        mexc.set_leverage(lev, sym, {'openType': m_code})
        
        ticker = mexc.fetch_ticker(sym)
        qty = (margin * lev) / ticker['last']
        
        order = mexc.create_market_order(sym, side, qty)
        return f"🔥 {side.upper()} ABERTO | {qty:.4f} {pair}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

def close_all(pair):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        positions = mexc.fetch_positions([sym])
        for p in positions:
            if float(p['contracts']) > 0:
                side = 'sell' if p['side'] == 'long' else 'buy'
                mexc.create_market_order(sym, side, p['contracts'])
        return "✅ TODAS AS POSIÇÕES ENCERRADAS"
    except Exception as e:
        return f"ERRO AO FECHAR: {e}"

# --- 5. SIDEBAR: SEU PAINEL DE COMANDO ---
with st.sidebar:
    st.markdown("## 🕹️ COMMAND CENTER")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 100, 20)
    margin_usd = st.number_input("MARGEM ($)", value=20)
    
    # SUA SOLICITAÇÃO: ESCOLHA DE MARGEM
    m_type = st.radio("TIPO DE MARGEM", ["Isolada", "Cruzada"], help="Isolada protege seu saldo total. Cruzada usa tudo para evitar liquidação.")
    
    st.divider()
    bot_active = st.toggle("🚀 ATIVAR IA EXECUTORA")
    if st.button("🔴 FECHAR TUDO AGORA", use_container_width=True):
        st.warning(close_all(asset))

st.title("QUANT-OS V32 // MASTER COMMANDER")

# Gráfico
st.components.v1.html(f"""
    <div id="tv-chart" style="height:400px;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{"autosize":true, "symbol":"MEXC:{asset.replace('/','')}.P", "interval":"1", "theme":"dark", "style":"1", "container_id":"tv-chart"}});
    </script>
""", height=400)

# --- 6. CORE ENGINE (IA EM TEMPO REAL) ---
@st.fragment(run_every=2)
def live_engine():
    sym_f = f"{asset.split('/')[0]}/USDT:USDT"
    
    # 1. Saldo Real
    bal = mexc.fetch_balance({'type': 'swap'})
    total_eq = bal['USDT']['total']
    
    # 2. Análise da IA
    label, color, side, price, score = get_ia_analysis(sym_f)
    
    # 3. UI Dashboard
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='glass-card'><div class='label'>EQUITY</div><div class='value neon-blue'>$ {total_eq:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='glass-card'><div class='label'>SCORE IA</div><div class='value'>{score} PTS</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='glass-card'><div class='label'>MODO</div><div class='value' style='color:#f0b90b'>{m_type}</div></div>", unsafe_allow_html=True)
    
    st.markdown(f"<div class='glass-card'><div class='label'>SINAL ATUAL</div><div class='value {color}' style='font-size:2.5rem;'>{label}</div></div>", unsafe_allow_html=True)

    # 4. LÓGICA DE EXECUÇÃO IA (ABRIR E FECHAR)
    if bot_active:
        # Pega posições abertas
        pos = mexc.fetch_positions([sym_f])
        in_trade = False
        current_side = None
        for p in pos:
            if float(p['contracts']) > 0:
                in_trade = True
                current_side = 'long' if p['side'] == 'long' else 'short'

        # SE NÃO ESTÁ EM TRADE -> IA PROCURA ENTRADA
        if not in_trade and side:
            res = execute_trade(side, asset, leverage, margin_usd, m_type)
            st.session_state.v32_log = res
            st.toast(res)

        # SE ESTÁ EM TRADE -> IA PROCURA FECHAMENTO (REVERSÃO)
        elif in_trade:
            # Se estou em LONG e o sinal vira SHORT ou NEUTRO com score baixo
            if current_side == 'long' and (side == 'sell' or score <= 0):
                res = close_all(asset)
                st.session_state.v32_log = f"FECHAMENTO IA: {res}"
                st.toast("LUCRO NO BOLSO!")
            
            # Se estou em SHORT e o sinal vira LONG ou NEUTRO com score alto
            elif current_side == 'short' and (side == 'buy' or score >= 0):
                res = close_all(asset)
                st.session_state.v32_log = f"FECHAMENTO IA: {res}"
                st.toast("LUCRO NO BOLSO!")

if 'v32_log' not in st.session_state: st.session_state.v32_log = "SISTEMA ONLINE. AGUARDANDO COMANDO DA IA..."

live_engine()

st.divider()
st.code(f"> TERMINAL LOG: {st.session_state.v32_log}")
