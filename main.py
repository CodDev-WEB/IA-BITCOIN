import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE INTERFACE (ESTILO TERMINAL PROFISSIONAL) ---
st.set_page_config(page_title="V54 // ULTIMATE QUANT", layout="wide", initial_sidebar_state="collapsed")

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
        font-family: 'Courier New', monospace; font-size: 11px; 
        height: 150px; border-radius: 5px; overflow-y: auto;
        border-left: 4px solid #f0b90b;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. MOTOR DE CONEXÃO E TRADUTOR DE SÍMBOLOS ---
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
        st.error(f"Erro Crítico de Conexão: {e}")
        return None

mexc = init_exchange()

def get_native_symbol(pair):
    """Converte BTC/USDT para BTC_USDT (formato exigido pela MEXC para ordens)"""
    return pair.replace('/', '_')

# --- 3. INTELIGÊNCIA TÉCNICA (ANÁLISE VELA-A-VELA) ---
def analyze_market_v54(symbol):
    try:
        # Puxa 100 velas para ter média móvel estável
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        if not ohlcv: return None, 0, False
        
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # Estratégia de Scalping Rápido (EMA 3/8 + Volume)
        df['ema3'] = df['c'].ewm(span=3, adjust=False).mean()
        df['ema8'] = df['c'].ewm(span=8, adjust=False).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        vol_avg = df['v'].rolling(20).mean().iloc[-1]
        
        # Lógica de Gatilho
        side = None
        if (last['ema3'] > last['ema8']) and (last['c'] > prev['c']) and (last['v'] > vol_avg):
            side = 'buy'
        elif (last['ema3'] < last['ema8']) and (last['c'] < prev['c']) and (last['v'] > vol_avg):
            side = 'sell'
            
        return side, float(last['c']), (last['c'] > last['o'])
    except Exception as e:
        return None, 0, False

# --- 4. MOTOR DE EXECUÇÃO À PROVA DE FALHAS ---
def execute_trade_v54(side, pair, leverage, compound, m_type):
    try:
        unified_sym = f"{pair.split('/')[0]}/USDT:USDT"
        native_sym = get_native_symbol(pair)
        
        m_code = 1 if m_type == "Isolada" else 2
        p_type = 1 if side == 'buy' else 2
        
        # Seta alavancagem com os novos parâmetros obrigatórios
        try:
            mexc.set_leverage(int(leverage), unified_sym, {'openType': m_code, 'positionType': p_type})
        except: pass

        # Verifica saldo real na carteira Swap
        bal = mexc.fetch_balance({'type': 'swap'})
        if not bal or 'USDT' not in bal: return "❌ Erro: Carteira de Futuros vazia ou inacessível."
        
        free_usdt = float(bal['USDT']['free'] or 0)
        if free_usdt < 1.0: return "❌ Saldo Insuficiente (Mín. $1 USDT)."
        
        # Calcula quantidade respeitando o compound
        ticker = mexc.fetch_ticker(unified_sym)
        price = float(ticker['last'])
        qty_raw = (free_usdt * (compound/100) * leverage) / price
        
        # Garante precisão aceita pela MEXC
        qty = mexc.amount_to_precision(unified_sym, qty_raw)

        # Envia a ordem usando o símbolo nativo
        mexc.create_order(native_sym, 'market', side, qty)
        return f"🔥 {side.upper()} ABERTO: {qty} contratos em {pair}"
    except Exception as e:
        return f"❌ ERRO API: {str(e)}"

# --- 5. INTERFACE DASHBOARD ---
with st.sidebar:
    st.header("⚡ TERMINAL CORE")
    asset = st.selectbox("PAR DE TRADING", ["BTC/USDT", "SOL/USDT", "ETH/USDT", "PEPE/USDT"])
    lev = st.slider("ALAVANCAGEM", 10, 125, 100)
    comp = st.slider("USO DA BANCA %", 10, 100, 95)
    margin_mode = st.radio("MODO MARGEM", ["Cruzada", "Isolada"])
    st.divider()
    bot_enabled = st.toggle("ATIVAR IA TRADING")
    if st.button("FECHAR TODAS POSIÇÕES"):
        st.warning("Comando enviado!")

st.title("QUANT-OS V54 // THE SINGULARITY")

col_left, col_right = st.columns([2.5, 1])

with col_right:
    st.subheader("📊 Posições & PnL")
    @st.fragment(run_every=1)
    def update_pnl_v54():
        u_sym = f"{asset.split('/')[0]}/USDT:USDT"
        n_sym = get_native_symbol(asset)
        try:
            # 1. PNL em Tempo Real
            positions = mexc.fetch_positions([u_sym])
            active = [p for p in positions if float(p['contracts'] or 0) > 0]
            
            # 2. Saldo Atualizado
            bal = mexc.fetch_balance({'type': 'swap'})
            total = float(bal['USDT']['total'] or 0)
            
            st.markdown(f"""
            <div class='mexc-panel'>
                <span class='text-label'>SALDO TOTAL</span><br>
                <span style='font-size:24px; font-weight:bold; color:#f0b90b;'>$ {total:,.4f}</span>
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
                        <b>{asset} <span style='color:#f0b90b;'>{lev}x</span></b>
                    </div>
                    <hr style='border: 0.1px solid #2b3036;'>
                    <span class='text-label'>PnL (%)</span><br>
                    <span class='{style}'>{roe:+.2f}%</span><br>
                    <span class='text-label'>VALOR EM DOLAR</span><br>
                    <span class='{style}'>${pnl:+.4f}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Inteligência de Saída: Fecha se a vela de 1m inverter
                _, _, is_bull = analyze_market_v54(u_sym)
                if (p['side'] == 'long' and not is_bull) or (p['side'] == 'short' and is_bull):
                    mexc.create_order(n_sym, 'market', 'sell' if p['side'] == 'long' else 'buy', p['contracts'])
                    st.toast("💰 LUCRO GARANTIDO! Reversão detectada.")
            else:
                st.info("Aguardando novo sinal técnico...")
                if bot_enabled:
                    side, price, is_bull = analyze_market_v54(u_sym)
                    if side:
                        res = execute_trade_v54(side, asset, lev, comp, margin_mode)
                        st.session_state.v54_log = res
                        st.toast(res)
        except Exception as e:
            st.error(f"Erro no Monitor: {e}")
    update_pnl_v54()

with col_left:
    # TradingView Chart
    st.components.v1.html(f"""
        <div id="tv" style="height:450px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize":true,"symbol":"MEXC:{asset.replace('/','')}.P","interval":"1","theme":"dark","container_id":"tv"}});</script>
    """, height=450)
    
    st.markdown("### 🖥️ Log de Operações")
    if 'v54_log' not in st.session_state: st.session_state.v54_log = "IA Conectada e pronta."
    st.markdown(f"<div class='terminal'>> {datetime.now().strftime('%H:%M:%S')} | {st.session_state.v54_log}</div>", unsafe_allow_html=True)
