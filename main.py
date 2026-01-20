import streamlit as st
import ccxt
import pandas as pd
import time
import numpy as np

# --- 1. CONFIGURAÇÃO DE ALTA PERFORMANCE ---
st.set_page_config(page_title="QUANT-OS V38 // SINGULARITY", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #010409; color: #e6edf3; }
    .status-card { background: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #30363d; text-align: center; }
    .neon-green { color: #39ff14; font-weight: bold; text-shadow: 0 0 5px #39ff1488; }
    .neon-red { color: #ff3131; font-weight: bold; text-shadow: 0 0 5px #ff313188; }
    .terminal { background: black; color: #00ff00; padding: 15px; border-radius: 8px; font-family: 'Courier New', monospace; font-size: 0.8rem; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO CORE ---
@st.cache_resource
def init_exchange():
    return ccxt.mexc({
        'apiKey': st.secrets.get("API_KEY", ""),
        'secret': st.secrets.get("SECRET_KEY", ""),
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True
    })

mexc = init_exchange()

# --- 3. CÉREBRO DA IA: ANÁLISE MULTIDIMENSIONAL ---
def get_institutional_analysis(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # 1. EMAs (Tendência)
        df['ema9'] = df['close'].ewm(span=9).mean()
        df['ema21'] = df['close'].ewm(span=21).mean()
        
        # 2. RSI (Exaustão)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        # 3. Bollinger Bands (Volatilidade)
        df['sma20'] = df['close'].rolling(20).mean()
        df['std'] = df['close'].rolling(20).std()
        df['upper'] = df['sma20'] + (df['std'] * 2)
        df['lower'] = df['sma20'] - (df['std'] * 2)
        
        # 4. MACD (Força)
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        last = df.iloc[-1]
        score = 0
        
        # --- PONTUAÇÃO DE CONFLUÊNCIA ---
        if last['ema9'] > last['ema21']: score += 1 # Tendência Alta
        if last['rsi'] < 35: score += 2             # Sobrevenda extrema
        if last['close'] < last['lower']: score += 2 # Preço furou banda inferior
        if last['macd'] > last['signal']: score += 1 # Cruzamento MACD
        
        if last['ema9'] < last['ema21']: score -= 1 # Tendência Baixa
        if last['rsi'] > 65: score -= 2             # Sobrecompra extrema
        if last['close'] > last['upper']: score -= 2 # Preço furou banda superior
        if last['macd'] < last['signal']: score -= 1 # Cruzamento MACD negativo

        if score >= 3: return "FORTE COMPRA", "neon-green", "buy", last['close'], score
        if score <= -3: return "FORTE VENDA", "neon-red", "sell", last['close'], score
        
        return "AGUARDANDO CONFLUÊNCIA", "white", None, last['close'], score
    except:
        return "SYNCING...", "white", None, 0.0, 0

# --- 4. MOTOR DE EXECUÇÃO ---
def execute_trade(side, pair, lev, margin, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if m_type == "Isolada" else 2
        mexc.set_leverage(lev, symbol, {'openType': m_code})
        
        ticker = mexc.fetch_ticker(symbol)
        qty = (margin * lev) / ticker['last']
        
        mexc.create_order(symbol, 'market', side, qty)
        return f"✅ ORDEM {side.upper()} EXECUTADA: {qty:.4f} {pair}"
    except Exception as e:
        return f"❌ ERRO: {str(e)}"

def emergency_close(symbol):
    try:
        pos = mexc.fetch_positions([symbol])
        for p in pos:
            if float(p['contracts']) > 0:
                side = 'sell' if p['side'] == 'long' else 'buy'
                mexc.create_order(symbol, 'market', side, p['contracts'])
        return "🚨 TODAS AS POSIÇÕES ENCERRADAS"
    except Exception as e:
        return f"ERRO: {e}"

# --- 5. INTERFACE DO TERMINAL ---
with st.sidebar:
    st.header("⚙️ CONFIGURAÇÃO IA")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT", "DOGE/USDT"])
    lev_val = st.slider("ALAVANCAGEM", 1, 100, 20)
    mar_val = st.number_input("MARGEM POR TRADE ($)", value=10)
    m_type = st.radio("TIPO DE MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_ready = st.toggle("🚀 LIGAR AUTO-TRADING")
    if st.button("🔴 PANIC BUTTON: CLOSE ALL", use_container_width=True):
        st.warning(emergency_close(f"{asset.split('/')[0]}/USDT:USDT"))

st.title("🛡️ SINGULARITY V38 // INSTITUTIONAL")

# --- GRID PRINCIPAL ---
col_chart, col_data = st.columns([3, 1])

with col_chart:
    # TradingView 1m
    st.components.v1.html(f"""
        <div id="tv" style="height:450px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"1","theme":"dark","style":"1","container_id":"tv"}});</script>
    """, height=450)
    
    # Painel de Posições
    st.subheader("📋 Posições Ativas")
    @st.fragment(run_every=3)
    def position_panel():
        try:
            sym_f = f"{asset.split('/')[0]}/USDT:USDT"
            pos = mexc.fetch_positions([sym_f])
            data = [p for p in pos if float(p['contracts']) > 0]
            if data:
                df_pos = pd.DataFrame(data)[['symbol', 'side', 'contracts', 'entryPrice', 'percentage']]
                st.dataframe(df_pos, use_container_width=True)
            else:
                st.info("Aguardando oportunidade de entrada...")
        except: pass
    position_panel()

with col_data:
    st.subheader("📊 IA DECISION")
    @st.fragment(run_every=2)
    def decision_engine():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        label, style, action, price, score = get_institutional_analysis(sym_f)
        
        st.markdown(f"""
            <div class='status-card'>
                <div style='color:#8b949e; font-size:12px;'>VALOR ATUAL</div>
                <div style='font-size:24px; font-weight:bold;'>$ {price:,.2f}</div>
                <hr style='border:0.1px solid #30363d;'>
                <div class='{style}' style='font-size:18px;'>{label}</div>
                <div style='font-size:12px; color:#58a6ff;'>SCORE: {score} PTS</div>
            </div>
        """, unsafe_allow_html=True)

        if bot_ready:
            pos = mexc.fetch_positions([sym_f])
            in_trade = any(float(p['contracts']) > 0 for p in pos)
            
            # ENTRADA: Só entra com score forte (3 ou mais)
            if not in_trade and action:
                res = execute_trade(action, asset, lev_val, mar_val, m_type)
                st.session_state.log38 = res
                st.toast(res)
            
            # SAÍDA: Fecha se o score inverter ou zerar (Lucro de Pombo)
            elif in_trade:
                if (score == 0):
                    res = emergency_close(sym_f)
                    st.session_state.log38 = f"ALVO ATINGIDO: {res}"
                    st.toast("LUCRO NO BOLSO!")

    decision_engine()
    
    # Saldo
    try:
        bal = mexc.fetch_balance({'type': 'swap'})
        st.metric("SALDO TOTAL USDT", f"$ {bal['USDT']['total']:,.2f}")
    except: pass

st.divider()
if 'log38' not in st.session_state: st.session_state.log38 = "Sincronizado."
st.markdown(f"<div class='terminal'>> {st.session_state.log38}</div>", unsafe_allow_html=True)
