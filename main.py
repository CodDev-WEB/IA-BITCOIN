import streamlit as st
import ccxt
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="IA-QUANT FUTUROS", layout="wide", initial_sidebar_state="collapsed")

# Estilo para simular o terminal da MEXC
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; background-color: #0b0e11; }
    .metric-card { 
        background-color: #181a20; padding: 20px; border-radius: 10px; 
        border: 1px solid #2b2f36; text-align: center;
    }
    .value { font-size: 1.8rem; font-weight: bold; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def get_mexc_api():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'}, # Define mercado de FUTUROS
        'enableRateLimit': True
    })

mexc = get_mexc_api()

# --- PAINEL LATERAL ---
with st.sidebar:
    st.header("⚙️ CONFIGURAÇÃO FUTUROS")
    pair = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 50, 10)
    bot_active = st.toggle("EXECUTOR IA ATIVO", value=False)

# --- GRÁFICO DE FUTUROS (ESTÁTICO) ---
st.components.v1.html(f"""
    <div id="tradingview_chart" style="height:500px;"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
    new TradingView.widget({{
      "autosize": true,
      "symbol": "MEXC:{pair.replace('/', '')}.P",
      "interval": "1",
      "theme": "dark",
      "container_id": "tradingview_chart"
    }});
    </script>
""", height=500)

# --- DADOS EM TEMPO REAL (SEM REFRESH DE PÁGINA) ---
@st.fragment(run_every=2)
def update_metrics(symbol_name):
    try:
        # Formato específico para contratos Perpétuos da MEXC
        formatted_symbol = f"{symbol_name.split('/')[0]}/USDT:USDT"
        ticker = mexc.fetch_ticker(formatted_symbol)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='metric-card'><p>PREÇO FUTUROS</p><div class='value'>$ {ticker['last']:,.2f}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card'><p>VARIAÇÃO 24H</p><div class='value'>{ticker['percentage']}%</div></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='metric-card'><p>STATUS IA</p><div class='value' style='color:#f0b90b'>VALIDANDO</div></div>", unsafe_allow_html=True)
            
        st.
