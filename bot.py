import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

# Garante que os logs apareçam em tempo real no Railway
sys.stdout.reconfigure(line_buffering=True)

class JordanEliteBot:
    def __init__(self, api_key, secret, telegram_token, chat_id):
        print(">>> 🚀 INICIANDO MASTER JORDAN ELITE V4 (LONG/SHORT + SL/TP)...")
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        self.symbol, self.mexc_symbol = 'BTC/USDT:USDT', 'BTC_USDT'
        self.telegram_token, self.chat_id = telegram_token, chat_id
        self.leverage = 10 
        
        # Variáveis de Relatório
        self.last_balance = 0
        self.daily_profit = 0
        self.trades_today = 0

    def notify(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            res = requests.post(url, json={"chat_id": self.chat_id, "text": f"🤖 {message}"}, timeout=10)
            if res.status_code != 200: print(f"❌ Erro Telegram: {res.text}")
        except: print("❌ Falha de conexão Telegram.")

    def get_balance(self):
        try:
            balance = self.exchange.fetch_balance()
            # Busca saldo disponível para Futuros
            return float(balance.get('USDT', {}).get('free', 0)) or float(balance.get('total', {}).get('USDT', 0))
        except: return 0

    def get_data(self):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, '5m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # --- ANÁLISE DE MÉTRICAS (EMA, BB, RSI) ---
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.ema(length=9, append=True)
            df.ta.ema(length=21, append=True)
            df['vol_avg'] = df['volume'].rolling(window=20).mean()
            
            # Mapeamento dinâmico para evitar erro 'BBU'
            cols = {
                'BBU': [c for c in df.columns if 'BBU' in c][0],
                'BBL': [c for c in df.columns if 'BBL' in c][0],
                'RSI': [c for c in df.columns if 'RSI' in c][0],
                'EMA9': [c for c in df.columns if 'EMA_9' in c][0],
                'EMA21': [c for c in df.columns if 'EMA_21' in c][0]
            }
            return df, cols
        except Exception as e:
            print(f"Erro na análise de métricas: {e}")
            return None, None

    def execute(self, side, price):
        try:
            current_balance = self.get_balance()
            self.last_balance = current_balance
            
            # 50% da banca com 10x alavancagem
            lot = (current_balance * 0.50 * self.leverage) / price
            
            # CONFIGURAÇÃO DE ALVOS (Preço)
            if side == 'buy':
                tp = price * 1.015  # Lucro de 15% (1.5% no movimento)
                sl = price * 0.950  # Perda Máxima de 5% no movimento (Stop Loss)
            else:
                tp = price * 0.985  # Lucro de 15% (1.5% no movimento)
                sl = price * 1.050  # Perda Máxima de 5% no movimento (Stop Loss)

            if lot > 0:
                self.exchange.create_order(
                    symbol=self.symbol, type='market', side=side, amount=lot,
                    params={'symbol': self.mexc_symbol, 'takeProfitPrice': tp, 'stopLossPrice': sl}
                )
                self.notify(f"🚀 ENTRADA: {side.upper()}\n📈 Preço: {price}\n🎯 Alvo (TP): {tp:.2f}\n🛡️ Seguro (SL): {sl:.2f}")
        except Exception as e:
            self.notify(f"❌ Falha ao executar trade: {e}")

    def monitor_exit(self):
        """Verifica se a posição fechou para gerar relatório"""
        try:
            pos = self.exchange.fetch_positions(params={'symbol': self.mexc_symbol})
            has_pos = any(float(p.get('contracts', 0)) > 0 for p in pos) if pos else False
            
            if not has_pos and self.last_balance > 0:
                new_balance = self.get_balance()
                profit = new_balance - self.last_balance
                self.daily_profit += profit
                self.trades_today += 1
                
                status = "💰 LUCRO" if profit > 0 else "📉 STOP"
                self.notify(f"🏁 RESULTADO DA OPERAÇÃO:\n{status}: ${profit:.2f}\n📊 Acumulado Hoje: ${self.daily_profit:.2f}\n🔄 Trades: {self.trades_today}")
                self.last_balance = 0
        except: pass

    def run_loop(self):
        self.notify("SISTEMA ONLINE 🚀\nAnalisando Compra e Venda com SL/TP.")
        while True:
            try:
                self.monitor_exit()
                pos = self.exchange.fetch_positions(params={'symbol': self.mexc_symbol})
                has_pos = any(float(p.get('contracts', 0)) > 0 for p in pos) if pos else False
                
                if not has_pos:
                    df, c = self.get_data()
                    if df is not None:
                        last, prev = df.iloc[-1], df.iloc[-2]
                        price = self.exchange.fetch_ticker(self.symbol)['last']
                        
                        # --- VERIFICAÇÃO DE MÉTRICAS ---
                        # Estratégia: Médias alinhadas + Rompimento de Banda + RSI + Volume
                        buy = (last['close'] > last[c['EMA9']]) and (last[c['EMA9']] > last[c['EMA21']]) and \
                              (prev['close'] > prev[c['BBU']]) and (50 < last[c['RSI']] < 70) and \
                              (last['volume'] > last['vol_avg'])

                        sell = (last['close'] < last[c['EMA9']]) and (last[c['EMA9']] < last[c['EMA21']]) and \
                               (prev['close'] < prev[c['BBL']]) and (30 < last[c['RSI']] < 50) and \
                               (last['volume'] > last['vol_avg'])

                        if buy: self.execute('buy', price)
                        elif sell: self.execute('sell', price)
                
                print(f"[{time.strftime('%H:%M:%S')}] Analisando confluências de 5m...")
                time.sleep(30)
            except Exception as e:
                print(f"Erro no loop: {e}"); time.sleep(20)

if __name__ == "__main__":
    k, s, t, c = os.getenv("MEXC_API_KEY"), os.getenv("MEXC_SECRET"), os.getenv("TELEGRAM_TOKEN"), os.getenv("CHAT_ID")
    if all([k, s, t, c]): JordanEliteBot(k, s, t, c).run_loop()
