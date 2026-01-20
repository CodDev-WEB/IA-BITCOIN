import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

class JordanEliteBot:
    def __init__(self, api_key, secret, telegram_token, chat_id):
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        
        self.symbol = 'BTC/USDT:USDT'
        self.mexc_symbol = 'BTC_USDT'
        self.timeframe = '15m'
        self.risk_per_trade = 0.01
        self.leverage = 10 # Apenas para cálculo de lote
        
        self.telegram_token = telegram_token
        self.chat_id = chat_id

    def notify(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": f"🤖 **JORDAN ELITE**\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, json=payload, timeout=5)
        except: pass

    def get_market_data(self):
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        bbands = df.ta.bbands(length=20, std=2)
        rsi = df.ta.rsi(length=14)
        df = pd.concat([df, bbands, rsi], axis=1)
        # Limpa nomes de colunas para garantir acesso simples
        df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
        return df

    def run(self):
        self.notify("⚡ **Bot Online (Modo Execução Pura)**\nConfiguração de Margem: Manual na MEXC.")
        
        while True:
            try:
                # Busca posições usando apenas o símbolo nativo para evitar erro 600
                params = {'symbol': self.mexc_symbol}
                positions = self.exchange.fetch_positions(params=params)
                
                has_pos = False
                if positions:
                    active = [p for p in positions if float(p.get('contracts', 0)) > 0]
                    if active: has_pos = True

                if not has_pos:
                    df = self.get_market_data()
                    last, prev = df.iloc[-1], df.iloc[-2]
                    price = self.exchange.fetch_ticker(self.symbol)['last']

                    # Lógica de entrada
                    if (prev['close'] > prev['BBU']) and (last['RSI'] < 70):
                        self.execute('buy', price)
                    elif (prev['close'] < prev['BBL']) and (last['RSI'] > 30):
                        self.execute('sell', price)
                
                time.sleep(60)
            except Exception as e:
                print(f"Erro no monitoramento: {e}")
                time.sleep(30)

    def execute(self, side, price):
        try:
            balance = self.exchange.fetch_balance()
            # Estrutura de saldo robusta para MEXC
            available = float(balance.get('USDT', {}).get('free', 0))
            if available == 0: available = float(balance.get('total', {}).get('USDT', 0))
            
            lot = (available * self.risk_per_trade * self.leverage) / price

            if lot > 0:
                # Ordem pura: Símbolo nativo injetado para evitar erro 600
                self.exchange.create_order(
                    symbol=self.symbol,
                    type='market',
                    side=side,
                    amount=lot,
                    params={'symbol': self.mexc_symbol}
                )
                self.notify(f"🚀 **ORDEM EXECUTADA**\n🔹 {side.upper()} BTC\n🔹 Lote: {lot:.4f}")
        except Exception as e:
            self.notify(f"❌ Erro ao executar: {e}")

if __name__ == "__main__":
    bot = JordanEliteBot(
        os.getenv("MEXC_API_KEY"),
        os.getenv("MEXC_SECRET"),
        os.getenv("TELEGRAM_TOKEN"),
        os.getenv("TELEGRAM_CHAT_ID")
    )
    bot.run()
