import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- 1. SETUP DE INTERFACE ESTILO TERMINAL BLOOMBERG ---
st.set_page_config(page_title="V52 // OMNI-QUANT FINAL", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #e6edf3; }
    .mexc-panel { 
        background: #161a1e; border: 1px solid #2b3036; border-radius: 4px; 
        padding: 15px; margin-bottom: 10px; border-top: 3px solid #f0b90b;
    }
    .pnl-green { color: #00b464; font-weight: bold; font-size: 22px; }
    .pnl-red { color: #f6465d; font-weight: bold; font-size: 22px; }
    .text-label { color: #848e9c; font-size: 12px; font-family: 'Inter', sans-serif; }
    .terminal { 
        background: #000; color: #00ff41; padding: 12px; 
        font-family: 'Courier New', monospace; font-size: 12px; 
        height: 120px; border-radius: 5px; overflow-y: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. MOTOR DE CONEXÃO RESILIENTE ---
@st.cache_resource
def init_exchange():
    try:
        if "API_KEY" not in st.secrets:
            st.error("API_KEY não encontrada nos Secrets!")
            return None
        return ccxt.mexc({
            'apiKey': st.secrets["API_KEY"],
            'secret': st.secrets["SECRET_KEY"],
            'options': {'defaultType': 'swap', 'adjustForTimeDifference': True},
            'enableRateLimit': True
        })
    except Exception as e:
        st.error(f"Erro na conexão inicial: {e}")
        return None

mexc = init_exchange()

# --- 3. INTELIGÊNCIA DE MERCADO (VELA-A-VELA) ---
def get_market_analysis(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=30)
        if not ohlcv or len(ohlcv) < 10: return None, 0, False
        
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        df['ema3'] = df['c'].ewm(span=3).mean()
        df['ema8'] = df['c'].ewm(span=8).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        vol_avg = df['v'].rolling(10).mean().iloc[-1]
        
        # Lógica de Gatilho de Alta Probabilidade
        side = None
        if (last['ema3'] > last['ema8']) and (last['c'] > prev['c']) and (last['v'] > vol_avg):
            side = 'buy'
        elif (last['ema3'] < last['ema8']) and (last['c'] < prev['c']) and (last['v'] > vol_avg):
            side = 'sell'
            
        return side, float(last['c'] or 0), (last['c'] > last['o'])
    except:
        return None, 0, False

# --- 4. ENGINE DE EXECUÇÃO À PROVA DE ERROS ---
def execute_trade_v52(side, pair, leverage, compound, m_type):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        mexc.load_markets()
        market = mexc.market(symbol)
        
        # Configuração de Alavancagem Obrigatória MEXC V2
        m_code = 1 if m_type == "Isolada" else 2
        p_type = 1 if side == 'buy' else 2
        try:
            mexc.set_leverage(int(leverage), symbol, {'openType': m_code, 'positionType': p_type})
        except: pass

        # Busca de Saldo com tratamento de None
        bal = mexc.fetch_balance({'type': 'swap'})
        if not bal or 'USDT' not in bal: return "❌ Erro: Saldo indisponível."
        
        free_margin = float(bal['USDT']['free'] or 0)
        if free_margin < 1.0: return "❌ Saldo insuficiente (< $1 USDT)."
        
        # Cálculo de Lote Preciso
        trade_usd = free_margin * (compound / 100)
        ticker = mexc.fetch_ticker(symbol)
        curr_price = float(ticker['last'] or 0)
        
        qty_raw = (trade_usd * leverage) / curr_price
        min_qty = float(market['limits']['amount']['min'] or 0)
        
        # Arredondamento conforme a exchange exige
        qty = max(min_qty, float(mexc.amount_to_precision(symbol, qty_raw)))

        mexc.create_market_order(symbol, side, qty)
        return f"🚀 {side.upper()} ABERTO: {qty} contratos em {curr_price}"
    except Exception as e:
        return f"❌ FALHA NA API: {str(e)}"

# --- 5. DASHBOARD PRINCIPAL ---
with st.sidebar:
    st.header("⚡ CONTROLE OPERACIONAL")
    asset = st.selectbox("ATIVO", ["BTC/USDT", "SOL/USDT", "PEPE/USDT", "ETH/USDT"])
    lev = st.slider("ALAVANCAGEM", 10, 125, 100)
    comp_pct = st.slider("COMPOUND %", 10, 100, 90)
    margin_mode = st.radio("MODO DE MARGEM", ["Cruzada", "Isolada"])
    st.divider()
    bot_enabled = st.toggle("LIGAR ROBÔ SCALPER")

st.title("QUANT-OS V52 // FULL-RECOVERY")

col_main, col_pnl = st.columns([2.5, 1])

with col_pnl:
    st.subheader("📊 Posição Real-Time")
    @st.fragment(run_every=1)
    def live_dashboard():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        try:
            # 1. PNL e Dados de Posição
            positions = mexc.fetch_positions([sym_f])
            active = [p for p in positions if float(p['contracts'] or 0) > 0]
            
            # 2. Saldo Atualizado
            bal = mexc.fetch_balance({'type': 'swap'})
            total_usdt = bal['USDT']['total'] if (bal and 'USDT' in bal) else 0.0
            
            st.markdown(f"""
            <div class='mexc-panel'>
                <span class='text-label'>BANCA ATUAL</span><br>
                <span style='font-size:24px; font-weight:bold; color:#f0b90b;'>$ {total_usdt:,.4f}</span>
            </div>
            """, unsafe_allow_html=True)

            if active:
                p = active[0]
                pnl = float(p['unrealizedPnl'] or 0)
                roe = float(p['percentage'] or 0)
                style = "pnl-green" if pnl >= 0 else "pnl-red"
                
                st.markdown(f"""
                <div class='mexc-panel'>
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='font-weight:bold;'>{asset} <span style='color:#f0b90b;'>{lev}x</span></span>
                    </div>
                    <hr style='border: 0.1px solid #2b3036;'>
                    <span class='text-label'>PnL NÃO REALIZADO</span><br>
                    <span class='{style}'>{pnl:+.4f} USDT</span><br>
                    <span class='text-label'>ROE %</span><br>
                    <span class='{style}'>{roe:+.2f}%</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Lógica de Saída Ativa
                _, _, is_bull = get_market_analysis(sym_f)
                if (p['side'] == 'long' and not is_bull) or (p['side'] == 'short' and is_bull):
                    mexc.create_market_order(sym_f, 'sell' if p['side'] == 'long' else 'buy', p['contracts'])
                    st.toast("💰 LUCRO NO BOLSO! Posição encerrada por reversão de vela.")
            else:
                st.info("Varrendo mercado... À espera de confluência técnica.")
                if bot_enabled:
                    side, price, is_bull = get_market_analysis(sym_f)
                    if side:
                        res = execute_trade_v52(side, asset, lev, comp_pct, margin_mode)
                        st.session_state.v52_log = res
                        st.toast(res)
        except Exception as e:
            st.error(f"Erro no Loop: {e}")
    live_dashboard()

with col_main:
    st.components.v1.html(f"""
        <div id="tv" style="height:450px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"1","theme":"dark","container_id":"tv"}});</script>
    """, height=450)
    
    st.markdown("### 🖥️ Terminal Logs")
    if 'v52_log' not in st.session_state: st.session_state.v52_log = "Sistema V52 pronto para operar."
    st.markdown(f"<div class='terminal'>> {datetime.now().strftime('%H:%M:%S')} | {st.session_state.v52_log}</div>", unsafe_allow_html=True)
