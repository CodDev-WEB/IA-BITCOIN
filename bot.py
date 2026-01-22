import streamlit as st
import ccxt
import pandas as pd
import requests
from datetime import datetime

# --- 1. SETUP DE INTERFACE ---
st.set_page_config(page_title="V56 // SIGNAL MODE", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #e6edf3; }
    .signal-card { 
        background: #161a1e; border-left: 5px solid #f0b90b; 
        padding: 20px; border-radius: 5px; margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. MOTOR DE CONEXÃO (APENAS LEITURA) ---
@st.cache_resource
def init_exchange():
    return ccxt.mexc({'options': {'defaultType': 'swap'}})

mexc = init_exchange()

# --- 3. FUNÇÃO DE ENVIO TELEGRAM ---
def send_telegram_signal(message):
    token = st.secrets["TELEGRAM_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    try:
        requests.get(url)
    except Exception as e:
        st.error(f"Erro Telegram: {e}")

# --- 4. INTELIGÊNCIA DE MERCADO ---
def get_analysis(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['ema3'] = df['c'].ewm(span=3).mean()
        df['ema8'] = df['c'].ewm(span=8).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Lógica de Sinal
        if last['ema3'] > last['ema8'] and last['c'] > prev['c']:
            return "🚀 SINAL DE COMPRA (LONG)"
        elif last['ema3'] < last['ema8'] and last['c'] < prev['c']:
            return "🔻 SINAL DE VENDA (SHORT)"
        return None
    except: return None

# --- 5. DASHBOARD E MONITOR ---
st.title("📡 QUANT-OS V56 // MODO SINALIZADOR")

with st.sidebar:
    asset = st.selectbox("ATIVO PARA MONITORAR", ["BTC/USDT:USDT", "SOL/USDT:USDT", "ETH/USDT:USDT"])
    intervalo = st.empty()
    monitoring = st.toggle("ATIVAR MONITORAMENTO DE SINAIS")

if monitoring:
    st.info(f"Monitorando {asset}... Os sinais serão enviados para o Telegram.")
    
    # Fragmento para loop de monitoramento
    @st.fragment(run_every=60) # Checa a cada fechamento de vela (1 min)
    def monitor_engine():
        sinal = get_analysis(asset)
        agora = datetime.now().strftime('%H:%M:%S')
        
        if sinal:
            msg = f"*🔔 NOVO SINAL DETECTADO*\n\n*Ativo:* {asset}\n*Ação:* {sinal}\n*Horário:* {agora}\n\n_Execute manualmente na MEXC se desejar._"
            send_telegram_signal(msg)
            st.markdown(f"<div class='signal-card'><b>{agora}</b> - {sinal} enviado para o Telegram.</div>", unsafe_allow_html=True)
        else:
            st.write(f"[{agora}] Sem sinais claros no momento. Aguardando fechamento de vela...")

    monitor_engine()
else:
    st.warning("Monitoramento em Stand-by. Ligue o botão lateral para iniciar.")

# Gráfico para referência visual
st.components.v1.html(f"""
    <div id="tv-chart" style="height:400px;"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{
      "autosize": true, "symbol": "MEXC:{asset.replace('/','').replace(':USDT','')}.P",
      "interval": "1", "theme": "dark", "container_id": "tv-chart"
    }});
    </script>
""", height=400)
