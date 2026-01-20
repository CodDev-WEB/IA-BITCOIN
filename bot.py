import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

class JordanEliteBot:
    def __init__(self, api_key, secret, telegram_token, chat_id):
        # 1. Configuração da Exchange
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'} 
        })
        
        # 2. DEFINIÇÃO DO PAR (Símbolo Nativo MEXC para Futuros)
        # O CCXT traduz BTC/USDT:USDT para o formato que a API precisa, 
        # mas forçaremos o mapeamento para evitar falhas de parâmetro.
        self.symbol = 'BTC_USDT' 
        self.mexc_native_symbol = 'BTC_USDT' # Usado em parâmetros específicos
        
        self.timeframe = '15m'
        self.leverage = 10           
        self.risk_per_trade = 0.01   
        
        # 3. Telemetria
        self.telegram_token = telegram_token
        self.chat_id = chat_id

    def notify(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": f"🤖 **JORDAN ELITE BOT**\n{message}", "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except:
            pass

    def apply_governance(self):
        """Aplica governança usando o mapeamento de símbolo explícito"""
        try:
            # Passamos o símbolo e a alavancagem de forma redundante
            self.exchange.set_margin_mode('ISOLATED', self.symbol, {'leverage': self.leverage})
            self.exchange.set_leverage(self.leverage, self.symbol)
            self.notify(f"✅ Governança Ativa: **{self.symbol} | {self.leverage}x**")
        except Exception as e:
            print(f"Aviso de Governança: {e}")

    def get_market_data(self):
        """Coleta dados e normaliza colunas"""
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        bbands = df.ta.bbands(length=20, std=2)
        rsi = df.ta.rsi(length=14)
        df = pd.concat([df, bbands, rsi], axis=1)
        
        new_cols = []
        for col in df.columns:
            if 'BBU' in col: new_cols.append('BBU')
            elif 'BBL' in col: new_cols.append('BBL')
            elif 'RSI' in col: new_cols.append('RSI')
            else: new_cols.append(col)
        df.columns = new_cols
        return df

    def calculate_position_size(self, price, stop_loss):
        try:
            balance = self.exchange.fetch_balance()
            # No Railway/MEXC v3, o saldo costuma estar em 'total' ou 'free'
            available = float(balance.get('USDT', {}).get('free', 0))
            if available == 0:
                # Fallback para estrutura alternativa de saldo
                available = float(balance.get('total', {}).get('USDT', 0))
            
            risk_amount = available * self.risk_per_trade
            price_var = abs(price - stop_loss)
            if price_var == 0: return 0
            size = risk_amount / price_var
            return min(size, (available * self.leverage * 0.9) / price)
        except:
            return 0

    def execute_logic(self):
        try:
            df = self.get_market_data()
            last, prev = df.iloc[-1], df.iloc[-2]
            price = self.exchange.fetch_ticker(self.symbol)['last']

            if (prev['close'] > prev['BBU']) and (last['RSI'] < 70):
                self.open_position('buy', price)
            elif (prev['close'] < prev['BBL']) and (last['RSI'] > 30):
                self.open_position('sell', price)
        except Exception as e:
            print(f"Erro na lógica: {e}")

    def open_position(self, side, price):
        sl_pct = 0.015
        sl = price * (1 - sl_pct) if side == 'buy' else price * (1 + sl_pct)
        tp = price * (1 + sl_pct * 2) if side == 'buy' else price * (1 - sl_pct * 2)
        lot = self.calculate_position_size(price, sl)
        
        if lot > 0:
            try:
                # Criando a ordem com parâmetros explícitos de símbolo para a MEXC
                self.exchange.create_order(
                    symbol=self.symbol, 
                    type='market', 
                    side=side, 
                    amount=lot,
                    params={
                        'stopLossPrice': sl, 
                        'takeProfitPrice': tp,
                        'symbol': self.mexc_native_symbol # Injeção forçada do símbolo nativo
                    }
                )
                self.notify(f"🚀 **ORDEM EXECUTADA**\n🔹 {side.upper()} BTC\n🔹 Lote: {lot:.4f}")
            except Exception as e:
                self.notify(f"❌ Erro ao abrir: {e}")

    def run(self):
        self.notify("⚡ **Jordan Elite Bot Ativado**")
        self.apply_governance()
        while True:
            try:
                # O PONTO CRÍTICO: Usamos fetch_positions com o símbolo exato esperado
                # Algumas versões da API da MEXC exigem o par sem o ":USDT"
                pos = self.exchange.fetch_positions(params={'symbol': self.mexc_native_symbol})
                
                has_pos = False
                if pos:
                    for p in pos:
                        if p['symbol'] == self.symbol or p['symbol'] == self.mexc_native_symbol:
                            if float(p.get('contracts', 0)) > 0:
                                has_pos = True
                                break

                if not has_pos:
                    self.execute_logic()
                
                time.sleep(60) 
            except Exception as e:
                print(f"Erro de Conexão/Parâmetro: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = JordanEliteBot(
        os.getenv("MEXC_API_KEY"),
        os.getenv("MEXC_SECRET"),
        os.getenv("TELEGRAM_TOKEN"),
        os.getenv("TELEGRAM_CHAT_ID")
    )
    bot.run()
