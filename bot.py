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
        
        # Inicializa cliente com a versão estável da API
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.bot_name = "JORDAN ELITE v9.0"

    def send_telegram(self, msg):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Erro Telegram: {e}")

    def ask_gemini(self, df, price, side):
        """Analisa o cenário real. Só aprova se houver alta probabilidade."""
        try:
            recent_data = df.tail(10)[['close', 'RSI', 'BBU', 'BBL']].to_string()
            prompt = (
                f"Analise Scalp de 200x para BTC. Direção: {side}. Preço: {price}.\n"
                f"Dados (1min):\n{recent_data}\n"
                f"O RSI e as Bandas suportam um alvo de 0.1% agora? "
                f"Responda 'APROVADO' ou 'NEGADO' e o motivo curto."
            )
            # Correção do modelo para evitar o erro 404
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp", # Usando a versão mais atual e estável
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Erro IA: {e}")
            return f"ERRO NA ANÁLISE: {str(e)[:50]}"

    def start(self):
        # Notificação de Inicialização
        self.send_telegram(f"✅ **{self.bot_name} INICIALIZADO**\n🚀 Alavancagem: {self.leverage}x\n⏱️ Monitorando 1min...")
        print(f">>> {self.bot_name} rodando...")

        while True:
            try:
                # Coleta e Processamento
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, '1m', limit=50)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df.ta.bbands(append=True)
                df.ta.rsi(append=True)
                df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
                
                last = df.iloc[-1]
                price = self.exchange.fetch_ticker(self.symbol)['last']
                price_move = self.target_roe / self.leverage 

                # Gatilhos Técnicos
                side = None
                if (price > last['BBU']) and (last['RSI'] < 70): side = "LONG 🟢"
                elif (price < last['BBL']) and (last['RSI'] > 30): side = "SHORT 🔴"

                if side:
                    print(f"[{time.strftime('%H:%M:%S')}] Analisando {side} com Gemini...")
                    verdict = self.ask_gemini(df, price, side)
                    
                    if "APROVADO" in verdict:
                        tp = price * (1 + price_move) if "LONG" in side else price * (1 - price_move)
                        sl = price * (1 - price_move) if "LONG" in side else price * (1 + price_move)
                        
                        msg = (f"🔥 **OPORTUNIDADE REAL (200x)** 🔥\n\n"
                               f"📟 Operação: {side}\n"
                               f"📥 Entrada: ${price:,.2f}\n"
                               f"🎯 Take Profit: ${tp:,.2f}\n"
                               f"🚫 Stop Loss: ${sl:,.2f}\n\n"
                               f"🧠 **Veredito IA:**\n{verdict}")
                        self.send_telegram(msg)
                        time.sleep(60)
                
                time.sleep(10) 

            except Exception as e:
                # Alerta de Falha
                print(f"Erro: {e}")
                self.send_telegram(f"⚠️ **ALERTA DE SISTEMA**\nErro no loop: `{str(e)[:100]}`\nTentando reconectar...")
                time.sleep(30)

if __name__ == "__main__":
    t = os.getenv("TELEGRAM_TOKEN")
    c = os.getenv("CHAT_ID")
    if t and c:
        JordanEliteAI(t, c).start()
