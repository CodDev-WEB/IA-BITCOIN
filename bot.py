import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys
from google import genai # Nova biblioteca oficial

# Sincronização de logs para o Railway
sys.stdout.reconfigure(line_buffering=True)

class JordanEliteAI:
    def __init__(self, token, chat_id):
        self.exchange = ccxt.mexc()
        self.symbol = 'BTC/USDT:USDT'
        self.token = token
        self.chat_id = chat_id
        self.leverage = 200 
        self.target_roe = 0.20 
        
        # Inicializa o cliente da nova SDK do Gemini
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def ask_gemini(self, df, price, side):
        """Filtro de inteligência usando a nova SDK google-genai"""
        try:
            recent_data = df.tail(10)[['close', 'RSI', 'BBU', 'BBL']].to_string()
            prompt = (
                f"Analise este Scalp de 200x para BTC.\nLado: {side}\nPreço: {price}\n"
                f"Dados recentes de 1min:\n{recent_data}\n"
                f"Responda apenas 'APROVADO' ou 'NEGADO' e uma justificativa curtíssima."
            )
            # Chamada otimizada para o modelo Flash
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"ERRO IA ({e}): Prosseguir com cautela."

    def send_signal(self, side, price, tp, sl, ai_verdict):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        msg = (f"🧠 **JORDAN ELITE AI v8.0 (200x)**\n\n"
               f"📟 **SINAL:** {side}\n"
               f"📥 **ENTRADA:** ${price:,.2f}\n\n"
               f"🎯 **TAKE PROFIT (SAÍDA 20%):** ${tp:,.2f}\n"
               f"🚫 **STOP LOSS (SAÍDA 20%):** ${sl:,.2f}\n\n"
               f"🤖 **ANÁLISE GEMINI:**\n{ai_verdict}")
        requests.post(url, json={"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"})

    def start(self):
        print(">>> Jordan Elite AI v8.0 Online - Nova SDK Google GenAI")
        while True:
            try:
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, '1m', limit=50)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df.ta.bbands(append=True)
                df.ta.rsi(append=True)
                df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
                
                last = df.iloc[-1]
                price = self.exchange.fetch_ticker(self.symbol)['last']
                price_change = self.target_roe / self.leverage 

                side = None
                if (price > last['BBU']) and (last['RSI'] < 70): side = "LONG 🟢"
                elif (price < last['BBL']) and (last['RSI'] > 30): side = "SHORT 🔴"

                if side:
                    verdict = self.ask_gemini(df, price, side)
                    if "APROVADO" in verdict:
                        if "LONG" in side:
                            tp = price * (1 + price_change)
                            sl = price * (1 - price_change)
                        else:
                            tp = price * (1 - price_change)
                            sl = price * (1 + price_change)
                        self.send_signal(side, price, tp, sl, verdict)
                        time.sleep(60)

                print(f"[{time.strftime('%H:%M:%S')}] BTC: {price} | Analisando com Gemini...", end='\r')
                time.sleep(10) 
            except Exception as e:
                print(f"Erro: {e}")
                time.sleep(5)

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    JordanEliteAI(token, chat_id).start()
