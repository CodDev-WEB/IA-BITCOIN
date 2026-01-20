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
        
        # DEFINIÇÃO ABSOLUTA DOS SÍMBOLOS
        self.symbol = 'BTC/USDT:USDT'    # Formato para OHLCV (CCXT)
        self.mexc_symbol = 'BTC_USDT'    # Formato Nativo para Ordens (MEXC)
        
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
        """Aplica governança ignorando erros se já estiver configurado"""
        try:
            # Forçamos a alavancagem primeiro, pois a MEXC exige isso para validar a margem
            self.exchange.set_leverage(self.leverage, self.symbol, {'symbol': self.mexc_symbol})
            
            # Tentamos a margem isolada injetando o símbolo nativo
            self.exchange.set_margin_mode('ISOLATED', self.symbol, {
                'leverage': self.leverage,
                'symbol': self.mexc_symbol
            })
            self.notify(f"✅ Governança MEXC Ativa: **{self.mexc_symbol} | {self.leverage}x**")
        except Exception as e:
            # Se der erro aqui, apenas logamos e seguimos, pois o bot pode operar com a config manual da conta
            print(f"Aviso de Governança (Seguindo adiante): {e}")

    def get_market_data(self):
        """Coleta dados sem depender de parâmetros extras"""
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, '15m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Indicadores
        bbands = df.ta.bbands(length=20, std=2)
        rsi = df.ta.rsi(length=14)
        df = pd.concat([df, bbands, rsi], axis=1)
        
        # Limpeza de colunas (BBU, BBL, RSI)
        df.columns = [c.split('_')[0] if any(x in c for x in ['BBU', 'BBL', 'RSI']) else c for c in df.columns]
        return df

    def run(self):
        self.notify("⚡ **Sistema Reiniciado: Protocolo de Injeção Direta**")
        self.apply_governance()
        
        while True:
            try:
                # CORREÇÃO DEFINITIVA PARA O ERRO 600
                # Usamos um endpoint mais simples e injetamos o símbolo nativo manualmente no dicionário de parâmetros
                params = {'symbol': self.mexc_symbol}
                
                # Chamada direta para posições de futuros
                positions = self.exchange.fetch_positions(None, params)
                
                has_pos = False
                if positions:
                    for p in positions:
                        # Verificamos se o símbolo bate E se há contratos abertos
                        if p.get('symbol') == self.symbol or p.get('info', {}).get('symbol') == self.mexc_symbol:
                            if float(p.get('contracts', 0)) > 0:
                                has_pos = True
                                break

                if not has_pos:
                    df = self.get_market_data()
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    price = self.exchange.fetch_ticker(self.symbol)['last']

                    # Estratégia
                    if (prev['close'] > prev['BBU']) and (last['RSI'] < 70):
                        self.execute_trade('buy', price)
                    elif (prev['close'] < prev['BBL']) and (last['RSI'] > 30):
                        self.execute_trade('sell', price)
                
                time.sleep(60)
            except Exception as e:
                # Se o erro 600 aparecer aqui, ele será printado, mas o bot não morre
                print(f"Monitoramento: {e}")
                time.sleep(30)

    def execute_trade(self, side, price):
        """Execução de ordem com injeção de parâmetros nativos"""
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

if __name__ == "__main__":
    bot = JordanEliteBot(
        os.getenv("MEXC_API_KEY"),
        os.getenv("MEXC_SECRET"),
        os.getenv("TELEGRAM_TOKEN"),
        os.getenv("TELEGRAM_CHAT_ID")
    )
    bot.run()
