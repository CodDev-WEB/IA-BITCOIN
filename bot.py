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
        print(">>> Conectando Sistema Multi-Métricas V2...")
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
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            res = requests.post(url, json={"chat_id": self.chat_id, "text": f"🤖 {message}"}, timeout=10)
            if res.status_code != 200:
                print(f"❌ Erro Telegram: {res.text}")
        except Exception as e:
            print(f"❌ Falha de conexão Telegram: {e}")

    def get_data(self):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Indicadores sem renomear para evitar erro de ambiguidade
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.ema(length=9, append=True)
            df.ta.ema(length=21, append=True)
            df['vol_avg'] = df['volume'].rolling(window=20).mean()
            
            # Limpeza manual e segura das colunas
            df.columns = [c.replace('BBU_20_2.0', 'BBU').replace('BBL_20_2.0', 'BBL').replace('RSI_14', 'RSI') for c in df.columns]
            return df
        except Exception as e:
            print(f"Erro ao processar métricas: {e}")
            return None

    def execute(self, side, price):
        try:
            balance = self.exchange.fetch_balance()
            available = float(balance.get('USDT', {}).get('free', 0)) or float(balance.get('total', {}).get('USDT', 0))
            
            lot = (available * 0.50 * self.leverage) / price # 50% de banca
            tp = price * 1.015 if side == 'buy' else price * 0.985 # Alvo 15% (1.5% no preço)

            if lot > 0:
                self.exchange.create_order(
                    symbol=self.symbol, type='market', side=side, amount=lot,
                    params={'symbol': self.mexc_symbol, 'takeProfitPrice': tp}
                )
                self.notify(f"🚀 ENTRADA CONFIRMADA: {side.upper()}\n📈 Preço: {price}\n🎯 Alvo 15% Lucro: {tp:.2f}")
        except Exception as e:
            print(f"Erro na ordem: {e}")

    def run_loop(self):
        self.notify("SISTEMA MULTI-MÉTRICAS ONLINE 🚀")
        print(">>> Monitorando confluências de mercado...")
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
                        
                        # LOGICA DE CONFLUÊNCIA CORRIGIDA (EMA_9 vs EMA_21)
                        # Compra: Preço acima das médias + Cruzamento de médias + Rompimento Banda + RSI ideal + Volume
                        buy_signal = (last['close'] > last['EMA_9']) and (last['EMA_9'] > last['EMA_21']) and \
                                     (prev['close'] > prev['BBU']) and (50 < last['RSI'] < 70) and \
                                     (last['volume'] > last['vol_avg'])

                        # Venda: Preço abaixo das médias + Médias invertidas + Rompimento Banda + RSI fraco + Volume
                        sell_signal = (last['close'] < last['EMA_9']) and (last['EMA_9'] < last['EMA_21']) and \
                                      (prev['close'] < prev['BBL']) and (30 < last['RSI'] < 50) and \
                                      (last['volume'] > last['vol_avg'])

                        if buy_signal: self.execute('buy', price)
                        elif sell_signal: self.execute('sell', price)
                
                time.sleep(30)
            except Exception as e:
                print(f"Erro no loop: {e}"); time.sleep(20)

if __name__ == "__main__":
    k, s, t, c = os.getenv("MEXC_API_KEY"), os.getenv("MEXC_SECRET"), os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if all([k, s, t, c]): JordanEliteBot(k, s, t, c).run_loop()
