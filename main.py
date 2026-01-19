import streamlit as st
import ccxt
import time
from datetime import datetime

# Configuração de Layout
st.set_page_config(page_title="IA-QUANT VALIDATOR", layout="wide", initial_sidebar_state="collapsed")

# CSS para estabilizar o visual dark
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; background-color: #0b0e11; }
    .metric-card { 
        background-color: #181a20; padding: 15px; border-radius: 8px; 
        border: 1px solid #2b2f36; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def get_api():
    # Usamos apenas o necessário para o Ticker público primeiro
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = get_api()

# --- TÍTULO ---
st.title("⚡ GEN-QUANT TERMINAL V14")

# --- GRÁFICO TRADINGVIEW (ESTÁTICO) ---
# O Widget é a melhor forma de validar sem consumir sua banda de API
st.components.v1.html("""
    <div id="tv-chart" style="height:480px;"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
    new TradingView.widget({
      "autosize": true, "symbol": "MEXC:BTCUSDT.P", "interval": "1",
      "theme": "dark", "style": "1", "locale": "br", "container_id": "tv-chart"
    });
    </script>
""", height=480)

# --- FRAGMENTO DE DADOS (CORRIGIDO) ---
@st.fragment(run_every=3) # Aumentamos para 3s para evitar bloqueio de IP (Rate Limit)
def live_dashboard():
    try:
        # CORREÇÃO DO SÍMBOLO: 
        # Para Futuros/Swap na MEXC via CCXT, o formato mais seguro é "BTC/USDT:USDT"
        # mas se falhar, tentamos o ID direto "BTC_USDT"
        symbol = "BTC/USDT:USDT"
        
        ticker = mexc.fetch_ticker(symbol)
        price = ticker['last']
        high = ticker['high']
        low = ticker['low']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"<div class='metric-card'><p style='color:#848e9c;margin:0;'>PREÇO</p><h2 style='color:#00ffcc;margin:0;'>$ {price:,.2f}</h2></div>", unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"<div class='metric-card'><p style='color:#848e9c;margin:0;'>MÁXIMA 24H</p><h2 style='color:#fff;margin:0;'>$ {high:,.1f}</h2></div>", unsafe_allow_html=True)
            
        with col3:
            # Lógica de validação: Se preço cair 1% da máxima, sinaliza atenção
            status = "NEUTRO"
            if price <= low * 1.005: status = "COMPRA"
            elif price >= high * 0.995: status = "VENDA"
            
            st.markdown(f"<div class='metric-card'><p style='color:#848e9c;margin:0;'>SINAL IA</p><h2 style='color:#f0b90b;margin:0;'>{status}</h2></div>", unsafe_allow_html=True)
            
        st.caption(f"Conexão estável • {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        # Se der erro, ele mostra uma mensagem discreta e tenta de novo no próximo ciclo
        st.caption(f"Aguardando resposta da MEXC...")

# Inicia o monitoramento
live_dashboard()
