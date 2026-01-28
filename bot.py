import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys
from google import genai # Nova SDK Oficial

# Sincronização de logs para o Railway
sys.stdout.reconfigure(line_buffering=True)

class JordanEliteAI:
    def __init__(self, token, chat_id):
        # Conexão MEXC (Apenas leitura para sinais)
        self.exchange = ccxt.mexc()
        self.symbol = 'BTC/USDT:USDT'
        self.token = token
        self.chat_id = chat_id
        
        # Configurações de Risco
        self.leverage = 200 
        self.target_roe = 0.20 # Meta de 20% de lucro/perda na operação
        
        # Inicializa Nova SDK Gemini
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.bot_name = "JORDAN ELITE v8.5"

    def send_telegram(self, msg):
        """Sistema de Notificações via Telegram"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Erro de conexão Telegram: {e}")

    def ask_gemini(self, df, price, side):
        """O cérebro do Bot: Análise de contexto via IA"""
        try:
            # Prepara os dados técnicos para a IA
            recent_data = df.tail(10)[['close', 'RSI', 'BBU', 'BBL']].to_string()
            prompt = (
                f"Você é um analista de Scalping de alta precisão.\n"
                f"Cenário: BTC/USDT em 1 minuto com alavancagem de 200x.\n"
                f"Sinal Técnico: {side} a ${price:,.2f}\n"
                f"Dados Recentes:\n{recent_data}\n"
                f"Sua missão: Verifique se há força para buscar 0.1% de lucro (20% ROE) sem ser stopado.\n"
                f"Responda 'APROVADO' ou 'NEGADO' e uma justificativa curta."
            )
            response = self.client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"APROVADO (Erro técnico na IA, valide o gráfico manualmente: {e})"

    def start(self):
        # Notificação de Status: LIGADO
        start_msg = (f"✅ **{self.bot_name} ONLINE**\n"
                     f"📈 Ativo: BTC/USDT (Futuros)\n"
                     f"🚀 Alavancagem: {self.leverage}x\n"
                     f"🎯 Alvo ROE: 20%\n"
                     f"⏱️ Gráfico: 1 Minuto")
        self.send_telegram(start_msg)
        print(f">>> {self.bot_name} em execução...")

        while True:
            try:
                # 1. Busca Dados (OHLCV)
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, '1m', limit=50)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # 2. Calcula Indicadores
                df.ta.bbands(append=True)
                df.ta.rsi(append=True)
                df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
                
                last = df.iloc[-1]
                price = self.exchange.fetch_ticker(self.symbol)['last']
                
                # Variação necessária para 20% de PNL em 200x (0.1%)
                price_change = self.target_roe / self.leverage 

                # 3. Lógica de Gatilho
                side = None
                if (price > last['BBU']) and (last['RSI'] < 70):
                    side = "LONG 🟢"
                elif (price < last['BBL']) and (last['RSI'] > 30):
                    side = "SHORT 🔴"

                if side:
                    # 4. Filtro de Inteligência Artificial
                    verdict = self.ask_gemini(df, price, side)
                    
                    if "APROVADO" in verdict:
                        # Cálculo de Saída
                        if "LONG" in side:
                            tp = price * (1 + price_change)
                            sl = price * (1 - price_change)
                        else:
                            tp = price * (1 - price_change)
                            sl = price * (1 + price_change)
                        
                        msg = (f"🔥 **NOVA OPORTUNIDADE (200x)** 🔥\n\n"
                               f"📟 Operação: {side}\n"
                               f"📥 Entrada: ${price:,.2f}\n"
                               f"🎯 Take Profit (20%): ${tp:,.2f}\n"
                               f"🚫 Stop Loss (20%): ${sl:,.2f}\n\n"
                               f"🧠 **Análise Gemini:**\n{verdict}")
                        self.send_telegram(msg)
                        time.sleep(60) # Evita múltiplos sinais no mesmo minuto

                # Delay de monitoramento
                print(f"[{time.strftime('%H:%M:%S')}] BTC: ${price:,.2f} | Monitorando...", end='\r')
                time.sleep(10) 

            except Exception as e:
                # Notificação de Erro e Auto-Restart
                error_msg = f"⚠️ **{self.bot_name} ALERT**\nErro detectado: `{str(e)[:100]}`\nReiniciando em 30s..."
                self.send_telegram(error_msg)
                time.sleep(30)

if __name__ == "__main__":
    # Carrega variáveis do Railway
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    
    if token and chat_id:
        bot = JordanEliteAI(token, chat_id)
        bot.start()
    else:
        print("❌ ERRO: Variáveis de ambiente faltando!")
