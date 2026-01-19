import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. ATUALIZAÇÃO ULTRA-RÁPIDA (5 segundos)
st_autorefresh(interval=5000, key="ia_elite_loop")

st.set_page_config(page_title="GEN-QUANT ELITE V8", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PARA ESTILO DARK MEXC ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: white; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 10px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    .order-bid { color: #00ffcc; font-family: monospace; }
    .order-ask { color: #ff4d4d; font-family: monospace; }
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

# --- FUNÇÕES DE DADOS ---
def get_market_intelligence(symbol):
    symbol_f = f"{symbol.split('/')[0]}/USDT:USDT"
    # OHLCV + Order Book
    candles = mexc.fetch_ohlcv(symbol_f, timeframe='1m', limit=100)
    orderbook = mexc.fetch_order_book(symbol_f, limit=10)
    
    df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    
    # Indicadores
    df['ema_fast'] = df['close'].ewm(span=9).mean()
    df['std'] = df['close'].rolling(20).std()
    df['b_up'] = df['ema_fast'] + (df['std'] * 2)
    df['b_down'] = df['ema_fast'] - (df['std'] * 2)
    
    return df, orderbook

# --- DASHBOARD ---
if mexc:
    try:
        pair = "BTC/USDT"
        symbol_f = f"{pair.split('/')[0]}/USDT:USDT"
        df, ob = get_market_intelligence(pair)
        c_price = df['close'].iloc[-1]
        
        # LINHA 1: MÉTRICAS TIPO MEXC
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("PREÇO", f"${c_price:,.2f}")
        m2.metric("MÁX 24H", f"${df['high'].max():,.2f}")
        m3.metric("MÍN 24H", f"${df['low'].min():,.2f}")
        m4.metric("VOL (BTC)", f"{df['vol'].iloc[-1]:.2f}")
        m5.metric("STATUS IA", "EXECUTANDO" if st.sidebar.toggle("ATIVAR", True) else "PAUSADA")

        # LINHA 2: GRÁFICO (ESQUERDA) + ORDERBOOK (DIREITA)
        col_main, col_side = st.columns([3, 1])

        with col_main:
            # Gráfico Candlestick + Volume (Subplots)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            
            # Candles e Bandas
            fig.add_trace(go.Candlestick(x=df['ts'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['ts'], y=df['b_up'], line=dict(color='rgba(255,255,255,0.2)'), name='Bollinger'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['ts'], y=df['b_down'], line=dict(color='rgba(255,255,255,0.2)'), fill='tonexty'), row=1, col=1)
            
            # Volume
            fig.add_trace(go.Bar(x=df['ts'], y=df['vol'], marker_color='gray', name='Volume'), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_side:
            st.subheader("Order Book")
            # Simulação do Livro de Ordens Estilizado
            asks = pd.DataFrame(ob['asks'], columns=['Price', 'Qty']).sort_values('Price', ascending=False)
            bids = pd.DataFrame(ob['bids'], columns=['Price', 'Qty'])
            
            for _, row in asks.head(5).iterrows():
                st.markdown(f"<div class='order-ask'>{row['Price']:,.2f} &nbsp;&nbsp;&nbsp; {row['Qty']:.4f}</div>", unsafe_allow_html=True)
            st.markdown(f"### {c_price:,.2f}")
            for _, row in bids.head(5).iterrows():
                st.markdown(f"<div class='order-bid'>{row['Price']:,.2f} &nbsp;&nbsp;&nbsp; {row['Qty']:.4f}</div>", unsafe_allow_html=True)

        # LINHA 3: POSIÇÕES ABERTAS (A parte crucial que faltava)
        st.divider()
        st.subheader("Posições em Aberto")
        pos = mexc.fetch_positions([symbol_f])
        active_pos = [p for p in pos if float(p['contracts']) > 0]
        
        if active_pos:
            for p in active_pos:
                pc1, pc2, pc3, pc4 = st.columns(4)
                pnl = float(p['unrealizedPnl'])
                pc1.write(f"**Lado:** {p['side'].upper()}")
                pc2.write(f"**Entrada:** ${float(p['entryPrice']):,.2f}")
                pc3.write(f"**PNL:** :{'green' if pnl > 0 else 'red'}[${pnl:.2f}]")
                pc4.write(f"**Liquidação:** ${float(p['liquidationPrice']):,.2f}")
        else:
            st.info("Nenhuma posição aberta no momento.")

    except Exception as e:
        st.error(f"Sync Error: {e}")
