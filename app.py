import streamlit as st
import ccxt
import pandas as pd
import time
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO DE NUVEM E AUTO-REFRESH ---
# Faz o "cérebro" da IA rodar a cada 30 segundos automaticamente na nuvem
st_autorefresh(interval=30000, key="ia_brain_loop")

st.set_page_config(page_title="GEN-QUANT SUPREMO V5", layout="wide")

# --- 2. CONEXÃO SEGURA (SECRETS) ---
@st.cache_resource
def connect_mexc():
    try:
        # Usa as chaves salvas nos Secrets do Streamlit Cloud
        return ccxt.mexc({
            'apiKey': st.secrets["API_KEY"],
            'secret': st.secrets["SECRET_KEY"],
            'options': {'defaultType': 'swap'}, 
            'adjustForTimeDifference': True,
            'enableRateLimit': True
        })
    except Exception as e:
        st.error(f"Erro de Conexão: Verifique os Secrets. {e}")
        return None

mexc = connect_mexc()

# --- 3. INTELIGÊNCIA DE MERCADO ---
def get_market_data(symbol):
    symbol_f = f"{symbol.split('/')[0]}/USDT:USDT"
    candles = mexc.fetch_ohlcv(symbol_f, timeframe='1m', limit=150)
    df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    
    # Médias Exponenciais (Tendência)
    df['ema_fast'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # RSI (Força)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    # Volatilidade (Bollinger)
    df['std'] = df['close'].rolling(window=20).std()
    df['b_up'] = df['ema_slow'] + (df['std'] * 2)
    df['b_down'] = df['ema_slow'] - (df['std'] * 2)
    
    # ROC (Filtro de Flash Crash)
    df['roc'] = df['close'].pct_change(periods=5) * 100 
    
    return df

# --- 4. INTERFACE DE COMANDO ---
st.sidebar.title("🧠 AGENTE AUTÔNOMO V5")
risk_mode = st.sidebar.select_slider("PERFIL DE RISCO", options=["Conservador", "Moderado", "Agressivo"])
leverage = {"Conservador": 5, "Moderado": 12, "Agressivo": 20}[risk_mode]

amount_usdt = st.sidebar.number_input("BANCA POR OPERAÇÃO (USDT)", value=50)
bot_active = st.sidebar.toggle("ATIVAR IA HUMANA 24H", value=False)
pair = st.sidebar.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT"])

st.title(f"GEN-QUANT::TERMINAL_EXECUTOR")
status_placeholder = st.empty()

if 'history' not in st.session_state:
    st.session_state.history = []

# --- 5. MOTOR DE EXECUÇÃO (SEM WHILE TRUE PARA NUVEM) ---
if mexc and bot_active:
    try:
        df = get_market_data(pair)
        c_price = df['close'].iloc[-1]
        c_rsi = df['rsi'].iloc[-1]
        c_roc = df['roc'].iloc[-1]
        b_up, b_down = df['b_up'].iloc[-1], df['b_down'].iloc[-1]
        symbol_f = f"{pair.split('/')[0]}/USDT:USDT"

        with status_placeholder.container():
            c1, c2, c3 = st.columns(3)
            c1.metric("PREÇO", f"${c_price:,.2f}")
            c2.metric("RSI", f"{c_rsi:.2f}")
            c3.metric("MERCADO", "ESTÁVEL" if abs(c_roc) < 1.2 else "VOLÁTIL")

            # A) VERIFICA SE JÁ HÁ POSIÇÃO (Evita duplicar ordens)
            positions = mexc.fetch_positions([symbol_f])
            has_position = any(float(p['contracts']) > 0 for p in positions)

            if not has_position:
                # Proteção contra Flash Crash
                if abs(c_roc) < 1.5:
                    mexc.set_leverage(leverage, symbol_f, {'openType': 2}) # Margem Cruzada
                    qty = (amount_usdt * leverage) / c_price

                    # LÓGICA DE ENTRADA LONG
                    if c_price <= b_down and c_rsi < 30:
                        tp, sl = c_price * 1.02, c_price * 0.985
                        mexc.create_market_buy_order(symbol_f, qty, {'takeProfitPrice': tp, 'stopLossPrice': sl})
                        st.session_state.history.insert(0, {"HORA": datetime.now().strftime("%H:%M"), "AÇÃO": "LONG", "PREÇO": c_price})
                        st.success("🚀 IA ABRIU LONG!")

                    # LÓGICA DE ENTRADA SHORT
                    elif c_price >= b_up and c_rsi > 70:
                        tp, sl = c_price * 0.98, c_price * 1.015
                        mexc.create_market_sell_order(symbol_f, qty, {'takeProfitPrice': tp, 'stopLossPrice': sl})
                        st.session_state.history.insert(0, {"HORA": datetime.now().strftime("%H:%M"), "AÇÃO": "SHORT", "PREÇO": c_price})
                        st.error("📉 IA ABRIU SHORT!")
                else:
                    st.warning("⚠️ IA pausada por alta volatilidade (Flash Crash).")
            else:
                st.info("🔎 Monitorando posição aberta... Aguardando alvo.")

    except Exception as e:
        st.error(f"Erro de Execução: {e}")

# Exibe Histórico
if st.session_state.history:
    st.subheader("LOG DE OPERAÇÕES")
    st.table(pd.DataFrame(st.session_state.history).head(5))
else:
    st.info("Aguardando o primeiro sinal da IA...")
