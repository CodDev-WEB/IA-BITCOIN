import streamlit as st
import ccxt
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE LAYOUT DA PÁGINA ---
st.set_page_config(
    page_title="IA-QUANT FUTUROS V17",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILO CSS (Visual Terminal MEXC) ---
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
    .value { font-size: 1.8rem; font-weight: bold; font-family: 'Courier New', monospace; color: #00ffcc; }
    iframe { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXÃO COM A API DA MEXC (MERCADO FUTUROS) ---
@st.cache_resource
def get_mexc_connection():
    try:
        return ccxt.mexc({
            'apiKey': st.secrets.get("API_KEY", ""),
            'secret': st.secrets.get("SECRET_KEY", ""),
            'options': {'defaultType': 'swap'}, # Define como FUTUROS PERPÉTUOS
            'enableRateLimit': True,
            'adjustForTimeDifference': True
        })
    except Exception as e:
        st.error(f"Erro ao conectar com a API: {e}")
        return None

mexc = get_mexc_connection()

# --- 4. BARRA LATERAL DE CONFIGURAÇÕES ---
with st.sidebar:
    st.header("⚙️ PAINEL DE CONTROLE")
    pair = st.selectbox("PAR DE NEGOCIAÇÃO", ["BTC/USDT", "ETH/USDT"], index=0)
    leverage = st.slider("ALAVANCAGEM", 1, 50, 10)
    st.divider()
    st.write("Configurado para: **MEXC FUTURES**")

# --- 5. TÍTULO PRINCIPAL ---
st.title("⚡ GEN-QUANT TERMINAL PRO")

# --- 6. GRÁFICO TRADINGVIEW (ESTÁTICO - NÃO RECARREGA) ---
# Este componente carrega uma vez e permanece fixo na tela
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

# --- 7. FRAGMENTO DE DADOS EM TEMPO REAL ---
# Esta função atualiza apenas os números a cada 2 segundos sem piscar a página
@st.fragment(run_every=2)
def live_data_updates(symbol_name):
    if mexc:
        try:
            # Formatação de símbolo correta para Futuros MEXC no CCXT
            formatted_symbol = f"{symbol_name.split('/')[0]}/USDT:USDT"
            
            ticker = mexc.fetch_ticker(formatted_symbol)
            price = ticker['last']
            change = ticker['percentage']
            high = ticker['high']
            low = ticker['low']

            # Colunas de métricas rápidas
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.markdown(f"""<div class='metric-card'>
                    <div class='label'>PREÇO ATUAL</div>
                    <div class='value'>$ {price:,.2f}</div>
                </div>""", unsafe_allow_html=True)

            with c2:
                color = "#00ffcc" if change >= 0 else "#ff4d4d"
                st.markdown(f"""<div class='metric-card'>
                    <div class='label'>VARIAÇÃO 24H</div>
                    <div class='value' style='color:{color};'>{change}%</div>
                </div>""", unsafe_allow_html=True)

            with c3:
                # Exemplo de lógica para SINAL IA (Validação Técnica)
                signal = "NEUTRO"
                sig_color = "#848e9c"
                if price <= low * 1.002:
                    signal = "COMPRA (LONG)"
                    sig_color = "#00ffcc"
                elif price >= high * 0.998:
                    signal = "VENDA (SHORT)"
                    sig_color = "#ff4d4d"

                st.markdown(f"""<div class='metric-card'>
                    <div class='label'>SINAL IA</div>
                    <div class='value' style='color:{sig_color};'>{signal}</div>
                </div>""", unsafe_allow_html=True)

            with c4:
                st.markdown(f"""<div class='metric-card'>
                    <div class='label'>CONEXÃO API</div>
                    <div class='value' style='color:#f0b90b; font-size: 1.2rem;'>LIVE</div>
                    <div style='font-size:10px; color:#848e9c;'>{datetime.now().strftime('%H:%M:%S')}</div>
                </div>""", unsafe_allow_html=True)

        except Exception as e:
            st.caption(f"Buscando dados da MEXC... ({e})")
    else:
        st.error("API não conectada. Verifique os Secrets.")

# Chama a função de tempo real
live_data_updates(pair)

# --- 8. MONITOR DE EXECUÇÃO (RODAPÉ) ---
st.divider()
st.subheader("📋 Log de Atividades do Motor")
st.caption("Aguardando confirmação de sinal da IA para execução automática em modo Futuros.")
