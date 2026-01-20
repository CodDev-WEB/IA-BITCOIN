import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import numpy as np

# --- 1. SETUP DE INTERFACE QUANT ---
st.set_page_config(page_title="V39 // COMPOUND GOD", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #010409; color: #e6edf3; }
    .status-card { background: linear-gradient(145deg, #0d1117, #161b22); border-radius: 12px; padding: 20px; border: 1px solid #30363d; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
    .neon-gold { color: #f0b90b; font-weight: bold; text-shadow: 0 0 10px #f0b90b88; font-family: 'Courier New'; }
    .neon-green { color: #39ff14; font-weight: bold; }
    .neon-red { color: #ff3131; font-weight: bold; }
    .terminal { background: #000; color: #0f0; padding: 15px; border-radius: 10px; font-family: monospace; border: 1px solid #333; }
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

# --- 3. MOTOR DE INTELIGÊNCIA ARTIFICIAL (7 INDICADORES) ---
def get_god_analysis(symbol):
    try:
        # Puxa dados de 5m para análise principal
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='5m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # --- INDICADORES TÉCNICOS ---
        # 1. Tendência (EMA 20/50/200)
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)
        
        # 2. Momentum (RSI + MACD)
        df['rsi'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        df['macd'] = macd['MACD_12_26_9']
        df['macds'] = macd['MACDs_12_26_9']
        
        # 3. Volatilidade (Bollinger + ATR)
        bb = ta.bbands(df['close'], length=20, std=2)
        df['bb_upper'] = bb['BBU_20_2.0']
        df['bb_lower'] = bb['BBL_20_2.0']
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # 4. Reversão (Stochastic)
        stoch = ta.stoch(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch['STOCHk_14_3_3']
        
        last = df.iloc[-1]
        score = 0
        
        # LÓGICA DE PONTUAÇÃO (CONFLUÊNCIA AGRESSIVA)
        # Compra
        if last['close'] > last['ema20']: score += 1
        if last['rsi'] < 40: score += 1
        if last['macd'] > last['macds']: score += 1
        if last['close'] < last['bb_lower']: score += 2
        if last['stoch_k'] < 20: score += 1
        
        # Venda
        if last['close'] < last['ema20']: score -= 1
        if last['rsi'] > 60: score -= 1
        if last['macd'] < last['macds']: score -= 1
        if last['close'] > last['bb_upper']: score -= 2
        if last['stoch_k'] > 80: score -= 1

        # Decisão baseada em Score (Filtro de 5 a 15 min)
        if score >= 4: return "STRONG BUY", "neon-green", "buy", last['close'], score
        if score <= -4: return "STRONG SELL", "neon-red", "sell", last['close'], score
        
        return "WAITING SIGNAL", "white", None, last['close'], score
    except Exception as e:
        return f"ERROR: {str(e)}", "white", None, 0.0, 0

# --- 4. FUNÇÃO DE TRADE COM JUROS COMPOSTOS ---
def execute_compound_trade(side, pair, lev, compound_percent, margin_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        m_code = 1 if margin_type == "Isolada" else 2
        mexc.set_leverage(lev, symbol, {'openType': m_code})
        
        # Cálculo de Juros Compostos: Usa % do saldo total
        bal = mexc.fetch_balance({'type': 'swap'})
        total_balance = float(bal['USDT']['total'])
        trade_margin = total_balance * (compound_percent / 100)
        
        if trade_margin < 1.0: trade_margin = 1.0 # Mínimo 1 dólar
        
        ticker = mexc.fetch_ticker(symbol)
        qty = (trade_margin * lev) / ticker['last']
        
        mexc.create_order(symbol, 'market', side, qty)
        return f"🚀 {side.upper()} EXECUTADO | MARGEM: ${trade_margin:.2f} | QTD: {qty:.4f}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

# --- 5. INTERFACE MASTER ---
with st.sidebar:
    st.header("🔑 MASTER ACCOUNT")
    asset = st.selectbox("PAR DE MOEDA", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT", "DOGE/USDT"])
    leverage = st.slider("ALAVANCAGEM (AGRESSIVA)", 1, 125, 50)
    compound_rate = st.slider("COMPOUND % (JUROS COMPOSTOS)", 10, 100, 80)
    m_type = st.radio("TIPO DE MARGEM", ["Isolada", "Cruzada"])
    st.divider()
    trading_on = st.toggle("LIGAR IA COMPOUND GOD")
    if st.button("🔴 FECHAR TUDO (EMERGÊNCIA)", use_container_width=True):
        st.write("Encerrando...")

st.title("V39 // THE COMPOUND GOD 🏛️")

# GRID DE DADOS
col_c, col_d = st.columns([3, 1])

with col_c:
    st.components.v1.html(f"""
        <div id="tv" style="height:500px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"5","theme":"dark","style":"1","container_id":"tv"}});</script>
    """, height=500)
    
    # Painel de Posições
    st.subheader("📋 Monitor de Crescimento")
    @st.fragment(run_every=3)
    def pos_monitor():
        try:
            sym_f = f"{asset.split('/')[0]}/USDT:USDT"
            pos = mexc.fetch_positions([sym_f])
            data = [p for p in pos if float(p['contracts']) > 0]
            if data:
                st.dataframe(pd.DataFrame(data)[['symbol', 'side', 'entryPrice', 'unrealizedPnl', 'percentage']], use_container_width=True)
            else: st.info("A IA está analisando velas de 5m/15m para o próximo tiro.")
        except: pass
    pos_monitor()

with col_d:
    st.subheader("🧠 IA CORE")
    @st.fragment(run_every=2)
    def brain():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        status, style, action, price, score = get_god_analysis(sym_f)
        
        st.markdown(f"""
            <div class='status-card'>
                <div style='color:#8b949e; font-size:12px;'>VALOR ATUAL</div>
                <div style='font-size:26px; font-weight:bold;' class='neon-gold'>$ {price:,.2f}</div>
                <hr style='border:0.1px solid #30363d;'>
                <div class='{style}' style='font-size:20px;'>{status}</div>
                <div style='font-size:14px; color:#58a6ff; margin-top:10px;'>CONFLUÊNCIA: {score}/7</div>
            </div>
        """, unsafe_allow_html=True)

        if trading_on and action:
            pos = mexc.fetch_positions([sym_f])
            if not any(float(p['contracts']) > 0 for p in pos):
                res = execute_compound_trade(action, asset, leverage, compound_rate, m_type)
                st.session_state.log39 = res
                st.toast(res)
            else:
                # Lógica de Saída por Alvo de Indicador (Lucro de Pombo)
                if score == 0:
                    mexc.create_order(sym_f, 'market', 'sell' if action == 'buy' else 'buy', pos[0]['contracts'])
                    st.toast("ALVO ATINGIDO! JUROS COMPOSTOS APLICADOS.")

    brain()
    
    # Saldo Real-Time
    try:
        bal = mexc.fetch_balance({'type': 'swap'})
        total_usd = bal['USDT']['total']
        st.metric("BANCA ATUAL", f"$ {total_usd:,.4f}")
    except: pass

st.divider()
if 'log39' not in st.session_state: st.session_state.log39 = "SISTEMA INICIALIZADO. MODO COMPOUND ATIVO."
st.markdown(f"<div class='terminal'>> {st.session_state.log39}</div>", unsafe_allow_html=True)
