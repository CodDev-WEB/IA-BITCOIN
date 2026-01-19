import streamlit as st
import ccxt
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE LAYOUT ---
st.set_page_config(
    page_title="IA-QUANT EXECUTOR V19", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Estilização CSS para manter o gráfico fixo e os números dinâmicos
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; background-color: #0b0e11; }
    .metric-card { 
        background-color: #181a20; padding: 20px; border-radius: 10px; 
        border: 1px solid #2b2f36; text-align: center;
    }
    .value { font-size: 1.8rem; font-weight: bold; font-family: 'Courier New', monospace; color: #00ffcc; }
    .label { color: #848e9c; font-size: 0.9rem; }
    iframe { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO COM A API (FUTUROS) ---
@st.cache_resource
def get_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True,
        'adjustForTimeDifference': True
    })

mexc = get_mexc()

# --- 3. FUNÇÃO DE EXECUÇÃO DE ORDENS ---
def executar_ordem_ia(lado, par_ativo, alavancagem_valor, volume_usd):
    try:
        symbol = f"{par_ativo.split('/')[0]}/USDT:USDT"
        
        # Ajusta Alavancagem antes de abrir a posição
        mexc.set_leverage(alavancagem_valor, symbol)
        
        # Obtém preço atual para calcular quantidade
        ticker_info = mexc.fetch_ticker(symbol)
        preco_atual = ticker_info['last']
        
        # Cálculo da Quantidade (Contratos)
        quantidade_contratos = (volume_usd * alavancagem_valor) / preco_atual
        
        if lado == 'buy':
            ordem = mexc.create_market_buy_order(symbol, quantidade_contratos)
        else:
            ordem = mexc.create_market_sell_order(symbol, quantidade_contratos)
            
        st.toast(f"🚀 ORDEM DE {lado.upper()} ENVIADA!", icon="✅")
        return f"[{datetime.now().strftime('%H:%M:%S')}] {lado.upper()} executado: {quantidade_contratos:.4f} {symbol}"
    except Exception as error:
        return f"❌ Erro na API: {str(error)}"

# --- 4. INTERFACE LATERAL ---
with st.sidebar:
    st.header("🎮 CONFIGURAÇÃO")
    par_selecionado = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT"], index=0)
    alavancagem = st.slider("ALAVANCAGEM", 1, 50, 10)
    valor_trade = st.number_input("VALOR POR TRADE (USD)", value=50, step=10)
    st.divider()
    bot_ligado = st.toggle("🚨 EXECUTOR REAL ATIVO", value=False)
    st.warning("Cuidado: Com o executor ativo, o robô abrirá posições reais na MEXC.")

# --- 5. TÍTULO E GRÁFICO (FIXOS) ---
st.title("⚡ GEN-QUANT TERMINAL & EXECUTOR")

# Widget TradingView de Futuros
st.components.v1.html(f"""
    <div id="tv-chart" style="height:450px;"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
    new TradingView.widget({{
      "autosize": true, "symbol": "MEXC:{par_selecionado.replace('/', '')}.P", 
      "interval": "1", "theme": "dark", "style": "1", "locale": "br", "container_id": "tv-chart"
    }});
    </script>
""", height=450)

# --- 6. MOTOR DE DECISÃO E MONITOR (FRAGMENTO) ---
@st.fragment(run_every=3)
def motor_ia(par):
    symbol_f = f"{par.split('/')[0]}/USDT:USDT"
    
    if 'log_operacao' not in st.session_state:
        st.session_state.log_operacao = "Aguardando sinal estratégico..."

    try:
        dados = mexc.fetch_ticker(symbol_f)
        preco = dados['last']
        maxima = dados['high']
        minima = dados['low']
        
        # Layout de Dados
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"<div class='metric-card'><p class='label'>PREÇO FUTUROS</p><div class='value'>$ {preco:,.2f}</div></div>", unsafe_allow_html=True)
        
        # Estratégia de Validação
        sinal = "AGUARDANDO"
        cor = "#848e9c"
        
        if preco <= minima * 1.001:
            sinal = "COMPRA (LONG)"
            cor = "#00ffcc"
            if bot_ligado:
                st.session_state.log_operacao = executar_ordem_ia('buy', par, alavancagem, valor_trade)
        elif preco >= maxima * 0.999:
            sinal = "VENDA (SHORT)"
            cor = "#ff4d4d"
            if bot_ligado:
                st.session_state.log_operacao = executar_ordem_ia('sell', par, alavancagem, valor_trade)

        with col2:
            st.markdown(f"<div class='metric-card'><p class='label'>SINAL IA</p><div class='value' style='color:{cor}'>{sinal}</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><p class='label'>VARIAÇÃO 24H</p><div class='value'>{dados['percentage']}%</div></div>", unsafe_allow_html=True)
            
        st.caption(f"Motor em execução... Sync: {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        st.caption("A estabelecer ligação com a MEXC...")

# Iniciar o motor de monitorização
motor_ia(par_selecionado)

# --- 7. HISTÓRICO DE LOGS ---
st.divider()
st.subheader("📝 REGISTO DE EXECUÇÃO")
st.code(st.session_state.log_operacao)
