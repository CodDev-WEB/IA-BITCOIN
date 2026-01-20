import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

# Força a saída de texto no log do Railway imediatamente
sys.stdout.reconfigure(line_buffering=True)

class JordanEliteBot:
    def __init__(self, api_key, secret, telegram_token, chat_id):
        print(">>> Iniciando conexão com a MEXC...")
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        self.symbol = 'BTC/USDT:USDT'
        self.mexc_symbol = 'BTC_USDT'
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.leverage = 10

    def notify(self, message):
        """Tenta enviar mensagem pro Telegram"""
        print(f">>> Notificação: {message}")
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": f"🤖 {message}"}, timeout=5)
        except Exception as e:
            print(f"Erro Telegram: {e}")

    def get_data(self):
        """Busca dados e calcula indicadores"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, '15m', limit=50)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Cálculo de Bandas e RSI
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.rsi(length=14, append=True)
            
            # Limpeza de nomes (Pega BBU, BBL, RSI)
            df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
            return df
        except Exception as e:
            print(f"Erro ao buscar dados: {e}")
            return None

    def run_loop(self):
        self.notify("JORDAN ELITE BOT ONLINE")
        print(">>> Loop de monitoramento iniciado.")
        
        while True:
            try:
                # 1. Verifica Posição (Anti-Erro 600)
                pos = self.exchange.fetch_positions(params={'symbol': self.mexc_symbol})
                has_pos = any(float(p.get('contracts', 0)) > 0 for p in pos) if pos else False
                
                if not has_pos:
                    df = self.get_data()
                    if df is not None:
                        last = df.iloc[-1]
                        prev = df.iloc[-2]
                        price = self.exchange.fetch_ticker(self.symbol)['last']
                        
                        # Lógica Simplificada
                        if (prev['close'] > prev['BBU']) and (last['RSI'] < 70):
                            self.execute('buy', price)
                        elif (prev['close'] < prev['BBL']) and (last['RSI'] > 30):
                            self.execute('sell', price)
                
                print(f"[{time.strftime('%H:%M:%S')}] Monitorando...")
                time.sleep(60)
            except Exception as e:
                print(f"Erro no loop: {e}")
                time.sleep(30)

    def execute(self, side, price):
        try:
            balance = self.exchange.fetch_balance()
            available = float(balance.get('USDT', {}).get('free', 0))
            lot = (available * 0.01 * self.leverage) / price
            
            if lot > 0:
                self.exchange.create_order(
                    symbol=self.symbol, type='market', side=side, amount=lot,
                    params={'symbol': self.mexc_symbol}
                )
                self.notify(f"ORDEM EXECUTADA: {side.upper()} BTC")
        except Exception as e:
            print(f"Erro execução: {e}")

if __name__ == "__main__":
    print("--- INICIANDO CONTAINER ---")
    k = os.getenv("MEXC_API_KEY")
    s = os.getenv("MEXC_SECRET")
    t = os.getenv("TELEGRAM_TOKEN")
    c = os.getenv("TELEGRAM_CHAT_ID")
    
    if not all([k, s, t, c]):
        print("ERRO: Faltam variáveis no Railway!")
        sys.exit(1)
        
    bot = JordanEliteBot(k, s, t, c)
    bot.run_loop()
