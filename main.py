import streamlit as st
import ccxt
import pandas as pd
import time
import numpy as np

# --- 1. SETUP INTERFACE ---
st.set_page_config(page_title="V43 // FIX EXECUTION", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #010409; color: #e6edf3; }
    .metric-card { background: #0d1117; border: 1px solid #30363d; border-radius: 10px; padding: 15px; text-align: center; }
    .neon-green { color: #39ff14; font-weight: bold; }
    .neon-red { color: #ff3131; font-weight: bold; }
    .terminal-box { background: #000; color: #0f0; padding: 12px; border-radius: 5px; font-family: monospace; font-size: 0.8rem; border-left: 3px solid #ff3131; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM TRATAMENTO DE ERRO ---
@st.cache_resource
def init_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets["API_KEY"],
        'secret': st.secrets["SECRET_KEY"],
        'options': {'defaultType': 'swap', 'adjustForTimeDifference': True},
        'enableRateLimit': True
    })

try:
    mexc = init_mexc()
except Exception as e:
    st.error(f"Erro de Conexão: {e}")

# --- 3. MOTOR DE ANÁLISE OMNI ---
def get_signals(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # VWAP Manual
        df['tp'] = (df['h'] + df['l'] + df['c']) / 3
        df['vwap'] = (df['tp'] * df['v']).cumsum() / df['v'].cumsum()
        
        # EMAs e RSI
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema21'] = df['c'].ewm(span=21).mean()
        
        last = df.iloc[-1]
        score = 0
        if last['c'] > last['ema9']: score += 1
        if last['ema9'] > last['ema21']: score += 1
        if last['c'] < last['vwap']: score += 1 # Preço abaixo da VWAP (Desconto)
        
        if last['c'] < last['ema9']: score -= 1
        if last['ema9'] < last['ema21']: score -= 1
        
        action = 'buy' if score >= 2 else 'sell' if score <= -2 else None
        return action, last['c'], score
    except:
        return None, 0, 0

# --- 4. FUNÇÃO DE EXECUÇÃO CORRIGIDA (O FIX) ---
def execute_trade_fixed(side, pair, lev, compound_pct, m_type):
    try:
        # 1. Ajuste de Símbolo: MEXC precisa de 'BTC/USDT:USDT' para contratos swap
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        
        # 2. Configurar Margem e Alavancagem antes
        m_code = 1 if m_type == "Isolada" else 2
        try:
            mexc.set_leverage(int(lev), symbol, {'openType': m_code})
        except: pass # Já configurado

        # 3. Cálculo de Quantidade com Precisão Decimal
        bal = mexc.fetch_balance({'type': 'swap'})
        usdt_balance = float(bal['USDT']['free'])
        trade_usd = usdt_balance * (compound_pct / 100)
        
        if trade_usd < 5.0: # MEXC mínimo é geralmente $5 de nocional
             return "❌ Saldo insuficiente para o mínimo da MEXC ($5 USD)"

        ticker = mexc.fetch_ticker(symbol)
        price = ticker['last']
        
        # QTY em contratos (A MEXC usa inteiros ou decimais específicos por moeda)
        raw_qty = (trade_usd * lev) / price
        
        # BUSCA PRECISÃO DA MOEDA (Crucial para não dar erro de API)
        markets = mexc.load_markets()
        market = markets[symbol]
        qty = mexc.amount_to_precision(symbol, raw_qty)

        # 4. ENVIO DA ORDEM MARKET
        order = mexc.create_market_order(symbol, side, qty)
        return f"✅ {side.upper()} EXECUTADO | Qtd: {qty} | Preço: {price}"
        
    except Exception as e:
        return f"❌ ERRO API MEXC: {str(e)}"

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("⚙️ OMNI V43")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 50, 20)
    compound = st.slider("COMPOUND %", 10, 100, 50)
    m_type = st.radio("MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_active = st.toggle("LIGAR AUTO-TRADING")

st.title("V43 // EXECUTION ENGINE")

c1, c2 = st.columns([3, 1])

with c1:
    st.components.v1.html(f"""
        <div id="tv" style="height:400px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"1","theme":"dark","container_id":"tv"}});</script>
    """, height=400)
    
    # Tabela de Posições Ativas
    st.subheader("📋 Posições")
    @st.fragment(run_every=3)
    def show_pos():
        try:
            sym_f = f"{asset.split('/')[0]}/USDT:USDT"
            pos = mexc.fetch_positions([sym_f])
            active = [p for p in pos if float(p['contracts']) > 0]
            if active: st.table(pd.DataFrame(active)[['side', 'contracts', 'entryPrice', 'unrealizedPnl']])
            else: st.info("Sem ordens no momento.")
        except: pass
    show_pos()

with c2:
    st.subheader("🧠 IA")
    @st.fragment(run_every=2)
    def motor():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        action, price, score = get_signals(sym_f)
        
        st.markdown(f"""
            <div class='metric-card'>
                <div style='font-size:12px;'>PREÇO</div>
                <div style='font-size:22px; font-weight:bold;'>$ {price:,.2f}</div>
                <hr>
                <div class='{"neon-green" if score > 0 else "neon-red"}'>{action if action else "NEUTRO"}</div>
                <div style='font-size:11px;'>SCORE: {score}</div>
            </div>
        """, unsafe_allow_html=True)

        if bot_active and action:
            # Verifica se já está posicionado
            pos = mexc.fetch_positions([sym_f])
            if not any(float(p['contracts']) > 0 for p in pos):
                res = execute_trade_fixed(action, asset, leverage, compound, m_type)
                st.session_state.log43 = res
                st.toast(res)
    motor()

st.divider()
if 'log43' not in st.session_state: st.session_state.log43 = "Sistema Pronto."
st.markdown(f"<div class='terminal-box'>> {st.session_state.log43}</div>", unsafe_allow_html=True)
