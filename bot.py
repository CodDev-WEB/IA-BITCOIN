import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

# Log em tempo real para o Railway
sys.stdout.reconfigure(line_buffering=True)

class JordanSignalBot:
    def __init__(self, token, chat_id):
        self.exchange = ccxt.mexc()
        self.symbol = 'BTC/USDT:USDT'
        self.token = token
        self.chat_id = chat_id
        # --- CONFIGURAÇÃO DE ALAVANCAGEM ---
        self.leverage = 10  # Exemplo: 10x
        self.target_roe = 0.20 # 20% de lucro/perda na operação

    def send_telegram(self, msg):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Erro Telegram: {e}")

    def get_data(self):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, '15m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.rsi(length=14, append=True)
            df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
            return df
        except: return None

    def start(self):
        print(f">>> Monitorando BTC com Alavancagem de {self.leverage}x para ROE de 20%")
        self.send_telegram(f"🚀 **JORDAN ELITE V5 ONLINE**\nFoco: Futuros (PNL 20%)\nAlavancagem Base: {self.leverage}x")
        
        while True:
            try:
                df = self.get_data()
                if df is not None:
                    last = df.iloc[-1]
                    price = self.exchange.fetch_ticker(self.symbol)['last']
                    
                    # Cálculo da variação necessária no preço (Price Move)
                    # Se ROE = 20% e Lev = 10x, move_needed = 0.02 (2%)
                    move_needed = self.target_roe / self.leverage
                    
                    # --- LÓGICA LONG ---
                    if (price > last['BBU']) and (last['RSI'] < 70):
                        tp = price * (1 + move_needed)
                        sl = price * (1 - move_needed)
                        msg = (f"🟢 **SINAL LONG (FUTUROS)**\n\n"
                               f"📥 **Entrada:** ${price:,.2f}\n"
                               f"Leverage Sugerida: {self.leverage}x\n\n"
                               f"🎯 **Saída Lucro (+20% PNL):** ${tp:,.2f}\n"
                               f"🚫 **Saída Stop (-20% PNL):** ${sl:,.2f}\n\n"
                               f"📊 RSI: {last['RSI']:.2f}")
                        self.send_telegram(msg)
                        time.sleep(900)
                        
                    # --- LÓGICA SHORT ---
                    elif (price < last['BBL']) and (last['RSI'] > 30):
                        tp = price * (1 - move_needed)
                        sl = price * (1 + move_needed)
                        msg = (f"🔴 **SINAL SHORT (FUTUROS)**\n\n"
                               f"📥 **Entrada:** ${price:,.2f}\n"
                               f"Leverage Sugerida: {self.leverage}x\n\n"
                               f"🎯 **Saída Lucro (+20% PNL):** ${tp:,.2f}\n"
                               f"🚫 **Saída Stop (-20% PNL):** ${sl:,.2f}\n\n"
                               f"📊 RSI: {last['RSI']:.2f}")
                        self.send_telegram(msg)
                        time.sleep(900)
                        
                print(f"[{time.strftime('%H:%M:%S')}] BTC: {price} | ROE Alvo: 20%", end='\r')
                time.sleep(30)
            except Exception as e:
                time.sleep(10)

if __name__ == "__main__":
    t = os.getenv("TELEGRAM_TOKEN")
    c = os.getenv("CHAT_ID")
    if t and c:
        JordanSignalBot(t, c).start()
