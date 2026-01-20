import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="V49 // MIRROR ENGINE", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #e6edf3; }
    .mexc-card { 
        background: #161a1e; border: 1px solid #2b2f36; border-radius: 4px; 
        padding: 15px; font-family: 'Inter', sans-serif;
    }
    .pnl-green { color: #00b464; font-weight: bold; font-size: 18px; }
    .pnl-red { color: #f6465d; font-weight: bold; font-size: 18px; }
    .text-gray { color: #848e9c; font-size: 12px; }
    .terminal { background: #000; color: #00ff41; padding: 10px; font-family: monospace; font-size: 11px; height: 80px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO CORE ---
@st.cache_resource
def init_mexc():
    return ccxt.mexc({
        'apiKey': st.secrets["API_KEY"],
        'secret': st.secrets["SECRET_KEY"],
        'options': {'defaultType': 'swap', 'adjustForTimeDifference': True},
        'enableRateLimit': True
    })

mexc = init_mexc()

# --- 3. MOTOR DE ANÁLISE DE ALTA FREQUÊNCIA ---
def fetch_logic(symbol):
    try:
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=20)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # Estratégia: EMA 3 cruzando a 8 + Volume
        df['ema3'] = df['c'].ewm(span=3).mean()
        df['ema8'] = df['c'].ewm(span=8).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Sinal de Entrada
        side = 'buy' if last['ema3'] > last['ema8'] and last['c'] > prev['c'] else \
               'sell' if last['ema3'] < last['ema8'] and last['c'] < prev['c'] else None
               
        return side, last['c'], (last['c'] > last['o'])
    except: return None, 0, False

# --- 4. EXECUÇÃO DE ORDENS COM PRECISÃO ---
def open_position(side, pair, leverage, compound):
    try:
        symbol = f"{pair.split('/')[0]}/USDT:USDT"
        mexc.load_markets()
        market = mexc.market(symbol)
        
        mexc.set_leverage(int(leverage), symbol)
        
        bal = mexc.fetch_balance({'type': 'swap'})
        free_margin = float(bal['USDT']['free'])
        trade_amount = free_margin * (compound / 100)
        
        ticker = mexc.fetch_ticker(symbol)
        # Cálculo de quantidade respeitando o custo mínimo de contrato
        qty_raw = (trade_amount * leverage) / ticker['last']
        
        # FIX DE PRECISÃO: Garante o mínimo de 1 contrato ou a precisão da moeda
        min_qty = market['limits']['amount']['min']
        qty = max(min_qty, float(mexc.amount_to_precision(symbol, qty_raw)))

        mexc.create_market_order(symbol, side, qty)
        return f"Ordem de {side.upper()} enviada: {qty} contratos."
    except Exception as e:
        return f"Erro na execução: {str(e)}"

# --- 5. INTERFACE DASHBOARD (O ESPELHO DA MEXC) ---
with st.sidebar:
    st.header("⚡ CONTROLE")
    asset = st.selectbox("PAR DE NEGOCIAÇÃO", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT"])
    lev = st.slider("ALAVANCAGEM", 1, 125, 100)
    comp = st.slider("COMPOUND %", 10, 100, 95)
    auto_trade = st.toggle("ATIVAR IA SCALPER")

st.title("QUANT-OS V49 // MONITOR PROFISSIONAL")

col_left, col_right = st.columns([2.5, 1])

with col_right:
    st.subheader("📊 Posições Ativas")
    @st.fragment(run_every=1)
    def update_mirror():
        sym_f = f"{asset.split('/')[0]}/USDT:USDT"
        try:
            # Dados da Posição
            pos = mexc.fetch_positions([sym_f])
            active = [p for p in pos if float(p['contracts']) > 0]
            
            # Dados da Carteira
            bal = mexc.fetch_balance({'type': 'swap'})
            total_wallet = bal['USDT']['total']
            
            st.markdown(f"<div class='mexc-card'><span class='text-gray'>Saldo Total</span><br><span style='font-size:20px; font-weight:bold;'>{total_wallet:,.4f} USDT</span></div>", unsafe_allow_html=True)

            if active:
                p = active[0]
                pnl = float(p['unrealizedPnl'])
                roe = float(p['percentage'])
                pnl_style = "pnl-green" if pnl >= 0 else "pnl-red"
                
                st.markdown(f"""
                <div class='mexc-card' style='margin-top:10px;'>
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='font-weight:bold;'>{asset} <span style='color:#00b464; font-size:10px;'>{p['side'].upper()} {lev}X</span></span>
                    </div>
                    <hr style='border: 0.1px solid #2b3036;'>
                    <div style='display:flex; justify-content:space-between;'>
                        <div><span class='text-gray'>Preço de Entrada</span><br><b>{p['entryPrice']}</b></div>
                        <div><span class='text-gray'>Preço Justo</span><br><b>{p['markPrice']}</b></div>
                    </div>
                    <div style='margin-top:10px;'>
                        <span class='text-gray'>PNL não realizado (USDT)</span><br>
                        <span class='{pnl_style}'>{pnl:+.4f} ({roe:+.2f}%)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Lógica de Fechamento Automático (Scalp por Vela)
                side, price, is_bullish = fetch_logic(sym_f)
                if (p['side'] == 'long' and not is_bullish) or (p['side'] == 'short' and is_bullish):
                    mexc.create_market_order(sym_f, 'sell' if p['side'] == 'long' else 'buy', p['contracts'])
                    st.toast("Saída automática executada para proteger o PNL!")
            else:
                st.info("Aguardando novo sinal de vela...")
                if auto_trade:
                    side, price, is_bull = fetch_logic(sym_f)
                    if side:
                        res = open_position(side, asset, lev, comp)
                        st.session_state.v49_log = res
                        st.toast(res)
        except Exception as e: st.error(f"Erro de Conexão: {e}")
    update_mirror()

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
    
    st.markdown("### 🖥️ Log de Execução")
    if 'v49_log' not in st.session_state: st.session_state.v49_log = "Sistema Pronto."
    st.markdown(f"<div class='terminal'>> {st.session_state.v49_log}</div>", unsafe_allow_html=True)
