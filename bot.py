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
        self.timeframe = '5m'  # ALTERADO PARA 5 MINUTOS
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.leverage = 10 

    def notify(self, message):
        print(f">>> Notificação: {message}")
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": f"🤖 {message}"}, timeout=5)
        except Exception as e:
            print(f"Erro Telegram: {e}")

    def get_data(self):
        try:
            # Busca velas de 5 minutos
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=50)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.rsi(length=14, append=True)
            
            new_cols = []
            for col in df.columns:
                if 'BBU' in col: new_cols.append('BBU')
                elif 'BBL' in col: new_cols.append('BBL')
                elif 'RSI' in col: new_cols.append('RSI')
                else: new_cols.append(col)
            df.columns = new_cols
            return df
        except Exception as e:
            print(f"Erro ao buscar dados: {e}")
            return None

    def execute(self, side, price):
        """Executa com 50% do saldo e alvo de 15% de lucro (1.5% no preço com 10x)"""
        try:
            balance = self.exchange.fetch_balance()
            available = float(balance.get('USDT', {}).get('free', 0))
            if available == 0:
                available = float(balance.get('total', {}).get('USDT', 0))
            
            # CONFIGURAÇÃO: 50% do saldo
            percent_to_use = 0.50 
            lot = (available * percent_to_use * self.leverage) / price
            
            # ALVO: 15% de lucro sobre a margem (1.5% de movimento no preço)
            profit_target = 0.015
            tp_price = price * (1 + profit_target) if side == 'buy' else price * (1 - profit_target)

            if lot > 0:
                self.exchange.create_order(
                    symbol=self.symbol, 
                    type='market', 
                    side=side, 
                    amount=lot,
                    params={
                        'symbol': self.mexc_symbol,
                        'takeProfitPrice': tp_price  # Saída automática no lucro
                    }
                )
                self.notify(f"🚀 ENTRADA AGRESSIVA (50% SALDO)\n🔹 Modo: {side.upper()} (5m)\n💰 Alvo Lucro (15%): {tp_price:.2f}")
            else:
                print(">>> Saldo insuficiente.")
        except Exception as e:
            self.notify(f"❌ Erro na execução: {e}")

    def run_loop(self):
        self.notify("JORDAN ELITE ATIVADO: 5m | 50% SALDO | 15% ALVO 🚀")
        while True:
            try:
                # Anti-Erro 600
                pos = self.exchange.fetch_positions(params={'symbol': self.mexc_symbol})
                has_pos = any(float(p.get('contracts', 0)) > 0 for p in pos) if pos else False
                
                if not has_pos:
                    df = self.get_data()
                    if df is not None:
                        last = df.iloc[-1]
                        prev = df.iloc[-2]
                        price = self.exchange.fetch_ticker(self.symbol)['last']
                        
                        # Estratégia Jordan Elite
                        if (prev['close'] > prev['BBU']) and (last['RSI'] < 70):
                            self.execute('buy', price)
                        elif (prev['close'] < prev['BBL']) and (last['RSI'] > 30):
                            self.execute('sell', price)
                
                print(f"[{time.strftime('%H:%M:%S')}] Monitorando 5m...")
                time.sleep(30) # Verificação mais rápida para gráfico de 5m
            except Exception as e:
                print(f"Erro: {e}")
                time.sleep(20)

if __name__ == "__main__":
    k, s, t, c = os.getenv("MEXC_API_KEY"), os.getenv("MEXC_SECRET"), os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if all([k, s, t, c]):
        JordanEliteBot(k, s, t, c).run_loop()
    else:
        print("Variáveis faltando!")
