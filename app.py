import streamlit as st
import ccxt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. ENGINE DE ATUALIZAÇÃO ---
# Intervalo de 5 segundos: O equilíbrio perfeito entre tempo real e estabilidade na nuvem.
st_autorefresh(interval=5000, key="mexc_high_freq_v10")

st.set_page_config(page_title="IA-QUANT ELITE V10", layout="wide", initial_sidebar_state="collapsed")

# CSS para Estética "MEXC Pro" (Cores escuras e métricas compactas)
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    .stMetric { background-color: #1a1e23; border: 1px solid #2b2f36; padding: 12px; border-radius: 4px; }
    div[data-testid="stMetricValue"] { font-family: 'Courier New', monospace; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE DE DADOS ---
@st.cache_resource(ttl=2)
def get_mexc_connection():
    return ccxt.mexc({
        'apiKey': st.secrets["API_KEY"],
        'secret': st.secrets["SECRET_KEY"],
        'options': {'defaultType': 'swap'},
        'adjustForTimeDifference': True
    })

def fetch_market_state(mexc, symbol):
    # OHLCV
    symbol_f = f"{symbol.split('/')[0]}/USDT:USDT"
    candles = mexc.fetch_ohlcv(symbol_f, timeframe='1m', limit=80)
    df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    
    # Indicadores Técnicos
    df['ema'] = df['close'].ewm(span=14).mean()
    df['std'] = df['close'].rolling(20).std()
    df['b_up'] = df['ema'] + (df['std'] * 2)
    df['b_down'] = df['ema'] - (df['std'] * 2)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    # Posições Ativas
    pos = mexc.fetch_positions([symbol_f])
    active_pos = [p for p in pos if float(p['contracts']) > 0]
    
    return df, active_pos

# --- 3. INTERFACE E EXECUÇÃO ---
mexc = get_mexc_connection()

if mexc:
    try:
        # Configurações do Robô
        st.sidebar.title("🎮 COCKPIT")
        pair = st.sidebar.selectbox("PAR", ["BTC/USDT", "ETH/USDT"])
        leverage = st.sidebar.slider("ALAVANCAGEM", 1, 25, 10)
        bot_on = st.sidebar.toggle("EXECUTOR IA", value=True)
        
        df, active_pos = fetch_market_state(mexc, pair)
        c_price = df['close'].iloc[-1]
        c_rsi = df['rsi'].iloc[-1]

        # TOP BAR: MÉTRICAS (Igual ao cabeçalho da MEXC)
        t1, t2, t3, t4, t5 = st.columns(5)
        t1.metric("PREÇO", f"${c_price:,.2f}", f"{df['close'].pct_change().iloc[-1]*100:.2f}%")
        t2.metric("RSI", f"{c_rsi:.1f}", "VENDA" if c_rsi > 70 else "COMPRA" if c_rsi < 30 else "NEUTRO")
        t3.metric("MÁX (1h)", f"${df['high'].max():,.1f}")
        t4.metric("VOL (1m)", f"{df['vol'].iloc[-1]:.2f}")
        t5.metric("POSIÇÕES", len(active_pos))

        # GRÁFICO PROFISSIONAL (Candles + Volume)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df['ts'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Preço"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['ts'], y=df['b_up'], line=dict(color='rgba(255,255,255,0.2)'), name="Bands"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['ts'], y=df['b_down'], line=dict(color='rgba(255,255,255,0.2)'), fill='tonexty'), row=1, col=1)
        # Barras de Volume
        colors = ['red' if df['open'].iloc[i] > df['close'].iloc[i] else 'green' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df['ts'], y=df['vol'], marker_color=colors, name="Volume"), row=2, col=1)
        
        fig.update_layout(template="plotly_dark", height=550, margin=dict(l=10,r=10,t=0,b=0), xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # PAINEL DE POSIÇÕES (Rodapé)
        if active_pos:
            st.subheader("📋 Posições Abertas")
            for p in active_pos:
                with st.container():
                    c1, c2, c3, c4 = st.columns(4)
                    pnl = float(p['unrealizedPnl'])
                    c1.markdown(f"**Lado:** {p['side']}")
                    c2.markdown(f"**Entrada:** ${float(p['entryPrice']):,.2f}")
                    c3.markdown(f"**Lucro/Perda:** :{'green' if pnl > 0 else 'red'}[${pnl:.2f}]")
                    c4.markdown(f"**Liq:** ${float(p['liquidationPrice']):,.2f}")
        else:
            st.caption(f"IA monitorando mercado... Última leitura: {datetime.now().strftime('%H:%M:%S')}")

        # LÓGICA DE EXECUÇÃO (Sem travar interface)
        if bot_on and not active_pos:
            symbol_f = f"{pair.split('/')[0]}/USDT:USDT"
            # SINAL DE COMPRA
            if c_price <= df['b_down'].iloc[-1] and c_rsi < 30:
                mexc.set_leverage(leverage, symbol_f, {'openType': 2, 'positionType': 1})
                mexc.create_market_buy_order(symbol_f, (2 * leverage / c_price), {'openType': 2})
                st.toast("🚀 LONG ABERTO!", icon="🔥")

    except Exception as e:
        st.error(f"Erro no Terminal: {e}")
