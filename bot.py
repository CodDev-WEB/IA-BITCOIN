import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys
from google import genai

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
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.bot_name = "JORDAN ELITE v8.5"

    def send_telegram(self, msg):
        """Central de notificações"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Erro ao contactar Telegram: {e}")

    def ask_gemini(self, df, price, side):
        try:
            recent_data = df.tail(10)[['close', 'RSI', 'BBU', 'BBL']].to_string()
            prompt = (
                f"Analise este Scalp de 200x para BTC.\nLado: {side}\nPreço: {price}\n"
                f"Dados recentes 1min:\n{recent_data}\n"
                f"Responda 'APROVADO' ou 'NEGADO' e o porquê em uma frase curta."
            )
            response = self.client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return response.text
        except Exception as e:
            return f"NEGADO (Erro na conexão com Gemini: {e})"

    def start(self):
        # NOTIFICAÇÃO DE INICIALIZAÇÃO
        start_msg = (f"✅ **{self.bot_name} LIGADO**\n"
                     f"🕒 Gráfico: 1 Minuto\n"
                     f"🚀 Alavancagem: {self.leverage}x\n"
                     f"🎯 Meta PNL: 20%\n"
                     f"🤖 Filtro IA: Ativo")
        self.send_telegram(start_msg)
        print(f">>> {self.bot_name} Online")

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
                    # Notificação de análise em curso (opcional, removido para evitar spam)
                    verdict = self.ask_gemini(df, price, side)
                    
                    if "APROVADO" in verdict:
                        tp = price * (1 + price_change) if "LONG" in side else price * (1 - price_change)
                        sl = price * (1 - price_change) if "LONG" in side else price * (1 + price_change)
                        
                        msg = (f"🔥 **ALVO DETECTADO** 🔥\n\n"
                               f"📟 Direção: {side}\n"
                               f"📥 Entrada: ${price:,.2f}\n"
                               f"🎯 Saída Lucro: ${tp:,.2f}\n"
                               f"🚫 Saída Stop: ${sl:,.2f}\n\n"
                               f"🧠 **IA:** {verdict}")
                        self.send_telegram(msg)
                        time.sleep(60)

                time.sleep(10) 

            except Exception as e:
                # NOTIFICAÇÃO DE ERRO/PARAGEM
                error_msg = f"⚠️ **{self.bot_name} ALERT**\nOcorreu um erro no loop: `{str(e)[:100]}`\nTentando reconectar em 30s..."
                self.send_telegram(error_msg)
                time.sleep(30)

if __name__ == "__main__":
    t = os.getenv("TELEGRAM_TOKEN")
    c = os.getenv("CHAT_ID")
    if t and c:
        JordanEliteAI(t, c).start()
