import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

# Força o log imediato no Railway
sys.stdout.reconfigure(line_buffering=True)

class JordanSignalBot:
    def __init__(self, token, chat_id):
        self.exchange = ccxt.mexc()
        self.symbol = 'BTC/USDT:USDT'
        self.token = token
        self.chat_id = chat_id

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
        self.send_telegram("🚀 **SINALIZADOR JORDAN ELITE ONLINE**\nMonitorando BTC/USDT...")
        while True:
            try:
                df = self.get_data()
                if df is not None:
                    last = df.iloc[-1]
                    price = self.exchange.fetch_ticker(self.symbol)['last']
                    if (price > last['BBU']) and (last['RSI'] < 70):
                        self.send_telegram(f"🟢 **SINAL DE COMPRA BTC**\n💰 Preço: ${price:,.2f}")
                        time.sleep(900)
                    elif (price < last['BBL']) and (last['RSI'] > 30):
                        self.send_telegram(f"🔴 **SINAL DE VENDA BTC**\n💰 Preço: ${price:,.2f}")
                        time.sleep(900)
                print(f"[{time.strftime('%H:%M:%S')}] BTC: {price} | Aguardando...")
                time.sleep(30)
            except Exception as e:
                time.sleep(10)

if __name__ == "__main__":
    # Nomes ajustados conforme sua imagem do Railway
    t = os.getenv("TELEGRAM_TOKEN")
    c = os.getenv("CHAT_ID")
    
    if not t or not c:
        print(f"❌ ERRO: Variáveis faltando! Token: {'OK' if t else 'FALTA'}, ChatID: {'OK' if c else 'FALTA'}")
        sys.exit(1)
        
    JordanSignalBot(t, c).start()
