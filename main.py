import streamlit as st
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. SETUP DE INTERFACE ---
st.set_page_config(page_title="V50 // OMNI-FINAL", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #e6edf3; }
    .mexc-panel { 
        background: #161a1e; border: 1px solid #2b3036; border-radius: 4px; 
        padding: 15px; margin-bottom: 10px;
    }
    .pnl-green { color: #00b464; font-weight: bold; font-size: 22px; }
    .pnl-red { color: #f6465d; font-weight: bold; font-size: 22px; }
    .text-label { color: #848e9c; font-size: 12px; }
    .terminal { background: #000; color: #00ff41; padding: 10px; font-family: monospace; font-size: 11px; height: 100px; border-left: 3px solid #f0b90b; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO CORE ---
@st.cache_resource
def init_exchange():
    return ccxt.mexc({
        'apiKey': st.secrets["API_KEY"],
        'secret': st.secrets["SECRET_KEY"],
        'options': {'defaultType': 'swap', 'adjustForTimeDifference': True},
        'enableRateLimit': True
    })

mexc = init_exchange()

# --- 3. MOTOR DE ANÁLISE (VELA E VOLUME) ---
def get_market_verdict(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=30)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # Estratégia de Reação Rápida
        df['ema3'] = df['c'].ewm(span=3).mean()
        df['ema8'] = df['c'].ewm(span=8).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Verificação de rompimento com volume
        vol_avg = df['v'].rolling(10).mean().iloc[-1]
        high_vol = last['v'] > vol_avg
        
        side = 'buy' if (last['ema3'] > last['ema8'] and last['c'] > prev['c'] and high_vol) else \
               'sell' if (last['ema3'] < last['ema8'] and last['c'] < prev['c'] and high_vol) else None
               
        return side, last['c'], (last['c'] > last['o'])
    except: return None, 0, False

# --- 4. EXECUÇÃO CORRIGIDA (O FIX DO ERRO) ---
def execute_order_fixed(side, pair, leverage, compound, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        mexc.load_markets()
        market = mexc.market(symbol)
        
        # FIX: MEXC agora exige positionType e openType explicitamente
        # openType: 1 (Isolada), 2 (Cruzada)
        # positionType: 1 (Long), 2 (Short)
        m_code = 1 if m_type == "Isolada" else 2
        p_type = 1 if side == 'buy' else 2
        
        try:
            mexc.set_leverage(int(leverage), symbol, {
                'openType': m_code, 
                'positionType': p_type
            })
        except: pass # Se já estiver configurado, ele ignora o erro

        # Cálculo de banca
        bal = mexc.fetch_balance({'type': 'swap'})
        free_margin = float(bal['USDT']['free'])
        trade_usd = free_margin * (compound / 100)
        
        price = mexc.fetch_ticker(symbol)['last']
        qty_raw = (trade_usd * leverage) / price
        
        # Precisão de Contrato
        min_qty = market['limits']['amount']['min']
        qty = max(min_qty, float(mexc.amount_to_precision(symbol, qty_raw)))

        order = mexc.create_market_order(symbol, side, qty)
        return f"🔥 ORDEM {side.upper()} EXECUTADA: {qty} contratos."
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

# --- 5. INTERFACE DASHBOARD ---
with st.sidebar:
    st.header("⚡ TERMINAL CONFIG")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "SOL/USDT", "ETH/USDT", "PEPE/USDT"])
    leverage = st.slider("ALAVANCAGEM", 10, 125, 100)
    compound = st.slider("COMPOUND %", 10, 100, 90)
    margin_mode = st.radio("MARGEM", ["Cruzada", "Isolada"])
    bot_active = st.toggle("ATIVAR IA AUTO-TRADING")

st.title("V50 // SINGULARITY REAL-TIME")

col_left, col_right = st.columns([2.5, 1])

with col_right:
    st.subheader("💰 Performance")
    @st.fragment(run_every=1)
    def update_dashboard():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        try:
            # Posições e Saldo
            pos = mexc.fetch_positions([sym_f])
            active = [p for p in pos if float(p['contracts']) > 0]
            bal = mexc.fetch_balance({'type': 'swap'})
            
            st.markdown(f"""
            <div class='mexc-panel'>
                <span class='text-label'>Saldo da Carteira</span><br>
                <span style='font-size:22px; font-weight:bold; color:#f0b90b;'>$ {bal['USDT']['total']:,.4f}</span>
            </div>
            """, unsafe_allow_html=True)

            if active:
                p = active[0]
                pnl = float(p['unrealizedPnl'])
                roe = float(p['percentage'])
                style = "pnl-green" if pnl >= 0 else "pnl-red"
                
                st.markdown(f"""
                <div class='mexc-panel'>
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='font-weight:bold;'>{asset} <span style='color:#f0b90b;'>{leverage}x</span></span>
                    </div>
                    <hr style='border: 0.1px solid #2b3036;'>
                    <span class='text-label'>ROE %</span><br>
                    <span class='{style}'>{roe:+.2f}%</span><br>
                    <span class='text-label'>PNL ($)</span><br>
                    <span class='{style}'>${pnl:+.4f}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Inteligência de Saída
                verdict, price, is_bull = get_market_verdict(sym_f)
                if (p['side'] == 'long' and not is_bull) or (p['side'] == 'short' and is_bull):
                    mexc.create_market_order(sym_f, 'sell' if p['side'] == 'long' else 'buy', p['contracts'])
                    st.toast("SAÍDA EXECUTADA: Vela reverteu.")
            else:
                st.info("Aguardando sinal técnico...")
                if bot_active:
                    side, price, is_bull = get_market_verdict(sym_f)
                    if side:
                        res = execute_order_fixed(side, asset, leverage, compound, margin_mode)
                        st.session_state.v50_log = res
                        st.toast(res)
        except Exception as e: st.error(e)
    update_dashboard()

with col_left:
    st.components.v1.html(f"""
        <div id="tv-chart" style="height:450px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
          "autosize": true, "symbol": "MEXC:{asset.replace('/','')}.P",
          "interval": "1", "theme": "dark", "style": "1", "container_id": "tv-chart"
        }});
        </script>
    """, height=450)
    
    st.markdown("### 📜 Log do Sistema")
    if 'v50_log' not in st.session_state: st.session_state.v50_log = "IA Operacional."
    st.markdown(f"<div class='terminal'>> {st.session_state.v50_log}</div>", unsafe_allow_html=True)
