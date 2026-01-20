import streamlit as st
import ccxt
import pandas as pd
import time

# --- 1. INTERFACE ---
st.set_page_config(page_title="QUANT-OS V33 // DEFINITIVE", layout="wide", initial_sidebar_state="collapsed")

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
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def connect_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = connect_mexc()

# --- 3. ANÁLISE IA AGRESSIVA (CURTO PRAZO) ---
def get_ia_signals(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # Estratégia Scalping: EMA 5/13 + Bollinger + RSI
        df['ema5'] = df['close'].ewm(span=5).mean()
        df['ema13'] = df['close'].ewm(span=13).mean()
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['up'] = df['sma20'] + (df['std20'] * 2)
        df['lw'] = df['sma20'] - (df['std20'] * 2)
        
        last = df.iloc[-1]
        score = 0
        if last['ema5'] > last['ema13']: score += 1
        if last['close'] < last['lw']: score += 2
        if last['ema5'] < last['ema13']: score -= 1
        if last['close'] > last['up']: score -= 2
        
        if score >= 2: return "LONG", "neon-green", "buy", last['close'], score
        if score <= -2: return "SHORT", "neon-red", "sell", last['close'], score
        return "NEUTRO", "white", None, last['close'], score
    except:
        return "SYNC", "white", None, 0, 0

# --- 4. EXECUÇÃO CORRIGIDA (O FIX PARA O SEU ERRO) ---
def execute_trade_v33(side, pair, lev, margin, margin_type):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        # openType: 1 = Isolada, 2 = Cruzada
        m_code = 1 if margin_type == "Isolada" else 2
        
        # A MEXC EXIGE DEFINIR ALAVANCAGEM PARA AMBOS OS LADOS (LONG E SHORT)
        try:
            mexc.set_leverage(lev, sym, {'openType': m_code, 'positionType': 1}) # Long
            mexc.set_leverage(lev, sym, {'openType': m_code, 'positionType': 2}) # Short
        except:
            pass # Se já estiver configurado, a API pode dar erro, então ignoramos
        
        ticker = mexc.fetch_ticker(sym)
        qty = (margin * lev) / ticker['last']
        
        # Execução
        mexc.create_market_order(sym, side, qty)
        return f"🔥 {side.upper()} EXECUTADO | {qty:.4f} {pair} | {margin_type}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

def close_all_v33(pair):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        positions = mexc.fetch_positions([sym])
        for p in positions:
            if float(p['contracts']) > 0:
                side = 'sell' if p['side'] == 'long' else 'buy'
                mexc.create_market_order(sym, side, p['contracts'])
        return "✅ POSIÇÕES ENCERRADAS"
    except Exception as e:
        return f"ERRO AO FECHAR: {e}"

# --- 5. UI ---
with st.sidebar:
    st.header("🕹️ COMANDO V33")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 100, 20)
    margin_usd = st.number_input("MARGEM ($)", value=10)
    m_type = st.radio("MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    active = st.toggle("LIGAR IA")
    if st.button("FECHAR TUDO", use_container_width=True):
        st.warning(close_all_v33(asset))

st.title("QUANT-OS V33 // THE FINAL FIX")

# --- 6. MOTOR ---
@st.fragment(run_every=2)
def motor():
    sym_f = f"{asset.split('/')[0]}/USDT:USDT"
    label, color, side, price, score = get_ia_signals(sym_f)
    
    # Wallet (Simples para evitar travas)
    try:
        bal = mexc.fetch_balance({'type': 'swap'})
        total = bal['USDT']['total']
    except:
        total = 0.0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='glass-card'><div class='label'>CARTEIRA</div><div class='value'>$ {total:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='glass-card'><div class='label'>PREÇO</div><div class='value'>$ {price:,.2f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='glass-card'><div class='label'>SINAL IA</div><div class='value {color}'>{label}</div></div>", unsafe_allow_html=True)

    if active:
        # Verifica se já está em posição
        pos = mexc.fetch_positions([sym_f])
        in_trade = any(float(p['contracts']) > 0 for p in pos)
        
        # ENTRADA
        if not in_trade and side:
            res = execute_trade_v33(side, asset, leverage, margin_usd, m_type)
            st.session_state.log33 = res
            st.toast(res)
            
        # FECHAMENTO (Lucro de Pombo Automático)
        elif in_trade:
            # Se a IA mudar o sinal ou score ficar neutro, fecha para garantir lucro
            if (label == "NEUTRO") or (score == 0):
                res = close_all_v33(asset)
                st.session_state.log33 = f"SAÍDA IA: {res}"
                st.toast("POSIÇÃO FECHADA PELA IA")

if 'log33' not in st.session_state: st.session_state.log33 = "ONLINE"
motor()

st.divider()
st.code(f"> LOG: {st.session_state.log33}")
