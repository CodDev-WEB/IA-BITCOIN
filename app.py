import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from streamlit_echarts import st_echarts

# 1. AUTO-REFRESH (O coração da IA na nuvem)
st_autorefresh(interval=30000, key="ia_v6_loop")

st.set_page_config(page_title="GEN-QUANT PRO TERMINAL", layout="wide", initial_sidebar_state="expanded")

# --- ESTILO CSS PARA PARECER TERMINAL ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-metric-label] { color: #808495 !important; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_ Wood: True)

# --- CONEXÃO ---
@st.cache_resource
def connect_mexc():
    try:
        return ccxt.mexc({
            'apiKey': st.secrets["API_KEY"],
            'secret': st.secrets["SECRET_KEY"],
            'options': {'defaultType': 'swap'}, 
            'adjustForTimeDifference': True
        })
    except: return None

mexc = connect_mexc()

def get_data(symbol):
    symbol_f = f"{symbol.split('/')[0]}/USDT:USDT"
    candles = mexc.fetch_ohlcv(symbol_f, timeframe='1m', limit=100)
    df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    
    # Cálculos Técnicos
    df['ema_21'] = df['close'].ewm(span=21).mean()
    df['std'] = df['close'].rolling(20).std()
    df['b_up'] = df['ema_21'] + (df['std'] * 2)
    df['b_down'] = df['ema_21'] - (df['std'] * 2)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain/loss)))
    return df

# --- SIDEBAR CONFIG ---
st.sidebar.title("⚡ COMANDO IA")
bot_active = st.sidebar.toggle("ATIVAR OPERAÇÕES", value=True)
pair = st.sidebar.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT"])
leverage = st.sidebar.slider("ALAVANCAGEM", 1, 20, 10)
amount = st.sidebar.number_input("BANCA POR TRADE", value=10)

# --- DASHBOARD PRINCIPAL ---
st.title(f"📊 TERMINAL QUANT :: {pair}")

if mexc:
    df = get_data(pair)
    c_price = df['close'].iloc[-1]
    c_rsi = df['rsi'].iloc[-1]
    
    # LINHA 1: MÉTRICAS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("PREÇO ATUAL", f"${c_price:,.2f}", f"{df['close'].pct_change().iloc[-1]*100:.2f}%")
    m2.metric("RSI (14)", f"{c_rsi:.2f}", "SOBRECOMPRA" if c_rsi > 70 else "SOBREVENDA" if c_rsi < 30 else "NEUTRO")
    m3.metric("TENDÊNCIA", "ALTA" if c_price > df['ema_21'].iloc[-1] else "BAIXA")
    m4.metric("VOLATILIDADE", f"{df['std'].iloc[-1]:.2f}")

    # LINHA 2: GRÁFICO E GAUGES
    col_chart, col_gauge = st.columns([3, 1])

    with col_chart:
        # Gráfico Candlestick com Plotly
        fig = go.Figure(data=[
            go.Candlestick(x=df['ts'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'),
            go.Scatter(x=df['ts'], y=df['b_up'], line=dict(color='rgba(173, 216, 230, 0.5)'), name='Banda Sup'),
            go.Scatter(x=df['ts'], y=df['b_down'], line=dict(color='rgba(173, 216, 230, 0.5)'), name='Banda Inf', fill='tonexty')
        ])
        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_gauge:
        # Gauge de RSI (Sentimento)
        option = {
            "series": [{
                "type": 'gauge',
                "startAngle": 180, "endAngle": 0, "min": 0, "max": 100,
                "splitNumber": 5,
                "itemStyle": {"color": '#58D9F9'},
                "progress": {"show": True, "width": 8},
                "pointer": {"show": False},
                "axisLine": {"lineStyle": {"width": 8}},
                "axisTick": {"show": False}, "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "detail": {"valueAnimation": True, "formatter": '{value}', "fontSize": 20, "offsetCenter": [0, '20%']},
                "data": [{"value": round(c_rsi, 2), "name": 'RSI'}]
            }]
        }
        st_echarts(options=option, height="250px")
        st.write(f"**Status da IA:** {'🟢 OPERANDO' if bot_active else '🔴 PAUSADA'}")

    # LINHA 3: HISTÓRICO PRO
    st.subheader("📋 LOG DE INTELIGÊNCIA")
    if 'history' not in st.session_state: st.session_state.history = []
    
    # Exemplo de Log formatado
    t_df = pd.DataFrame(st.session_state.history)
    if not t_df.empty:
        st.dataframe(t_df, use_container_width=True)
    else:
        st.info("Varrendo o mercado em busca de oportunidades...")

# --- LÓGICA DE TRADE (OCULTA) ---
# (Aqui entra a mesma lógica da MEXC que corrigimos no passo anterior)
