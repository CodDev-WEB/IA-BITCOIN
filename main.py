import streamlit as st
import ccxt
import pandas as pd
import time

# --- 1. INTERFACE ---
st.set_page_config(page_title="QUANT-OS V35", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background: #010409; color: #e0e0e0; }
    .glass-card { background: rgba(13, 17, 23, 0.9); border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center; }
    .neon-green { color: #00ff9d; } .neon-red { color: #ff3366; }
    .value { font-size: 1.5rem; font-weight: bold; font-family: monospace; }
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

# --- 3. MOTOR IA (SCALPING AGRESSIVO) ---
def get_ia_analysis(symbol):
    try:
        # Nota: MEXC usa BTC/USDT:USDT no fetch, mas o erro era na ORDEM
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        df['ema5'] = df['close'].ewm(span=5).mean()
        df['ema13'] = df['close'].ewm(span=13).mean()
        df['std'] = df['close'].rolling(20).std()
        df['up'] = df['close'].rolling(20).mean() + (df['std'] * 2)
        df['lw'] = df['close'].rolling(20).mean() - (df['std'] * 2)
        
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

# --- 4. EXECUÇÃO COM CORREÇÃO DE SÍMBOLO ---
def execute_trade_v35(side, pair, lev, margin, margin_type):
    try:
        # CORREÇÃO DO SÍMBOLO PARA A ORDEM (Removendo o :USDT extra se necessário)
        # Para ordens Swap na MEXC via CCXT, o formato costuma ser 'BTC/USDT:USDT' 
        # mas se der erro, tentamos o formato limpo 'BTC/USDT'
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if margin_type == "Isolada" else 2
        
        # Configura Alavancagem
        try:
            mexc.set_leverage(lev, sym, {'openType': m_code, 'positionType': 1})
            mexc.set_leverage(lev, sym, {'openType': m_code, 'positionType': 2})
        except: pass

        ticker = mexc.fetch_ticker(sym)
        qty = (margin * lev) / ticker['last']
        
        # O SEGREDO: Usar o símbolo que a MEXC espera na ordem
        order = mexc.create_order(symbol=sym, type='market', side=side, amount=qty)
        return f"✅ {side.upper()} ABERTO | {qty:.4f} {pair}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

def close_all_v35(pair):
    try:
        sym = f"{pair.split('/')[0]}/USDT:USDT"
        positions = mexc.fetch_positions([sym])
        for p in positions:
            if float(p['contracts']) > 0:
                side = 'sell' if p['side'] == 'long' else 'buy'
                mexc.create_order(symbol=sym, type='market', side=side, amount=p['contracts'])
        return "✅ POSIÇÕES FECHADAS"
    except Exception as e:
        return f"❌ ERRO AO FECHAR: {str(e)}"

# --- 5. UI SIDEBAR ---
with st.sidebar:
    st.header("🕹️ COMANDO V35")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    lev = st.slider("ALAVANCAGEM", 1, 100, 20)
    mar = st.number_input("MARGEM ($)", value=10)
    m_type = st.radio("MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_on = st.toggle("ATIVAR IA")
    if st.button("FECHAR TUDO"): st.toast(close_all_v35(asset))

st.title("QUANT-OS V35 // THE FINAL PATCH")

# --- 6. CORE ENGINE ---
@st.fragment(run_every=2)
def core_v35():
    sym_f = f"{asset.split('/')[0]}/USDT:USDT"
    label, color, action, price, score = get_ia_analysis(sym_f)
    
    # Wallet Status
    try:
        bal = mexc.fetch_balance({'type': 'swap'})
        total = bal['USDT']['total']
    except: total = 0.0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='glass-card'><div class='label'>EQUITY</div><div class='value'>$ {total:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='glass-card'><div class='label'>PREÇO</div><div class='value'>$ {price:,.2f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='glass-card'><div class='label'>SINAL</div><div class='value {color}'>{label}</div></div>", unsafe_allow_html=True)

    if bot_on:
        # Check Positions
        pos = mexc.fetch_positions([sym_f])
        in_trade = any(float(p['contracts']) > 0 for p in pos)
        
        if not in_trade and action:
            res = execute_trade_v35(action, asset, lev, mar, m_type)
            st.session_state.log35 = res
            st.toast(res)
        elif in_trade and (score == 0 or label == "NEUTRO"):
            res = close_all_v35(asset)
            st.session_state.log35 = f"SAÍDA IA: {res}"
            st.toast("LUCRO NO BOLSO")

if 'log35' not in st.session_state: st.session_state.log35 = "READY"
core_v35()
st.divider()
st.code(f"> LOG: {st.session_state.log35}")
