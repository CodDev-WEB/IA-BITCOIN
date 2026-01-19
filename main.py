import streamlit as st
import ccxt
import time
from datetime import datetime

# --- CONFIGURAÇÃO DE LAYOUT PROFISSIONAL ---
st.set_page_config(
    page_title="IA-QUANT TERMINAL V15",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estabilização visual via CSS (Cores da MEXC)
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; background-color: #0b0e11; }
    .metric-card { 
        background-color: #181a20; 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px solid #2b2f36;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .label { color: #848e9c; font-size: 0.9rem; margin-bottom: 5px; }
    .value { font-size: 1.8rem; font-weight: bold; font-family: 'Courier New', monospace; }
    iframe { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO BLINDADA COM A API ---
@st.cache_resource
def get_mexc_api():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True,
        'adjustForTimeDifference': True
    })

mexc = get_mexc_api()

# --- INTERFACE PRINCIPAL ---
st.title("⚡ GEN-QUANT TERMINAL PRO")

# COLUNA DE CONFIGURAÇÃO (FIXA)
with st.sidebar:
    st.header("CONTROLE")
    pair = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT"], index=0)
    leverage = st.slider("ALAVANCAGEM", 1, 50, 10)
    bot_active = st.toggle("EXECUTOR ATIVO", value=False)
    st.divider()
    st.info("Modo de Validação: O gráfico abaixo é estático para evitar recarregamento da página.")

# --- GRÁFICO TRADINGVIEW (NUNCA RECARREGA) ---
# O widget oficial da MEXC/TradingView é injetado uma única vez
st.components.v1.html(f"""
    <div id="tradingview_chart" style="height:500px;"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
    new TradingView.widget({{
      "autosize": true,
      "symbol": "MEXC:{pair.replace('/', '')}.P",
      "interval": "1",
      "timezone": "Etc/UTC",
      "theme": "dark",
      "style": "1",
      "locale": "br",
      "toolbar_bg": "#f1f3f6",
      "enable_publishing": false,
      "hide_side_toolbar": false,
      "allow_symbol_change": true,
      "container_id": "tradingview_chart"
    }});
    </script>
""", height=500)

# --- FRAGMENTO DE DADOS EM TEMPO REAL ---
# Esta função atualiza apenas os números, sem dar refresh no gráfico acima
@st.fragment(run_every=2)
def update_live_metrics(symbol_name):
    try:
        # Formato de símbolo corrigido para evitar ExchangeError
        formatted_symbol = f"{symbol_name.split('/')[0]}/USDT:USDT"
        
        ticker = mexc.fetch_ticker(formatted_symbol)
        price = ticker['last']
        high = ticker['high']
        low = ticker['low']
        change = ticker['percentage']

        # Layout de métricas estilo MEXC
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(f"""<div class='metric-card'>
                <div class='label'>PREÇO ATUAL</div>
                <div class='value' style='color:#00ffcc;'>$ {price:,.2f}</div>
            </div>""", unsafe_allow_html=True)

        with c2:
            st.markdown(f"""<div class='metric-card'>
                <div class='label'>VARIAÇÃO 24H</div>
                <div class='value' style='color:{"#00ffcc" if change >= 0 else "#ff4d4d"};'>{change}%</div>
            </div>""", unsafe_allow_html=True)

        with c3:
            # Lógica de Sinais (Exemplo de Validação)
            rsi_simulado = 35.4 # Aqui você integraria sua lógica de indicadores
            status = "AGUARDANDO"
            color = "#848e9c"
            
            if price <= low * 1.002:
                status = "COMPRA"
                color = "#00ffcc"
            elif price >= high * 0.998:
                status = "VENDA"
                color = "#ff4d4d"

            st.markdown(f"""<div class='metric-card'>
                <div class='label'>SINAL IA</div>
                <div class='value' style='color:{color};'>{status}</div>
            </div>""", unsafe_allow_html=True)

        with c4:
             st.markdown(f"""<div class='metric-card'>
                <div class='label'>STATUS API</div>
                <div class='value' style='color:#f0b90b; font-size: 1.2rem;'>ESTÁVEL</div>
                <div style='font-size:10px; color:#848e9c;'>{datetime.now().strftime('%H:%M:%S')}</div>
            </div>""", unsafe_allow_html=True)

    except Exception as e:
        st.caption(f"Sincronizando dados com MEXC... (Verifique se o par {symbol_name} é válido)")

# Executa o fragmento de tempo real
update_live_metrics(pair)

# --- RODAPÉ DE POSIÇÕES (OPCIONAL) ---
st.divider()
st.subheader("📋 Monitor de Execução")
st.caption("As ordens reais só serão enviadas se o 'Executor Ativo' estiver ligado e as chaves API configuradas.")
