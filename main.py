import streamlit as st
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. SETUP DE INTERFACE ---
st.set_page_config(page_title="V51 // RESILIENT-QUANT", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #e6edf3; }
    .mexc-panel { 
        background: #161a1e; border: 1px solid #2b3036; border-radius: 4px; 
        padding: 15px; margin-bottom: 10px;
    }
    .pnl-green { color: #00b464; font-weight: bold; font-size: 22px; }
    .pnl-red { color: #f6465d; font-weight: bold; font-size: 22px; }
    .terminal { background: #000; color: #00ff41; padding: 10px; font-family: monospace; font-size: 11px; height: 100px; border-left: 3px solid #f0b90b; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO SEGURA ---
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
        st.error(f"Erro de Conexão: {e}")
        return None

mexc = init_exchange()

# --- 3. MOTOR DE ANÁLISE COM FILTRO DE ERRO ---
def get_market_verdict(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=30)
        if not ohlcv: return None, 0, False
        
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['ema3'] = df['c'].ewm(span=3).mean()
        df['ema8'] = df['c'].ewm(span=8).mean()
        
        last, prev = df.iloc[-1], df.iloc[-2]
        vol_avg = df['v'].rolling(10).mean().iloc[-1]
        
        # Lógica de Gatilho
        side = 'buy' if (last['ema3'] > last['ema8'] and last['c'] > prev['c'] and last['v'] > vol_avg) else \
               'sell' if (last['ema3'] < last['ema8'] and last['c'] < prev['c'] and last['v'] > vol_avg) else None
               
        return side, last['c'], (last['c'] > last['o'])
    except:
        return None, 0, False

# --- 4. EXECUÇÃO À PROVA DE FALHAS (FIX NONETYPE) ---
def execute_order_resilient(side, pair, leverage, compound, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        mexc.load_markets()
        market = mexc.market(symbol)
        
        m_code = 1 if m_type == "Isolada" else 2
        p_type = 1 if side == 'buy' else 2
        
        try:
            mexc.set_leverage(int(leverage), symbol, {'openType': m_code, 'positionType': p_type})
        except: pass

        # FIX CRÍTICO: Verificação de Saldo (Evita NoneType)
        bal = mexc.fetch_balance({'type': 'swap'})
        if bal is None or 'USDT' not in bal or 'free' not in bal['USDT']:
            return "❌ Erro: Saldo não encontrado. Verifique se há fundos na carteira de Futuros."
            
        free_margin = float(bal['USDT']['free'] or 0)
        if free_margin <= 0: return "❌ Saldo insuficiente na carteira Swap."
        
        trade_usd = free_margin * (compound / 100)
        ticker = mexc.fetch_ticker(symbol)
        curr_price = float(ticker['last'] or 0)
        
        if curr_price == 0: return "❌ Erro: Preço do ativo não recebido."

        qty_raw = (trade_usd * leverage) / curr_price
        min_qty = float(market['limits']['amount']['min'] or 0)
        qty = max(min_qty, float(mexc.amount_to_precision(symbol, qty_raw)))

        mexc.create_market_order(symbol, side, qty)
        return f"🔥 {side.upper()} EXECUTADO: {qty} contratos."
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("⚡ CONFIG")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "SOL/USDT", "PEPE/USDT"])
    lev = st.slider("ALAVANCAGEM", 10, 125, 100)
    comp = st.slider("COMPOUND %", 10, 100, 95)
    margin_mode = st.radio("MARGEM", ["Cruzada", "Isolada"])
    bot_on = st.toggle("ATIVAR IA")

st.title("V51 // RESILIENTE (FIXED NONETYPE)")

col_left, col_right = st.columns([2.5, 1])

with col_right:
    st.subheader("💰 Live Wallet")
    @st.fragment(run_every=2)
    def update_resilient():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        try:
            bal = mexc.fetch_balance({'type': 'swap'})
            # Verificação de segurança para o saldo total
            total_bal = bal['USDT']['total'] if (bal and 'USDT' in bal) else 0.0
            
            st.markdown(f"<div class='mexc-panel'>SALDO TOTAL<br><span style='font-size:22px; font-weight:bold; color:#f0b90b;'>$ {total_bal:,.4f}</span></div>", unsafe_allow_html=True)

            pos = mexc.fetch_positions([sym_f])
            active = [p for p in pos if float(p['contracts'] or 0) > 0]
            
            if active:
                p = active[0]
                pnl = float(p['unrealizedPnl'] or 0)
                roe = float(p['percentage'] or 0)
                style = "pnl-green" if pnl >= 0 else "pnl-red"
                
                st.markdown(f"""
                <div class='mexc-panel'>
                    <span style='font-weight:bold;'>{asset} <span style='color:#f0b90b;'>{lev}x</span></span><br>
                    <span class='{style}'>{roe:+.2f}% (${pnl:+.4f})</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Saída Automática
                _, _, is_bull = get_market_verdict(sym_f)
                if (p['side'] == 'long' and not is_bull) or (p['side'] == 'short' and is_bull):
                    mexc.create_market_order(sym_f, 'sell' if p['side'] == 'long' else 'buy', p['contracts'])
                    st.toast("POSIÇÃO FECHADA: Reversão detectada.")
            else:
                if bot_on:
                    side, _, _ = get_market_verdict(sym_f)
                    if side:
                        res = execute_order_resilient(side, asset, lev, comp, margin_mode)
                        st.session_state.v51_log = res
                        st.toast(res)
        except: pass
    update_resilient()

with col_left:
    st.components.v1.html(f"""
        <div id="tv" style="height:450px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"1","theme":"dark","container_id":"tv"}});</script>
    """, height=450)
    
    if 'v51_log' not in st.session_state: st.session_state.v51_log = "Sistema Pronto."
    st.markdown(f"<div class='terminal'>> {st.session_state.v51_log}</div>", unsafe_allow_html=True)
