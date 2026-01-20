import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

class JordanEliteBot:
    def __init__(self, api_key, secret, telegram_token, chat_id):
        # 1. Conexão com a Exchange
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        
        # 2. Configurações de Governança
        self.symbol = 'BTC/USDT:USDT'
        self.timeframe = '15m'
        self.leverage = 10           
        self.risk_per_trade = 0.01   
        
        # 3. Credenciais de Telemetria
        self.telegram_token = telegram_token
        self.chat_id = chat_id

    def notify(self, message):
        """Protocolo de comunicação remota via Telegram"""
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": f"🤖 **JORDAN ELITE BOT**\n{message}", "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Erro de telemetria: {e}")

    def apply_governance(self):
        """Aplica protocolos de segurança corrigidos para exigências da MEXC"""
        try:
            # Forçando parâmetros explícitos para evitar erro 600
            self.exchange.set_margin_mode('ISOLATED', self.symbol, {'leverage': self.leverage})
            self.exchange.set_leverage(self.leverage, self.symbol)
            self.notify(f"✅ Governança Aplicada: **Margem Isolada | {self.leverage}x**")
        except Exception as e:
            print(f"Nota de Governança: {e}")

    def get_market_data(self):
        """Camada de inteligência de dados com normalização de colunas"""
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
        """Cálculo de Lote Dinâmico - Gestão de Risco"""
        try:
            balance = self.exchange.fetch_balance()
            available = float(balance['info']['data']['available'])
            risk_amount = available * self.risk_per_trade
            price_variation = abs(price - stop_loss)
            if price_variation == 0: return 0
            size = risk_amount / price_variation
            max_allowed = (available * self.leverage * 0.9) / price
            return min(size, max_allowed)
        except Exception as e:
            print(f"Erro no cálculo de lote: {e}")
            return 0

    def check_liquidity(self, side, amount):
        """Verifica se há liquidez no Orderbook"""
        try:
            ob = self.exchange.fetch_order_book(self.symbol, limit=5)
            levels = ob['asks'] if side == 'buy' else ob['bids']
            total_vol = sum([level[1] for level in levels])
            return total_vol >= (amount * 2)
        except:
            return False

    def execute_logic(self):
        """Motor de decisão principal"""
        try:
            df = self.get_market_data()
            last = df.iloc[-1]
            prev = df.iloc[-2]
            current_price = self.exchange.fetch_ticker(self.symbol)['last']

            long_cond = (prev['close'] > prev['BBU']) and (last['RSI'] < 70)
            short_cond = (prev['close'] < prev['BBL']) and (last['RSI'] > 30)

            if long_cond:
                self.open_position('buy', current_price)
            elif short_cond:
                self.open_position('sell', current_price)
        except Exception as e:
            print(f"Erro na lógica: {e}")

    def open_position(self, side, price):
        """Execução de Ordem Market com SL e TP"""
        sl_pct = 0.015
        sl = price * (1 - sl_pct) if side == 'buy' else price * (1 + sl_pct)
        tp = price * (1 + sl_pct * 2) if side == 'buy' else price * (1 - sl_pct * 2)
        lot = self.calculate_position_size(price, sl)
        
        if lot > 0 and self.check_liquidity(side, lot):
            try:
                self.exchange.create_order(
                    symbol=self.symbol, type='market', side=side, amount=lot,
                    params={'stopLossPrice': sl, 'takeProfitPrice': tp}
                )
                self.notify(f"🚀 **ORDEM EXECUTADA**\n🔹 {side.upper()} BTC\n🔹 Lote: {lot:.4f}")
            except Exception as e:
                self.notify(f"❌ Falha na execução: {e}")

    def run(self):
        """Início do Loop de Monitoramento com correção para Erro 600"""
        self.notify("⚡ **Jordan Elite Bot Ativado**")
        self.apply_governance()
        while True:
            try:
                # CORREÇÃO: Passando o symbol explicitamente para evitar 'Params can't be null'
                # Na MEXC, fetch_positions requer o filtro de símbolo para retornar dados limpos
                pos = self.exchange.fetch_positions([self.symbol])
                
                # Verificação robusta de posição aberta
                has_pos = False
                if pos and len(pos) > 0:
                    # Filtra apenas posições que possuem contratos maiores que zero
                    active_pos = [p for p in pos if float(p.get('contracts', 0)) > 0]
                    if len(active_pos) > 0:
                        has_pos = True

                if not has_pos:
                    self.execute_logic()
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Posição ativa detectada. Aguardando saída...")
                
                time.sleep(60) 
            except Exception as e:
                print(f"Erro no loop (Code 600 Fix): {e}")
                time.sleep(30)

if __name__ == "__main__":
    key = os.getenv("MEXC_API_KEY")
    sec = os.getenv("MEXC_SECRET")
    tok = os.getenv("TELEGRAM_TOKEN")
    cid = os.getenv("TELEGRAM_CHAT_ID")
    if not all([key, sec, tok, cid]):
        sys.exit(1)
    bot = JordanEliteBot(key, sec, tok, cid)
    bot.run()
