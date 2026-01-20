import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time

# --- 1. CONFIGURAÇÃO DE INTERFACE DE ALTA PERFORMANCE ---
st.set_page_config(page_title="V46 // SINGULARITY", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #010409; color: #e6edf3; }
    header {visibility: hidden;}
    .metric-card {
        background: #0d1117; border: 1px solid #30363d; border-radius: 12px;
        padding: 15px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.6);
    }
    .neon-gold { color: #f0b90b; font-weight: bold; text-shadow: 0 0 12px #f0b90b77; }
    .neon-green { color: #39ff14; font-weight: bold; }
    .neon-red { color: #ff3131; font-weight: bold; }
    .terminal-box {
        background: #000; color: #00ff41; padding: 15px;
        border-radius: 8px; font-family: 'Courier New', monospace; font-size: 0.85rem;
        border-left: 5px solid #f0b90b;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. ENGINE DE CONEXÃO ROBUSTA ---
@st.cache_resource
def get_exchange_connection():
    try:
        exchange = ccxt.mexc({
            'apiKey': st.secrets["API_KEY"],
            'secret': st.secrets["SECRET_KEY"],
            'options': {
                'defaultType': 'swap',
                'adjustForTimeDifference': True,
                'recvWindow': 10000 
            },
            'enableRateLimit': True
        })
        return exchange
    except Exception as e:
        st.error(f"Erro Crítico de Conexão: {e}")
        return None

mexc = get_exchange_connection()

# --- 3. MOTOR DE INTELIGÊNCIA TÉCNICA (LÓGICA PURA) ---
def analyze_market_logic(symbol):
    try:
        # Puxa dados de 1m (Execução) e 5m (Tendência)
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=60)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # --- INDICADORES ---
        # 1. EMA 3/8 (Gatilho Rápido)
        df['ema3'] = df['c'].ewm(span=3, adjust=False).mean()
        df['ema8'] = df['c'].ewm(span=8, adjust=False).mean()
        
        # 2. VWAP (Preço Médio por Volume)
        df['vwap'] = (df['c'] * df['v']).cumsum() / df['v'].cumsum()
        
        # 3. RSI 7 (Momentum)
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        rsi = 100 - (100 / (1 + (gain / (loss + 1e-10))))
        
        # 4. Filtro de Volume (Volume > Média de 20 períodos)
        vol_mean = df['v'].rolling(20).mean()
        vol_confirmed = df['v'].iloc[-1] > vol_mean.iloc[-1]

        last = df.iloc[-1]
        score = 0
        
        # --- LÓGICA DE ENTRADA ---
        if last['ema3'] > last['ema8'] and last['c'] > last['vwap']:
            score += 2
        if rsi.iloc[-1] < 40: score += 1
        if vol_confirmed: score += 1

        if last['ema3'] < last['ema8'] and last['c'] < last['vwap']:
            score -= 2
        if rsi.iloc[-1] > 60: score -= 1
        if vol_confirmed: score -= 1

        # --- LÓGICA DE SAÍDA (Onde o lucro é feito) ---
        # Sai se o sinal inverter ou RSI atingir extremos
        exit_long = rsi.iloc[-1] > 80 or last['c'] < last['ema8']
        exit_short = rsi.iloc[-1] < 20 or last['c'] > last['ema8']

        return {
            "side": "buy" if score >= 3 else "sell" if score <= -3 else None,
            "price": last['c'],
            "score": score,
            "rsi": rsi.iloc[-1],
            "exit_long": exit_long,
            "exit_short": exit_short
        }
    except:
        return None

# --- 4. EXECUÇÃO PROFISSIONAL ---
def execute_smart_order(side, pair, lev, compound_pct, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if m_type == "Isolada" else 2
        
        mexc.load_markets()
        mexc.set_leverage(int(lev), symbol, {'openType': m_code})

        bal = mexc.fetch_balance({'type': 'swap'})
        free_balance = float(bal['USDT']['free'])
        margin = free_balance * (compound_pct / 100)
        
        if margin < 5.0: return "❌ Saldo Insuficiente (Mín. $5)"

        ticker = mexc.fetch_ticker(symbol)
        raw_qty = (margin * lev) / ticker['last']
        
        # Ajusta precisão para a MEXC não recusar
        qty = mexc.amount_to_precision(symbol, raw_qty)

        order = mexc.create_market_order(symbol, side, qty)
        return f"🚀 {side.upper()} EXECUTADO | QTY: {qty}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

# --- 5. INTERFACE DASHBOARD ---
with st.sidebar:
    st.header("⚡ SINGULARITY CORE")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT"])
    leverage = st.slider("ALAVANCAGEM", 1, 100, 20)
    comp_pct = st.slider("COMPOUND %", 10, 100, 90)
    m_type = st.radio("MODO MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    bot_on = st.toggle("ATIVAR AUTO-QUANT")

st.title("V46 // THE SINGULARITY ENGINE")

c_chart, c_stats = st.columns([3, 1])

with c_chart:
    st.components.v1.html(f"""
        <div id="tv" style="height:450px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"1","theme":"dark","style":"1","container_id":"tv"}});</script>
    """, height=450)
    
    # MONITOR DE OPERAÇÕES EM TEMPO REAL
    st.subheader("📋 Gestão de Ativos")
    @st.fragment(run_every=2)
    def operation_manager():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        data = analyze_market_logic(sym_f)
        
        if data:
            try:
                pos = mexc.fetch_positions([sym_f])
                active = [p for p in pos if float(p['contracts']) > 0]
                
                if active:
                    p = active[0]
                    # Lógica de Saída Ativa
                    if (p['side'] == 'long' and data['exit_long']) or (p['side'] == 'short' and data['exit_short']):
                        mexc.create_market_order(sym_f, 'sell' if p['side'] == 'long' else 'buy', p['contracts'])
                        st.session_state.v46_log = "💰 Lucro Garantido! Saída por sinal de exaustão."
                        st.toast("POSIÇÃO ENCERRADA")
                    else:
                        st.success(f"EM OPERAÇÃO: {p['side'].upper()} | ROE: {p['percentage']}% | PnL: ${p['unrealizedPnl']}")
                else:
                    if bot_on and data['side']:
                        res = execute_smart_order(data['side'], asset, leverage, comp_pct, m_type)
                        st.session_state.v46_log = res
                        st.toast(res)
            except: pass
    operation_manager()

with c_stats:
    st.subheader("📊 IA BRAIN")
    @st.fragment(run_every=2)
    def update_brain():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        s = analyze_market_logic(sym_f)
        try:
            bal = mexc.fetch_balance({'type': 'swap'})
            total = bal['USDT']['total']
            st.markdown(f"<div class='metric-card'>BANCA TOTAL<br><span class='neon-gold'>$ {total:,.4f}</span></div>", unsafe_allow_html=True)
        except: pass
        
        if s:
            color = "neon-green" if s['score'] > 0 else "neon-red" if s['score'] < 0 else "white"
            st.markdown(f"""
                <div class='metric-card'>
                    <div class='{color}' style='font-size:20px;'>{s['side'].upper() if s['side'] else "NEUTRO"}</div>
                    <div style='font-size:12px;'>SCORE: {s['score']} | RSI: {s['rsi']:.1f}</div>
                </div>
            """, unsafe_allow_html=True)
    update_brain()

st.divider()
if 'v46_log' not in st.session_state: st.session_state.v46_log = "AGUARDANDO CONFLUÊNCIA..."
st.markdown(f"<div class='terminal-box'><strong>LOG:</strong> {st.session_state.v46_log}</div>", unsafe_allow_html=True)
