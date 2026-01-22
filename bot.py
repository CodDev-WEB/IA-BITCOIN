import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

# Garante que o log no Railway seja atualizado em tempo real
sys.stdout.reconfigure(line_buffering=True)

class JordanSignalBot:
    def __init__(self, telegram_token, chat_id):
        print(">>> Iniciando Monitor de Sinais (Modo Visualização)...")
        # Usamos CCXT apenas para leitura de dados (não precisa de API Key para isso)
        self.exchange = ccxt.mexc()
        self.symbol = 'BTC/USDT:USDT'
        self.telegram_token = telegram_token
        self.chat_id = chat_id

    def send_signal(self, side, price, rsi, bbu, bbl):
        """Formata e envia o sinal de trade para o Telegram"""
        
        # Cálculo de alvos (Exemplo: 1% de Stop e 2% de Lucro)
        stop_loss = price * 0.99 if side == 'COMPRA 🟢' else price * 1.01
        take_profit = price * 1.02 if side == 'COMPRA 🟢' else price * 0.98
        
        emoji = "🚀" if side == 'COMPRA 🟢' else "🔻"
        
        message = (
            f"{emoji} **SINAL DE ELITE DETECTADO** {emoji}\n\n"
            f"**Ativo:** BTC/USDT (Futuros)\n"
            f"**Ação:** {side}\n"
            f"**Preço de Entrada:** ${price:,.2f}\n\n"
            f"🚫 **Stop Loss:** ${stop_loss:,.2f}\n"
            f"🎯 **Take Profit:** ${take_profit:,.2f}\n\n"
            f"📊 **Indicadores:**\n"
            f"- RSI: {rsi:.2f}\n"
            f"- Banda Superior: ${bbu:,.2f}\n"
            f"- Banda Inferior: ${bbl:,.2f}\n\n"
            f"⚠️ *Este é um sinal automático. Valide antes de entrar.*"
        )
        
        print(f">>> Enviando Sinal: {side} @ {price}")
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
        except Exception as e:
            print(f"Erro ao enviar para Telegram: {e}")

    def get_market_data(self):
        """Busca e processa indicadores técnicos"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, '15m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Bandas de Bollinger e RSI
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.rsi(length=14, append=True)
            
            # Limpeza dos nomes das colunas geradas pelo pandas_ta
            df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
            return df
        except Exception as e:
            print(f"Erro ao buscar dados: {e}")
            return None

    def run_monitor(self):
        print(">>> Bot Jordan Elite em modo MONITORAMENTO ativo.")
        ultimo_sinal_time = 0 # Evita spam de sinais repetidos no mesmo candle

        while True:
            try:
                df = self.get_market_data()
                if df is not None:
                    last = df.iloc[-1]
                    price = self.exchange.fetch_ticker(self.symbol)['last']
                    
                    # LOGICA DE SINAL
                    # Sinal de Compra: Preço cruza a Banda Superior e RSI não está exausto
                    if (price > last['BBU']) and (last['RSI'] < 70):
                        if time.time() - ultimo_sinal_time > 900: # 15 min de intervalo
                            self.send_signal('COMPRA 🟢', price, last['RSI'], last['BBU'], last['BBL'])
                            ultimo_sinal_time = time.time()

                    # Sinal de Venda: Preço cruza a Banda Inferior e RSI não está exausto
                    elif (price < last['BBL']) and (last['RSI'] > 30):
                        if time.time() - ultimo_sinal_time > 900:
                            self.send_signal('VENDA 🔴', price, last['RSI'], last['BBU'], last['BBL'])
                            ultimo_sinal_time = time.time()

                print(f"[{time.strftime('%H:%M:%S')}] BTC: ${price:,.2f} | RSI: {last['RSI']:.2f} | Aguardando...", end='\r')
                time.sleep(30)
            except Exception as e:
                print(f"\nErro no loop: {e}")
                time.sleep(10)

if __name__ == "__main__":
    # Para o Railway, você só precisa dessas duas variáveis agora
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    if not TOKEN or not CHAT_ID:
        print("❌ ERRO: Variáveis do Telegram não encontradas!")
        sys.exit(1)
        
    bot = JordanSignalBot(TOKEN, CHAT_ID)
    bot.run_monitor()
