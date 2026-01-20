import streamlit as st
import ccxt
import pandas as pd
import time

# --- 1. CONFIGURAÇÃO DE TELA ---
st.set_page_config(page_title="TRADER-OS V36", layout="wide")

# Estilo Dark Pro
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: white; }
    .status-card { 
        background: #161b22; border: 1px solid #30363d; 
        border-radius: 10px; padding: 15px; text-align: center; 
    }
    .neon-text { color: #58a6ff; font-weight: bold; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO SEGURA ---
@st.cache_resource
def get_exchange():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = get_exchange()

# --- 3. INTELIGÊNCIA DE MERCADO (CURTO PRAZO) ---
def analyze_market(symbol):
    try:
        # Busca dados para análise técnica
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # Estratégia: EMA 9 + Bollinger Bands
        df['ema'] = df['close'].ewm(span=9).mean()
        df['std'] = df['close'].rolling(20).std()
        df['upper'] = df['close'].rolling(20).mean() + (df['std'] * 2)
        df['lower'] = df['close'].rolling(20).mean() - (df['std'] * 2)
        
        last = df.iloc[-1]
        
        # Sinal de Scalping (Entrada rápida)
        if last['close'] < last['lower']:
            return "COMPRA (LONG)", "#00ff9d", "buy", last['close']
        elif last['close'] > last['upper']:
            return "VENDA (SHORT)", "#ff3366", "sell", last['close']
        
        return "AGUARDANDO", "#8b949e", None, last['close']
    except:
        return "ERRO SYNC", "#8b949e", None, 0

# --- 4. EXECUÇÃO DE ORDENS ---
def trade_now(side, pair, lev, margin, m_type):
    try:
        # Formata o símbolo como a MEXC quer: BTC/USDT:USDT
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if m_type == "Isolada" else 2
        
        # Configura Alavancagem e Margem
        mexc.set_leverage(lev, symbol, {'openType': m_code})
        
        ticker = mexc.fetch_ticker(symbol)
        amount = (margin * lev) / ticker['last']
        
        # Ordem a Mercado
        order = mexc.create_order(symbol, 'market', side, amount)
        return f"✅ {side.upper()} EXECUTADO | Vol: {amount:.4f}"
    except Exception as e:
        return f"❌ ERRO: {str(e)}"

# --- 5. INTERFACE DO USUÁRIO ---
with st.sidebar:
    st.header("⚡ CONTROLE")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 50, 20)
    margin = st.number_input("MARGEM ($)", value=10)
    margin_type = st.radio("TIPO DE MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_active = st.toggle("LIGAR IA EXECUTORA")

# --- COLUNAS PRINCIPAIS ---
col_main, col_side = st.columns([3, 1])

with col_main:
    # GRÁFICO TRADINGVIEW (RESTAURADO)
    st.components.v1.html(f"""
        <div id="tradingview_chart" style="height:500px;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
          "autosize": true, "symbol": "MEXC:{asset.replace('/', '')}.P",
          "interval": "1", "theme": "dark", "style": "1", "locale": "br", "container_id": "tradingview_chart"
        }});
        </script>
    """, height=500)

with col_side:
    st.subheader("📊 STATUS IA")
    
    # Motor de atualização em tempo real
    @st.fragment(run_every=2)
    def update_status():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        label, color, side, price = analyze_market(sym_f)
        
        st.markdown(f"""
            <div class='status-card'>
                <div style='color: #8b949e; font-size: 12px;'>PREÇO ATUAL</div>
                <div class='value' style='font-size: 20px;'>$ {price:,.2f}</div>
                <hr style='border: 0.1px solid #30363d;'>
                <div style='color: {color}; font-weight: bold; font-size: 18px;'>{label}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Lógica de Execução
        if bot_active and side:
            # Proteção simples para não abrir ordens repetidas
            if 'last_t' not in st.session_state or (time.time() - st.session_state.last_t > 60):
                res = trade_now(side, asset, leverage, margin, margin_type)
                st.session_state.last_t = time.time()
                st.session_state.terminal_log = res
                st.toast(res)

    update_status()

st.divider()
st.subheader("📟 LOG DO TERMINAL")
if 'terminal_log' not in st.session_state: st.session_state.terminal_log = "Sistema inicializado..."
st.code(f"> {st.session_state.terminal_log}")
