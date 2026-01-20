import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

sys.stdout.reconfigure(line_buffering=True)

class JordanEliteBot:
    def __init__(self, api_key, secret, telegram_token, chat_id):
        print(">>> Conectando Sistema Multi-Métricas...")
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        self.symbol = 'BTC/USDT:USDT'
        self.mexc_symbol = 'BTC_USDT'
        self.timeframe = '5m'
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.leverage = 10 

    def notify(self, message):
        """Notificação com Debug para garantir que chegue no seu Telegram"""
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            res = requests.post(url, json={"chat_id": self.chat_id, "text": f"🤖 {message}"}, timeout=10)
            if res.status_code == 200: print("✅ Notificação enviada.")
            else: print(f"❌ Erro Telegram: {res.text}")
        except: print("❌ Falha de conexão Telegram.")

    def get_data(self):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 1. Bandas de Bollinger (Volatilidade)
            df.ta.bbands(length=20, std=2, append=True)
            # 2. RSI (Momento)
            df.ta.rsi(length=14, append=True)
            # 3. EMAs (Tendência: Rápida 9 e Lenta 21)
            df.ta.ema(length=9, append=True)
            df.ta.ema(length=21, append=True)
            # 4. Média de Volume
            df['vol_avg'] = df['volume'].rolling(window=20).mean()
            
            # Normalizar nomes
            df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI', 'EMA']) else c for c in df.columns]
            return df
        except Exception as e:
            print(f"Erro dados: {e}")
            return None

    def execute(self, side, price):
        try:
            balance = self.exchange.fetch_balance()
            available = float(balance.get('USDT', {}).get('free', 0)) or float(balance.get('total', {}).get('USDT', 0))
            
            lot = (available * 0.50 * self.leverage) / price # 50% do Saldo
            
            # Alvo de 15% de lucro (1.5% no preço)
            tp = price * 1.015 if side == 'buy' else price * 0.985

            if lot > 0:
                self.exchange.create_order(
                    symbol=self.symbol, type='market', side=side, amount=lot,
                    params={'symbol': self.mexc_symbol, 'takeProfitPrice': tp}
                )
                self.notify(f"🚀 ENTRADA MULTI-MÉTRICA: {side.upper()}\n📈 Preço: {price}\n🎯 Alvo 15%: {tp:.2f}")
        except Exception as e:
            self.notify(f"❌ Erro Execução: {e}")

    def run_loop(self):
        self.notify("ESTRATÉGIA MULTI-INDICADORES ATIVA 🚀")
        while True:
            try:
                pos = self.exchange.fetch_positions(params={'symbol': self.mexc_symbol})
                has_pos = any(float(p.get('contracts', 0)) > 0 for p in pos) if pos else False
                
                if not has_pos:
                    df = self.get_data()
                    if df is not None:
                        last = df.iloc[-1]
                        prev = df.iloc[-2]
                        price = self.exchange.fetch_ticker(self.symbol)['last']
                        
                        # LÓGICA DE CONFLUÊNCIA (PRECISA DE TODOS OS SINAIS)
                        # COMPRA: Preço > EMA9 > EMA21 + Rompeu Banda Superior + RSI Forte + Volume Alto
                        buy_signal = (last['close'] > last['EMA']) and (last['EMA'] > df.iloc[-1]['EMA']) and \
                                     (prev['close'] > prev['BBU']) and (last['RSI'] > 50 and last['RSI'] < 70) and \
                                     (last['volume'] > last['vol_avg'])

                        # VENDA: Preço < EMA9 < EMA21 + Rompeu Banda Inferior + RSI Fraco + Volume Alto
                        sell_signal = (last['close'] < last['EMA']) and (last['EMA'] < df.iloc[-1]['EMA']) and \
                                      (prev['close'] < prev['BBL']) and (last['RSI'] < 50 and last['RSI'] > 30) and \
                                      (last['volume'] > last['vol_avg'])

                        if buy_signal: self.execute('buy', price)
                        elif sell_signal: self.execute('sell', price)
                
                print(f"[{time.strftime('%H:%M:%S')}] Analisando confluências...")
                time.sleep(30)
            except Exception as e:
                print(f"Erro: {e}"); time.sleep(20)

if __name__ == "__main__":
    k, s, t, c = os.getenv("MEXC_API_KEY"), os.getenv("MEXC_SECRET"), os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if all([k, s, t, c]): JordanEliteBot(k, s, t, c).run_loop()
