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
        
        # Sincronização de Símbolos
        self.symbol = 'BTC/USDT:USDT' 
        self.mexc_symbol = 'BTC_USDT' 
        
        self.leverage = 10
        self.risk_per_trade = 0.01
        self.telegram_token = telegram_token
        self.chat_id = chat_id

    def notify(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": f"🤖 **JORDAN ELITE BOT**\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, json=payload, timeout=5)
        except: pass

    def apply_governance(self):
        """Correção Crítica: Passando leverage como parâmetro nomeado para a MEXC"""
        try:
            # A MEXC v3 exige o parâmetro 'leverage' dentro de um dicionário extra
            self.exchange.set_margin_mode('ISOLATED', self.symbol, {
                'leverage': self.leverage,
                'symbol': self.mexc_symbol
            })
            # Reforça a alavancagem separadamente por segurança
            self.exchange.set_leverage(self.leverage, self.symbol, {'symbol': self.mexc_symbol})
            self.notify(f"✅ Governança MEXC Ativa: **{self.mexc_symbol} | {self.leverage}x**")
        except Exception as e:
            print(f"Nota de Governança: {e}")
            # Se já estiver configurado, o bot segue em frente

    def get_market_data(self):
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, '15m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Análise Técnica
        bbands = df.ta.bbands(length=20, std=2)
        rsi = df.ta.rsi(length=14)
        df = pd.concat([df, bbands, rsi], axis=1)
        
        # Limpeza de nomes de colunas
        df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
        return df

    def open_position(self, side, price):
        """Execução direta no servidor da MEXC"""
        sl = price * 0.985 if side == 'buy' else price * 1.015
        tp = price * 1.03 if side == 'buy' else price * 0.97
        
        try:
            balance = self.exchange.fetch_balance()
            available = float(balance.get('USDT', {}).get('free', 0))
            lot = (available * self.risk_per_trade * self.leverage) / price

            if lot > 0:
                self.exchange.create_order(
                    symbol=self.symbol,
                    type='market',
                    side=side,
                    amount=lot,
                    params={
                        'symbol': self.mexc_symbol,
                        'stopLossPrice': sl,
                        'takeProfitPrice': tp
                    }
                )
                self.notify(f"🚀 **ORDEM EXECUTADA**\n🔹 {side.upper()} {self.mexc_symbol}\n🔹 Lote: {lot:.4f}")
        except Exception as e:
            self.notify(f"❌ Erro na execução: {e}")

    def run(self):
        self.notify("⚡ **Sistema Iniciado: Modo de Alta Compatibilidade**")
        self.apply_governance()
        while True:
            try:
                # Verificação de posição com parâmetro nativo para evitar Erro 600
                positions = self.exchange.fetch_positions(params={'symbol': self.mexc_symbol})
                
                has_pos = False
                if positions:
                    active = [p for p in positions if float(p.get('contracts', 0)) > 0]
                    if active: has_pos = True

                if not has_pos:
                    df = self.get_market_data()
                    last, prev = df.iloc[-1], df.iloc[-2]
                    price = self.exchange.fetch_ticker(self.symbol)['last']

                    if (prev['close'] > prev['BBU']) and (last['RSI'] < 70):
                        self.open_position('buy', price)
                    elif (prev['close'] < prev['BBL']) and (last['RSI'] > 30):
                        self.open_position('sell', price)
                
                time.sleep(60)
            except Exception as e:
                print(f"Erro no monitoramento: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = JordanEliteBot(
        os.getenv("MEXC_API_KEY"),
        os.getenv("MEXC_SECRET"),
        os.getenv("TELEGRAM_TOKEN"),
        os.getenv("TELEGRAM_CHAT_ID")
    )
    bot.run()
