import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="V55 // ULTIMATE PRECISION", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #e6edf3; }
    .mexc-panel { 
        background: #161a1e; border: 1px solid #2b3036; border-radius: 4px; 
        padding: 15px; margin-bottom: 10px; border-top: 3px solid #f0b90b;
    }
    .pnl-green { color: #00b464; font-weight: bold; font-size: 22px; }
    .pnl-red { color: #f6465d; font-weight: bold; font-size: 22px; }
    .terminal { 
        background: #000; color: #00ff41; padding: 12px; 
        font-family: 'Courier New', monospace; font-size: 11px; 
        height: 120px; border-radius: 5px; border-left: 4px solid #f0b90b;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. MOTOR DE CONEXÃO ---
@st.cache_resource
def init_exchange():
    try:
        return ccxt.mexc({
            'apiKey': st.secrets["API_KEY"],
            'secret': st.secrets["SECRET_KEY"],
            'options': {'defaultType': 'swap', 'adjustForTimeDifference': True},
            'enableRateLimit': True
        })
    except Exception as e:
        st.error(f"Erro Conexão: {e}")
        return None

mexc = init_exchange()

# --- 3. INTELIGÊNCIA VELA-A-VELA ---
def get_market_analysis(symbol):
    try:
        # Para leitura (fetch), usamos o símbolo unificado
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=35)
        if not ohlcv: return None, 0, False
        
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['ema3'] = df['c'].ewm(span=3, adjust=False).mean()
        df['ema8'] = df['c'].ewm(span=8, adjust=False).mean()
        
        last, prev = df.iloc[-1], df.iloc[-2]
        vol_avg = df['v'].rolling(10).mean().iloc[-1]
        
        # Estratégia: Médias cruzadas + Cor da vela atual + Volume
        side = 'buy' if (last['ema3'] > last['ema8'] and last['c'] > prev['c'] and last['v'] > vol_avg) else \
               'sell' if (last['ema3'] < last['ema8'] and last['c'] < prev['c'] and last['v'] > vol_avg) else None
            
        return side, float(last['c']), (last['c'] > last['o'])
    except: return None, 0, False

# --- 4. EXECUÇÃO DE ORDENS (O FIX DEFINITIVO) ---
def execute_trade_v55(side, pair, leverage, compound, m_type):
    try:
        # Símbolo Unificado (para configs e consultas)
        unified_sym = f"{pair.split('/')[0]}/USDT:USDT"
        # Símbolo Nativo (para ordens): Remove o :USDT e troca / por _
        native_sym = pair.replace('/', '_')
        
        m_code = 1 if m_type == "Isolada" else 2
        p_type = 1 if side == 'buy' else 2
        
        # 1. Ajusta Alavancagem (Usa o unificado)
        try:
            mexc.set_leverage(int(leverage), unified_sym, {'openType': m_code, 'positionType': p_type})
        except: pass

        # 2. Verifica Saldo
        bal = mexc.fetch_balance({'type': 'swap'})
        free_usdt = float(bal['USDT']['free'] or 0)
        if free_usdt < 1.0: return "❌ Sem saldo em Futuros."
        
        # 3. Calcula Quantidade
        ticker = mexc.fetch_ticker(unified_sym)
        price = float(ticker['last'])
        qty_raw = (free_usdt * (compound/100) * leverage) / price
        qty = mexc.amount_to_precision(unified_sym, qty_raw)

        # 4. CRIA ORDEM (O segredo está em usar o native_sym aqui)
        # Usamos create_order diretamente para evitar abstrações problemáticas do CCXT
        mexc.create_order(symbol=native_sym, type='market', side=side, amount=qty)
        
        return f"🚀 {side.upper()} ABERTO: {qty} em {pair}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

# --- 5. DASHBOARD ---
with st.sidebar:
    st.header("⚙️ CONFIGURAÇÃO")
    asset = st.selectbox("PAR", ["BTC/USDT", "SOL/USDT", "PEPE/USDT", "ETH/USDT"])
    lev = st.slider("ALAVANCAGEM", 10, 125, 100)
    comp = st.slider("BANCA %", 10, 100, 95)
    m_mode = st.radio("MODO", ["Cruzada", "Isolada"])
    bot_on = st.toggle("LIGAR IA SCALPER")

st.title("QUANT-OS V55 // THE FINAL ENGINE")

c1, c2 = st.columns([2.5, 1])

with c2:
    st.subheader("📊 Live PnL")
    @st.fragment(run_every=1)
    def update_pnl():
        u_sym = f"{asset.split('/')[0]}/USDT:USDT"
        n_sym = asset.replace('/', '_')
        try:
            bal = mexc.fetch_balance({'type': 'swap'})
            total = float(bal['USDT']['total'] or 0)
            st.markdown(f"<div class='mexc-panel'>SALDO TOTAL<br><b>$ {total:,.4f}</b></div>", unsafe_allow_html=True)

            pos = mexc.fetch_positions([u_sym])
            active = [p for p in pos if float(p['contracts'] or 0) > 0]
            
            if active:
                p = active[0]
                pnl = float(p['unrealizedPnl'] or 0)
                roe = float(p['percentage'] or 0)
                style = "pnl-green" if pnl >= 0 else "pnl-red"
                
                st.markdown(f"""
                <div class='mexc-panel'>
                    <b>{asset} {lev}x</b><br>
                    <span class='{style}'>{roe:+.2f}% (${pnl:+.4f})</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Fechamento Automático por Inversão de Vela
                _, _, is_bull = get_market_analysis(u_sym)
                if (p['side'] == 'long' and not is_bull) or (p['side'] == 'short' and is_bull):
                    mexc.create_order(symbol=n_sym, type='market', side='sell' if p['side'] == 'long' else 'buy', amount=p['contracts'])
                    st.toast("💰 Lucro Protegido!")
            elif bot_on:
                side, _, _ = get_market_analysis(u_sym)
                if side:
                    st.session_state.v55_log = execute_trade_v55(side, asset, lev, comp, m_mode)
                    st.toast(st.session_state.v55_log)
        except Exception as e:
            st.error(f"Erro no Loop: {e}")
    update_pnl()

with c1:
    
    st.components.v1.html(f"""
        <div id="tv" style="height:400px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"1","theme":"dark","container_id":"tv"}});</script>
    """, height=400)
    
    if 'v55_log' not in st.session_state: st.session_state.v55_log = "IA em Standby..."
    st.markdown(f"### 📜 Terminal Logs")
    st.markdown(f"<div class='terminal'>> {datetime.now().strftime('%H:%M:%S')} | {st.session_state.v55_log}</div>", unsafe_allow_html=True)
