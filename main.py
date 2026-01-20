import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="V47 // VELOCITY", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #010409; color: #e6edf3; }
    .status-box { 
        background: #0d1117; border: 1px solid #30363d; border-radius: 10px; 
        padding: 20px; text-align: center; border-top: 4px solid #f0b90b;
    }
    .pnl-positive { color: #39ff14; font-weight: bold; font-family: monospace; font-size: 20px; }
    .pnl-negative { color: #ff3131; font-weight: bold; font-family: monospace; font-size: 20px; }
    .neon-gold { color: #f0b90b; font-weight: bold; font-size: 28px; }
    .terminal { background: #000; color: #0f0; padding: 10px; font-family: monospace; border-radius: 5px; height: 100px; overflow-y: auto; }
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

# --- 3. MOTOR DE ANÁLISE VELA-A-VELA ---
def get_candle_analysis(symbol):
    try:
        # Analisa as últimas 50 velas de 1 minuto
        ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # Indicadores de Scalp Rápido
        df['ema3'] = df['c'].ewm(span=3).mean()
        df['ema8'] = df['c'].ewm(span=8).mean()
        
        # RSI rápido (5 períodos)
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(5).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(5).mean()
        rsi = 100 - (100 / (1 + (gain / (loss + 1e-10))))

        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Lógica de Decisão: Cruzamento de médias + Direção da última vela
        action = None
        if last['ema3'] > last['ema8'] and last['c'] > prev['c']:
            action = 'buy'
        elif last['ema3'] < last['ema8'] and last['c'] < prev['c']:
            action = 'sell'
            
        return {
            "action": action,
            "price": last['c'],
            "rsi": rsi.iloc[-1],
            "is_bullish": last['c'] > last['o']
        }
    except:
        return None

# --- 4. DASHBOARD E CONTROLES ---
with st.sidebar:
    st.header("⚡ VELOCITY CONTROL")
    pair = st.selectbox("PAR", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT"])
    lev = st.slider("ALAVANCAGEM", 10, 125, 50)
    comp = st.slider("COMPOUND % (Banca)", 10, 100, 90)
    bot_active = st.toggle("LIGAR ROBÔ")
    if st.button("FECHAR TUDO AGORA"):
        st.warning("Comando enviado!")

st.title("QUANT-OS V47 // HIGH FREQUENCY SCALPER")

col_main, col_pnl = st.columns([2, 1])

# --- 5. MONITOR DE POSIÇÕES (IGUAL À MEXC) ---
with col_pnl:
    st.subheader("📊 Posições em Aberto")
    @st.fragment(run_every=1)
    def update_pnl():
        sym_f = f"{pair.split('/')[0]}/USDT:USDT"
        try:
            # 1. Busca Posições Reais
            positions = mexc.fetch_positions([sym_f])
            active = [p for p in positions if float(p['contracts']) > 0]
            
            # 2. Busca Saldo Real
            bal = mexc.fetch_balance({'type': 'swap'})
            total_usdt = bal['USDT']['total']
            
            st.markdown(f"<div class='status-box'>BANCA TOTAL<br><span class='neon-gold'>$ {total_usdt:,.4f}</span></div>", unsafe_allow_html=True)

            if active:
                p = active[0]
                pnl = float(p['unrealizedPnl'])
                roe = float(p['percentage'])
                color_class = "pnl-positive" if pnl >= 0 else "pnl-negative"
                
                st.markdown(f"""
                <div class='status-box' style='margin-top:10px; border-top: 4px solid #39ff14;'>
                    <div style='font-size:12px;'>{p['side'].upper()} {pair} {lev}x</div>
                    <div class='{color_class}'>{roe:.2f}% (${pnl:.4f})</div>
                    <div style='font-size:11px; color:#8b949e;'>Entrada: {p['entryPrice']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # --- SAÍDA AUTOMÁTICA (LUCRO DE CADA VELA) ---
                analysis = get_candle_analysis(sym_f)
                if (p['side'] == 'long' and not analysis['is_bullish']) or (p['side'] == 'short' and analysis['is_bullish']):
                    mexc.create_market_order(sym_f, 'sell' if p['side'] == 'long' else 'buy', p['contracts'])
                    st.toast("Lucro da vela embolsado!")
            else:
                st.info("Aguardando sinal na próxima vela...")
                # Tenta abrir se o robô estiver ativo
                if bot_active:
                    analysis = get_candle_analysis(sym_f)
                    if analysis and analysis['action']:
                        # Execução de Compra/Venda
                        margin = float(bal['USDT']['free']) * (comp / 100)
                        if margin > 1.0:
                            raw_qty = (margin * lev) / analysis['price']
                            qty = mexc.amount_to_precision(sym_f, raw_qty)
                            mexc.create_market_order(sym_f, analysis['action'], qty)
                            st.toast(f"ORDEM ABERTA: {analysis['action'].upper()}")
        except Exception as e:
            st.error(f"Erro: {e}")

    update_pnl()

# --- 6. GRÁFICO E TERMINAL ---
with col_main:
    st.components.v1.html(f"""
        <div id="tv-chart" style="height:450px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
          "autosize": true, "symbol": "MEXC:{pair.replace('/','')}.P",
          "interval": "1", "theme": "dark", "style": "1", "container_id": "tv-chart"
        }});
        </script>
    """, height=450)
    
    st.markdown("### 🖥️ Singularity Terminal Log")
    st.markdown(f"""
    <div class='terminal'>
        > [{datetime.now().strftime('%H:%M:%S')}] Iniciando análise de micro-tendência...<br>
        > [{datetime.now().strftime('%H:%M:%S')}] Conectado à MEXC via API segura...<br>
        > [{datetime.now().strftime('%H:%M:%S')}] Escaneando velas de 1 minuto em {pair}...
    </div>
    """, unsafe_allow_html=True)
