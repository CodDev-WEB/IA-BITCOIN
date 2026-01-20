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
        print(">>> Iniciando Sistema Multi-Métricas V2...")
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        self.symbol, self.mexc_symbol = 'BTC/USDT:USDT', 'BTC_USDT'
        self.telegram_token, self.chat_id = telegram_token, chat_id
        self.leverage = 10 

    def notify(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            res = requests.post(url, json={"chat_id": self.chat_id, "text": f"🤖 {message}"}, timeout=10)
            if res.status_code != 200: print(f"❌ Erro Telegram: {res.text}")
        except: print("❌ Falha de conexão Telegram.")

    def get_data(self):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, '5m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Adicionando Indicadores
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.ema(length=9, append=True)
            df.ta.ema(length=21, append=True)
            df['vol_avg'] = df['volume'].rolling(window=20).mean()
            
            # MAPEAMENTO SEGURO DE COLUNAS (Resolve o erro 'BBU' e KeyError)
            # Procuramos as colunas que contenham o nome, independente dos sufixos da biblioteca
            cols = {
                'BBU': [c for c in df.columns if 'BBU' in c][0],
                'BBL': [c for c in df.columns if 'BBL' in c][0],
                'RSI': [c for c in df.columns if 'RSI' in c][0],
                'EMA9': [c for c in df.columns if 'EMA_9' in c][0],
                'EMA21': [c for c in df.columns if 'EMA_21' in c][0]
            }
            return df, cols
        except Exception as e:
            print(f"Erro no processamento de dados: {e}")
            return None, None

    def execute(self, side, price):
        try:
            balance = self.exchange.fetch_balance()
            available = float(balance.get('USDT', {}).get('free', 0)) or float(balance.get('total', {}).get('USDT', 0))
            
            # 50% da banca com 10x alavancagem
            lot = (available * 0.50 * self.leverage) / price
            # Alvo de 15% de lucro (1.5% no preço)
            tp = price * 1.015 if side == 'buy' else price * 0.985

            if lot > 0:
                self.exchange.create_order(
                    symbol=self.symbol, type='market', side=side, amount=lot,
                    params={'symbol': self.mexc_symbol, 'takeProfitPrice': tp}
                )
                self.notify(f"🚀 ENTRADA FORTE: {side.upper()}\n📈 Preço: {price}\n🎯 Alvo Lucro: {tp:.2f}")
        except Exception as e:
            print(f"Erro na execução: {e}")

    def run_loop(self):
        self.notify("SISTEMA MULTI-MÉTRICAS ONLINE 🚀")
        while True:
            try:
                # Anti-Erro 600 na MEXC
                pos = self.exchange.fetch_positions(params={'symbol': self.mexc_symbol})
                has_pos = any(float(p.get('contracts', 0)) > 0 for p in pos) if pos else False
                
                if not has_pos:
                    df, c = self.get_data()
                    if df is not None:
                        last, prev = df.iloc[-1], df.iloc[-2]
                        price = self.exchange.fetch_ticker(self.symbol)['last']
                        
                        # LÓGICA DE CONFLUÊNCIA (EMA + BB + RSI + VOLUME)
                        # Compra: Preço > EMA9 > EMA21 E rompimento de Banda E RSI entre 50-70 E Volume acima da média
                        buy = (last['close'] > last[c['EMA9']]) and (last[c['EMA9']] > last[c['EMA21']]) and \
                              (prev['close'] > prev[c['BBU']]) and (50 < last[c['RSI']] < 70) and \
                              (last['volume'] > last['vol_avg'])

                        # Venda: Preço < EMA9 < EMA21 E rompimento de Banda E RSI entre 30-50 E Volume acima da média
                        sell = (last['close'] < last[c['EMA9']]) and (last[c['EMA9']] < last[c['EMA21']]) and \
                               (prev['close'] < prev[c['BBL']]) and (30 < last[c['RSI']] < 50) and \
                               (last['volume'] > last['vol_avg'])

                        if buy: self.execute('buy', price)
                        elif sell: self.execute('sell', price)
                
                print(f"[{time.strftime('%H:%M:%S')}] Analisando confluências de 5m...")
                time.sleep(30)
            except Exception as e:
                print(f"Erro no monitoramento: {e}"); time.sleep(20)
                
        # No final do seu arquivo bot.py
if __name__ == "__main__":
    # O bot pega as chaves que você salvou nas variáveis do Railway
    k = os.getenv("MEXC_API_KEY")
    s = os.getenv("MEXC_SECRET")
    t = os.getenv("TELEGRAM_TOKEN")
    c = os.getenv("CHAT_ID") # Certifique-se que no Railway o nome é CHAT_ID ou TELEGRAM_CHAT_ID
    
    if all([k, s, t, c]):
        JordanEliteBot(k, s, t, c).run_loop()
