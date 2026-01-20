import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE INTERFACE PROFISSIONAL ---
st.set_page_config(page_title="QUANT-OS V37", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    header {visibility: hidden;}
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .neon-green { color: #39ff14; font-weight: bold; }
    .neon-red { color: #ff3131; font-weight: bold; }
    .terminal-box {
        background: #010409;
        color: #39ff14;
        padding: 10px;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO SEGURA COM A EXCHANGE ---
@st.cache_resource
def get_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = get_mexc()

# --- 3. MOTOR DE INTELIGÊNCIA (ANÁLISE DE SCALPING) ---
def get_scalper_signals(symbol):
    try:
        # Puxa 50 velas de 1 minuto
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # Estratégia: Médias Rápidas (EMA 9) e Bandas de Bollinger
        df['ema'] = df['close'].ewm(span=9).mean()
        df['std'] = df['close'].rolling(20).std()
        df['upper'] = df['close'].rolling(20).mean() + (df['std'] * 2)
        df['lower'] = df['close'].rolling(20).mean() - (df['std'] * 2)
        
        last = df.iloc[-1]
        
        # Lógica de "Lucro de Pombo" (Reversão às bandas)
        if last['close'] < last['lower']:
            return "COMPRA (LONG)", "neon-green", "buy", last['close']
        elif last['close'] > last['upper']:
            return "VENDA (SHORT)", "neon-red", "sell", last['close']
        
        return "NEUTRO", "white", None, last['close']
    except:
        return "SYNC...", "white", None, 0.0

# --- 4. FUNÇÕES DE NEGOCIAÇÃO ---
def execute_trade(side, pair, lev, margin, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if m_type == "Isolada" else 2
        
        # Ajuste de Alavancagem e Margem
        mexc.set_leverage(lev, symbol, {'openType': m_code})
        
        ticker = mexc.fetch_ticker(symbol)
        qty = (margin * lev) / ticker['last']
        
        # Envio da Ordem
        order = mexc.create_order(symbol, 'market', side, qty)
        return f"🔥 {side.upper()} ABERTO: {qty:.4f} {pair}"
    except Exception as e:
        return f"❌ ERRO: {str(e)}"

def close_position(symbol):
    try:
        positions = mexc.fetch_positions([symbol])
        for p in positions:
            if float(p['contracts']) > 0:
                side = 'sell' if p['side'] == 'long' else 'buy'
                mexc.create_order(symbol, 'market', side, p['contracts'])
        return "✅ POSIÇÃO FECHADA"
    except Exception as e:
        return f"❌ ERRO AO FECHAR: {str(e)}"

# --- 5. INTERFACE DO USUÁRIO ---
with st.sidebar:
    st.header("⚡ CONTROLE MASTER")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT"])
    lev = st.slider("ALAVANCAGEM", 1, 100, 20)
    mar = st.number_input("MARGEM ($)", value=10)
    m_type = st.radio("MODO DE MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_on = st.toggle("ATIVAR IA EXECUTORA")
    if st.button("🔴 FECHAR TUDO AGORA", use_container_width=True):
        res = close_position(f"{asset.split('/')[0]}/USDT:USDT")
        st.toast(res)

# Layout Principal
col_left, col_right = st.columns([3, 1])

with col_left:
    # GRÁFICO TRADINGVIEW (1 MINUTO)
    st.components.v1.html(f"""
        <div id="tv-chart" style="height:450px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
          "autosize": true, "symbol": "MEXC:{asset.replace('/', '')}.P",
          "interval": "1", "theme": "dark", "style": "1", "locale": "pt", "container_id": "tv-chart"
        }});
        </script>
    """, height=450)

    # PAINEL DE POSIÇÕES ATIVAS (EMBAIXO DO GRÁFICO)
    st.subheader("📋 Posições Abertas")
    @st.fragment(run_every=3)
    def show_positions():
        try:
            sym_f = f"{asset.split('/')[0]}/USDT:USDT"
            pos = mexc.fetch_positions([sym_f])
            data = []
            for p in pos:
                if float(p['contracts']) > 0:
                    data.append({
                        "Ativo": p['symbol'],
                        "Lado": p['side'],
                        "Tamanho": p['contracts'],
                        "Preço Entrada": p['entryPrice'],
                        "PnL (ROE%)": f"{float(p['percentage']):.2f}%"
                    })
            if data:
                st.table(pd.DataFrame(data))
            else:
                st.info("Nenhuma posição aberta no momento.")
        except:
            st.error("Erro ao carregar posições.")
    show_positions()

with col_right:
    st.subheader("🤖 IA ANALYTICS")
    @st.fragment(run_every=2)
    def monitor_ia():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        label, style_class, action, price = get_scalper_signals(sym_f)
        
        # Display de Status
        st.markdown(f"""
            <div class='metric-card'>
                <div style='color: #8b949e; font-size: 11px;'>PREÇO ATUAL</div>
                <div style='font-size: 22px; font-weight: bold;'>$ {price:,.2f}</div>
                <hr style='border: 0.1px solid #30363d;'>
                <div class='{style_class}' style='font-size: 18px;'>{label}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Lógica de Trading Automático
        if bot_on and action:
            # Verifica se já está em posição para não duplicar
            pos = mexc.fetch_positions([sym_f])
            in_trade = any(float(p['contracts']) > 0 for p in pos)
            
            if not in_trade:
                res = execute_trade(action, asset, lev, mar, m_type)
                st.session_state.log_v37 = res
                st.toast(res)
            # Saída IA (Se o sinal mudar para o lado oposto)
            elif in_trade:
                current_side = 'buy' if pos[0]['side'] == 'long' else 'sell'
                if action != current_side:
                    close_position(sym_f)
                    st.toast("LUCRO REALIZADO!")

    monitor_ia()
    
    # Wallet Status
    st.divider()
    try:
        bal = mexc.fetch_balance({'type': 'swap'})
        st.metric("Saldo USDT", f"$ {bal['USDT']['total']:,.2f}")
    except:
        st.metric("Saldo USDT", "0.00")

# Terminal Log no Rodapé
st.divider()
st.subheader("📟 Terminal Log")
if 'log_v37' not in st.session_state: st.session_state.log_v37 = "Sincronizado com MEXC."
st.markdown(f"<div class='terminal-box'>> {st.session_state.log_v37}</div>", unsafe_allow_html=True)
