import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from streamlit_echarts import st_echarts

# 1. AUTO-REFRESH (Mantém a IA viva na nuvem)
st_autorefresh(interval=30000, key="ia_v6_loop")

st.set_page_config(page_title="GEN-QUANT PRO TERMINAL", layout="wide", initial_sidebar_state="expanded")

# --- ESTILO CSS PARA TERMINAL DARK ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-metric-label] { color: #808495 !important; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

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
    except:
        return None

mexc = connect_mexc()

def get_data(symbol):
    symbol_f = f"{symbol.split('/')[0]}/USDT:USDT"
    candles = mexc.fetch_ohlcv(symbol_f, timeframe='1m', limit=100)
    df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    
    # Indicadores Técnicos
    df['ema_21'] = df['close'].ewm(span=21).mean()
    df['std'] = df['close'].rolling(20).std()
    df['b_up'] = df['ema_21'] + (df['std'] * 2)
    df['b_down'] = df['ema_21'] - (df['std'] * 2)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain/loss)))
    df['roc'] = df['close'].pct_change(5) * 100
    return df

# --- SIDEBAR CONFIG ---
st.sidebar.title("⚡ COMANDO IA")
bot_active = st.sidebar.toggle("ATIVAR OPERAÇÕES", value=True)
pair = st.sidebar.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT"])
leverage = st.sidebar.slider("ALAVANCAGEM", 1, 20, 10)
amount_usdt = st.sidebar.number_input("BANCA POR TRADE", value=10)

# --- DASHBOARD PRINCIPAL ---
st.title(f"📊 TERMINAL QUANT :: {pair}")

if mexc:
    try:
        df = get_data(pair)
        c_price = df['close'].iloc[-1]
        c_rsi = df['rsi'].iloc[-1]
        c_roc = df['roc'].iloc[-1]
        symbol_f = f"{pair.split('/')[0]}/USDT:USDT"

        # LINHA 1: MÉTRICAS DE TOPO
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("PREÇO ATUAL", f"${c_price:,.2f}", f"{df['close'].pct_change().iloc[-1]*100:.2f}%")
        m2.metric("RSI (14)", f"{c_rsi:.2f}", "SOBRECOMPRA" if c_rsi > 70 else "SOBREVENDA" if c_rsi < 30 else "NEUTRO")
        m3.metric("MERCADO", "ESTÁVEL" if abs(c_roc) < 1.2 else "VOLÁTIL", delta_color="inverse")
        m4.metric("VOLATILIDADE", f"{df['std'].iloc[-1]:.2f}")

        # LINHA 2: GRÁFICO CANDLESTICK E GAUGES
        col_chart, col_gauge = st.columns([3, 1])

        with col_chart:
            fig = go.Figure(data=[
                go.Candlestick(x=df['ts'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'),
                go.Scatter(x=df['ts'], y=df['b_up'], line=dict(color='rgba(173, 216, 230, 0.4)', width=1), name='Banda Superior'),
                go.Scatter(x=df['ts'], y=df['b_down'], line=dict(color='rgba(173, 216, 230, 0.4)', width=1), name='Banda Inferior', fill='tonexty')
            ])
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_gauge:
            # Gauge de Força do Mercado (RSI)
            option = {
                "series": [{
                    "type": 'gauge',
                    "startAngle": 180, "endAngle": 0, "min": 0, "max": 100,
                    "itemStyle": {"color": '#00ffcc' if 30 < c_rsi < 70 else '#ff4d4d'},
                    "progress": {"show": True, "width": 12},
                    "pointer": {"show": False},
                    "axisLine": {"lineStyle": {"width": 12}},
                    "detail": {"valueAnimation": True, "formatter": '{value}', "fontSize": 25, "offsetCenter": [0, '30%']},
                    "data": [{"value": round(c_rsi, 2), "name": 'RSI'}]
                }]
            }
            st_echarts(options=option, height="280px")
            st.write(f"**Status da IA:** {'🟢 MONITORANDO' if bot_active else '🔴 DESATIVADA'}")

        # --- LÓGICA DE EXECUÇÃO ---
        if bot_active:
            pos = mexc.fetch_positions([symbol_f])
            has_position = any(float(p['contracts']) > 0 for p in pos)

            if not has_position:
                if abs(c_roc) < 1.5:
                    try:
                        mexc.set_leverage(leverage, symbol_f, {'openType': 2, 'positionType': 1})
                    except: pass
                    
                    qty = (amount_usdt * leverage) / c_price
                    
                    if c_price <= df['b_down'].iloc[-1] and c_rsi < 30:
                        mexc.create_market_buy_order(symbol_f, qty, {'takeProfitPrice': c_price*1.02, 'stopLossPrice': c_price*0.985, 'openType': 2})
                        st.toast("🚀 LONG EXECUTADO!", icon="🔥")
                    elif c_price >= df['b_up'].iloc[-1] and c_rsi > 70:
                        mexc.create_market_sell_order(symbol_f, qty, {'takeProfitPrice': c_price*0.98, 'stopLossPrice': c_price*1.015, 'openType': 2})
                        st.toast("📉 SHORT EXECUTADO!", icon="⚡")

    except Exception as e:
        st.error(f"Erro no Terminal: {e}")

# --- LOG DE ATIVIDADE ---
st.subheader("📋 HISTÓRICO DE INTELIGÊNCIA")
if 'history' not in st.session_state: st.session_state.history = []
if st.session_state.history:
    st.table(pd.DataFrame(st.session_state.history).head(10))
else:
    st.info("Varrendo o livro de ordens em busca de assimetria de preço...")
