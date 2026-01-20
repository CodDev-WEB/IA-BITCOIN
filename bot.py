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
        
        # Símbolo unificado (CCXT) e Nativo (MEXC)
        self.symbol = 'BTC/USDT:USDT'
        self.mexc_symbol = 'BTC_USDT'
        
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.leverage = 10

    def notify(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": f"🤖 **JORDAN ELITE**\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, json=payload, timeout=5)
        except: pass

    def get_market_data(self):
        # Busca dados de mercado (OHLCV)
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, '15m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Indicadores
        bbands = df.ta.bbands(length=20, std=2)
        rsi = df.ta.rsi(length=14)
        df = pd.concat([df, bbands, rsi], axis=1)
        
        # Limpa nomes das colunas (Pega apenas o prefixo BBU, BBL, RSI)
        df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
        return df

    def run(self):
        self.notify("⚡ **Bot Iniciado**\nMonitorando BTC_USDT na MEXC.")
        
        while True:
            try:
                # SOLUÇÃO DEFINITIVA ERRO 600:
                # Chamamos o endpoint de posições passando o símbolo nativo diretamente nos parâmetros
                # Isso impede que o parâmetro 'symbol' vá nulo para a MEXC
                positions = self.exchange.fetch_positions(params={'symbol': self.mexc_symbol})
                
                has_pos = False
                if positions:
                    # Filtra apenas posições que realmente têm contratos abertos
                    active = [p for p in positions if float(p.get('contracts', 0)) > 0]
                    if active:
                        has_pos = True

                if not has_pos:
                    df = self.get_market_data()
                    last, prev = df.iloc[-1], df.iloc[-2]
                    price = self.exchange.fetch_ticker(self.symbol)['last']

                    # Estratégia de entrada
                    if (prev['close'] > prev['BBU']) and (last['RSI'] < 70):
                        self.execute_trade('buy', price)
                    elif (prev['close'] < prev['BBL']) and (last['RSI'] > 30):
                        self.execute_trade('sell', price)
                
                # Aguarda 60 segundos para a próxima verificação
                time.sleep(60)
                
            except Exception as e:
                print(f"Erro no monitoramento: {e}")
                time.sleep(30)

    def execute_trade(self, side, price):
        """Execução com injeção de parâmetros nativos"""
        try:
            balance = self.exchange.fetch_balance()
            available = float(balance.get('USDT', {}).get('free', 0))
            if available == 0:
                available = float(balance.get('total', {}).get('USDT', 0))
            
            # Cálculo de lote (1% de risco com 10x alavancagem)
            lot = (available * 0.01 * self.leverage) / price

            if lot > 0:
                # Envia ordem injetando o símbolo nativo no params
                self.exchange.create_order(
                    symbol=self.symbol,
                    type='market',
                    side=side,
                    amount=lot,
                    params={'symbol': self.mexc_symbol}
                )
                self.notify(f"🚀 **ORDEM EXECUTADA**\n🔹 {side.upper()} BTC\n🔹 Preço: {price}")
        except Exception as e:
            self.notify(f"❌ Falha na execução: {e}")

if __name__ == "__main__":
    # Carrega variáveis do Railway
    bot = JordanEliteBot(
        os.getenv("MEXC_API_KEY"),
        os.getenv("MEXC_SECRET"),
        os.getenv("TELEGRAM_TOKEN"),
        os.getenv("TELEGRAM_CHAT_ID")
    )
    bot.run()
