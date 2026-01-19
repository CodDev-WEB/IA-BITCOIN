import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. ATUALIZAÇÃO RÁPIDA (5s) - O autorefresh ainda é necessário na nuvem,
# mas usaremos placeholders para suavizar a transição visual.
st_autorefresh(interval=5000, key="ia_v9_loop")

st.set_page_config(page_title="GEN-QUANT ELITE V9", layout="wide", initial_sidebar_state="collapsed")

# CSS para remover padding e aproximar o visual da MEXC
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource(ttl=2)
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

# --- PLACEHOLDERS (O segredo para não atualizar a página toda) ---
# Definimos os espaços antes de preenchê-los com dados
header_chart = st.empty()
main_layout = st.empty()
positions_footer = st.empty()

def get_data(symbol):
    symbol_f = f"{symbol.split('/')[0]}/USDT:USDT"
    candles = mexc.fetch_ohlcv(symbol_f, timeframe='1m', limit=100)
    # Correção do erro de colunas: garantimos a estrutura exata
    df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    
    # Indicadores
    df['ema_9'] = df['close'].ewm(span=9).mean()
    df['std'] = df['close'].rolling(20).std()
    df['b_up'] = df['ema_9'] + (df['std'] * 2)
    df['b_down'] = df['ema_9'] - (df['std'] * 2)
    return df

# --- EXECUÇÃO ---
if mexc:
    try:
        pair = "BTC/USDT"
        symbol_f = f"{pair.split('/')[0]}/USDT:USDT"
        df = get_data(pair)
        c_price = df['close'].iloc[-1]

        # Preenchendo as métricas de topo
        with header_chart.container():
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("PREÇO", f"${c_price:,.2f}")
            m2.metric("MÁX 24H", f"${df['high'].max():,.2f}")
            m3.metric("MÍN 24H", f"${df['low'].min():,.2f}")
            m4.metric("VOL", f"{df['vol'].iloc[-1]:.1f}")
            m5.metric("SINAL IA", "AGUARDANDO" if c_price > df['b_down'].iloc[-1] else "COMPRA")

        # Gráfico Estável
        with main_layout.container():
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2])
            fig.add_trace(go.Candlestick(x=df['ts'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['ts'], y=df['b_up'], line=dict(color='gray', width=1), name='Bands'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['ts'], y=df['b_down'], line=dict(color='gray', width=1), fill='tonexty'), row=1, col=1)
            fig.add_trace(go.Bar(x=df['ts'], y=df['vol'], marker_color='#30363d'), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Atualização das Posições
        with positions_footer.container():
            st.write("---")
            st.subheader("Painel de Posições")
            pos = mexc.fetch_positions([symbol_f])
            active = [p for p in pos if float(p['contracts']) > 0]
            if active:
                st.table(pd.DataFrame(active)[['symbol', 'side', 'entryPrice', 'unrealizedPnl', 'liquidationPrice']])
            else:
                st.caption(f"Sem posições abertas em {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        # Resolve o erro "2 columns passed, data had 3 columns"
        st.error(f"Erro de Sincronização: {e}")
