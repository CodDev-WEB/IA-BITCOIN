import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. AUTO-REFRESH (30 SEGUNDOS)
st_autorefresh(interval=30000, key="ia_final_loop")

st.set_page_config(page_title="GEN-QUANT SUPREMO V5", layout="wide")

# --- CONEXÃO SEGURA ---
@st.cache_resource
def connect_mexc():
    try:
        return ccxt.mexc({
            'apiKey': st.secrets["API_KEY"],
            'secret': st.secrets["SECRET_KEY"],
            'options': {'defaultType': 'swap'}, 
            'adjustForTimeDifference': True
        })
    except Exception as e:
        st.error("Erro nos Secrets: Configure API_KEY e SECRET_KEY no Streamlit Cloud.")
        return None

mexc = connect_mexc()

# --- INTELIGÊNCIA ---
def get_data(symbol):
    symbol_f = f"{symbol.split('/')[0]}/USDT:USDT"
    candles = mexc.fetch_ohlcv(symbol_f, timeframe='1m', limit=100)
    df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain/loss)))
    
    # Médias e Bandas
    df['ema_slow'] = df['close'].ewm(span=21).mean()
    df['std'] = df['close'].rolling(20).std()
    df['b_up'] = df['ema_slow'] + (df['std'] * 2)
    df['b_down'] = df['ema_slow'] - (df['std'] * 2)
    df['roc'] = df['close'].pct_change(5) * 100
    
    return df

# --- INTERFACE ---
st.sidebar.title("🧠 IA HUMAN_QUANT")
bot_active = st.sidebar.toggle("ATIVAR IA 24H")
pair = st.sidebar.selectbox("PAR", ["BTC/USDT", "ETH/USDT"])
leverage = st.sidebar.select_slider("ALAVANCAGEM", options=[5, 10, 15, 20], value=10)
amount_usdt = st.sidebar.number_input("BANCA (USDT)", value=50)

st.title(f"AGENT_AI::{pair}")
status = st.empty()

if 'history' not in st.session_state:
    st.session_state.history = []

# --- EXECUÇÃO CORRIGIDA ---
if bot_active and mexc:
    try:
        df = get_data(pair)
        c_price = df['close'].iloc[-1]
        c_rsi = df['rsi'].iloc[-1]
        c_roc = df['roc'].iloc[-1]
        symbol_f = f"{pair.split('/')[0]}/USDT:USDT"

        with status.container():
            col1, col2, col3 = st.columns(3)
            col1.metric("PREÇO", f"${c_price:,.2f}")
            col2.metric("RSI", f"{c_rsi:.2f}")
            col3.metric("MERCADO", "ESTÁVEL" if abs(c_roc) < 1.2 else "VOLÁTIL")

            # Verifica posição
            pos = mexc.fetch_positions([symbol_f])
            has_position = any(float(p['contracts']) > 0 for p in pos)

            if not has_position:
                # 1. CORREÇÃO DO ERRO DE ALAVANCAGEM (Parâmetros obrigatórios da MEXC)
                try:
                    mexc.set_leverage(leverage, symbol_f, {
                        'openType': 2,    # 2 = Margem Cruzada (Cross)
                        'positionType': 1 # 1 = Define alavancagem para a conta no par
                    })
                except: pass # Se já estiver configurado, ignora o erro

                qty = (amount_usdt * leverage) / c_price

                if abs(c_roc) < 1.5:
                    # LONG
                    if c_price <= df['b_down'].iloc[-1] and c_rsi < 30:
                        tp, sl = c_price * 1.02, c_price * 0.985
                        # 2. ADIÇÃO DE PARÂMETROS NA ORDEM
                        mexc.create_market_buy_order(symbol_f, qty, {
                            'takeProfitPrice': tp, 
                            'stopLossPrice': sl,
                            'openType': 2 # Garante que abre em margem cruzada
                        })
                        st.session_state.history.insert(0, {"HORA": datetime.now().strftime("%H:%M"), "AÇÃO": "LONG"})
                        st.balloons()

                    # SHORT
                    elif c_price >= df['b_up'].iloc[-1] and c_rsi > 70:
                        tp, sl = c_price * 0.98, c_price * 1.015
                        mexc.create_market_sell_order(symbol_f, qty, {
                            'takeProfitPrice': tp, 
                            'stopLossPrice': sl,
                            'openType': 2
                        })
                        st.session_state.history.insert(0, {"HORA": datetime.now().strftime("%H:%M"), "AÇÃO": "SHORT"})
            else:
                st.info("🔎 IA Monitorando posição aberta...")

    except Exception as e:
        st.error(f"Erro de Execução: {e}")

if st.session_state.history:
    st.subheader("LOG DE OPERAÇÕES")
    st.table(pd.DataFrame(st.session_state.history).head(5))
