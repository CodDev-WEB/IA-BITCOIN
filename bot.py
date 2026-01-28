import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys
import google.generativeai as genai

# Sincronização de logs para o Railway
sys.stdout.reconfigure(line_buffering=True)

# Configuração da IA Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
ai_model = genai.GenerativeModel('gemini-1.5-flash')

class JordanEliteAI:
    def __init__(self, token, chat_id):
        self.exchange = ccxt.mexc()
        self.symbol = 'BTC/USDT:USDT'
        self.token = token
        self.chat_id = chat_id
        self.leverage = 200 
        self.target_roe = 0.20 # 20% de PNL

    def ask_gemini(self, df, price, side):
        """O Gemini analisa se o sinal técnico faz sentido no contexto atual"""
        try:
            # Pega os últimos 10 minutos para contexto
            recent_data = df.tail(10)[['close', 'RSI', 'BBU', 'BBL']].to_string()
            prompt = (
                f"Analise este Scalp de 200x para BTC.\n"
                f"Lado: {side}\nPreço: {price}\n"
                f"Dados (1min):\n{recent_data}\n"
                f"O RSI e a volatilidade suportam um ganho rápido de 0.1% (20% ROE)? "
                f"Responda apenas 'APROVADO' ou 'NEGADO' seguido de uma frase curta."
            )
            response = ai_model.generate_content(prompt)
            return response.text
        except: return "ERRO IA: Prosseguir com cautela."

    def send_signal(self, side, price, tp, sl, ai_verdict):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        msg = (f"🧠 **JORDAN ELITE AI (200x)**\n"
               f"Sinal: {side}\n"
               f"📥 Entrada: ${price:,.2f}\n"
               f"🎯 Take Profit (20%): ${tp:,.2f}\n"
               f"🚫 Stop Loss (20%): ${sl:,.2f}\n\n"
               f"🤖 **Veredito Gemini:**\n{ai_verdict}")
        requests.post(url, json={"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"})

    def start(self):
        print(">>> Jordan Elite AI Online - Modo 1min / 200x")
        while True:
            try:
                # Busca dados no tempo de 1 minuto (Necessário para 200x)
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, '1m', limit=50)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df.ta.bbands(append=True)
                df.ta.rsi(append=True)
                df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
                
                last = df.iloc[-1]
                price = self.exchange.fetch_ticker(self.symbol)['last']
                move = self.target_roe / self.leverage # 0.001 (0.1%)

                # Gatilho Técnico
                side = None
                if (price > last['BBU']) and (last['RSI'] < 70): side = "LONG 🟢"
                elif (price < last['BBL']) and (last['RSI'] > 30): side = "SHORT 🔴"

                if side:
                    # Filtro de Inteligência Artificial
                    verdict = self.ask_gemini(df, price, side)
                    if "APROVADO" in verdict:
                        tp = price * (1 + move) if "LONG" in side else price * (1 - move)
                        sl = price * (1 - move) if "LONG" in side else price * (1 + move)
                        self.send_signal(side, price, tp, sl, verdict)
                        time.sleep(60) # Pausa para não repetir no mesmo candle

                time.sleep(10) # Checa a cada 10 segundos
            except Exception as e:
                print(f"Erro: {e}")
                time.sleep(5)

if __name__ == "__main__":
    bot = JordanEliteAI(os.getenv("TELEGRAM_TOKEN"), os.getenv("CHAT_ID"))
    bot.start()
