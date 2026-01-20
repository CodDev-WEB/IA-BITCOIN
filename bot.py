import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import os
import sys

class JordanEliteBot:
    def __init__(self, api_key, secret, telegram_token, chat_id):
        # 1. Conexão com a Exchange (Motor de Missão Crítica)
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'} # Foca em Futuros Perpétuos
        })
        
        # 2. Configurações de Governança
        self.symbol = 'BTC/USDT:USDT'
        self.timeframe = '15m'
        self.leverage = 10           # Alavancagem máxima permitida
        self.risk_per_trade = 0.01   # Risco de 1% do capital por trade
        
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
        """Aplica regras de margem e alavancagem na conta"""
        try:
            # Garante que estamos usando MARGEM ISOLADA para proteção de capital
            self.exchange.set_margin_mode('ISOLATED', self.symbol)
            self.exchange.set_leverage(self.leverage, self.symbol)
            self.notify(f"✅ Governança Aplicada: **Margem Isolada | {self.leverage}x**")
        except Exception as e:
            self.notify(f"⚠️ Nota de Governança: {e} (Pode já estar configurado)")

    def get_market_data(self):
        """Camada de inteligência de dados (Análise Quantitativa)"""
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Indicadores: Estratégia de Volatilidade e Momentum
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.rsi(length=14, append=True)
        return df

    def calculate_position_size(self, price, stop_loss):
        """Cálculo de Lote Dinâmico - Gestão de Risco de Elite"""
        try:
            balance = self.exchange.fetch_balance()
            # Acessa saldo disponível em USDT na carteira de Futuros
            available = float(balance['info']['data']['available'])
            
            risk_amount = available * self.risk_per_trade
            price_variation = abs(price - stop_loss)
            
            if price_variation == 0: return 0
            
            # Tamanho da posição baseado no risco financeiro
            size = risk_amount / price_variation
            
            # Trava de Segurança: Não exceder 90% do poder de compra real
            max_allowed = (available * self.leverage * 0.9) / price
            return min(size, max_allowed)
        except Exception as e:
            print(f"Erro no cálculo de lote: {e}")
            return 0

    def check_orderbook_liquidity(self, side, amount):
        """Evita Slippage: Verifica se há liquidez para o nosso lote"""
        ob = self.exchange.fetch_order_book(self.symbol, limit=5)
        levels = ob['asks'] if side == 'buy' else ob['bids']
        total_vol = sum([level[1] for level in levels])
        return total_vol >= (amount * 2) # Exigimos 2x a liquidez necessária

    def execute_logic(self):
        """Motor de decisão de entrada e saída"""
        df = self.get_market_data()
        last = df.iloc[-1]
        prev = df.iloc[-2]
        current_price = self.exchange.fetch_ticker(self.symbol)['last']

        # Sinais Técnicos
        long_signal = (prev['close'] > prev['BBU_20_2.0']) and (last['RSI_14'] < 70)
        short_signal = (prev['close'] < prev['BBL_20_2.0']) and (last['RSI_14'] > 30)

        if long_signal:
            self.open_position('buy', current_price)
        elif short_signal:
            self.open_position('sell', current_price)

    def open_position(self, side, price):
        """Executa a ordem com Stop Loss e Take Profit automáticos"""
        # Stop de 1.5% e Take Profit de 3% (Risk:Reward 1:2)
        sl_pct = 0.015
        sl = price * (1 - sl_pct) if side == 'buy' else price * (1 + sl_pct)
        tp = price * (1 + sl_pct * 2) if side == 'buy' else price * (1 - sl_pct * 2)

        lot = self.calculate_position_size(price, sl)
        
        if lot > 0 and self.check_orderbook_liquidity(side, lot):
            try:
                order = self.exchange.create_order(
                    symbol=self.symbol,
                    type='market',
                    side=side,
                    amount=lot,
                    params={'stopLossPrice': sl, 'takeProfitPrice': tp}
                )
                self.notify(f"🚀 **ORDEM EXECUTADA**\n🔹 {side.upper()} BTC\n🔹 Preço: {price}\n🔹 Lote: {lot:.4f}\n🔹 SL: {sl:.2f} | TP: {tp:.2f}")
            except Exception as e:
                self.notify(f"❌ Falha crítica na execução: {e}")
        else:
            print(f"Sinal ignorado: Liquidez insuficiente ou lote inválido ({lot})")

    def run(self):
        """Inicia o ciclo vital do sistema"""
        self.notify("⚡ **Jordan Elite Bot Ativado**\nMonitorando BTC/USDT em tempo real na Railway.")
        self.apply_governance()
        
        while True:
            try:
                # Verifica se já existe posição aberta
                pos = self.exchange.fetch_positions([self.symbol])
                has_pos = float(pos[0]['contracts']) > 0 if pos else False
                
                if not has_pos:
                    self.execute_logic()
                else:
                    # Monitoramento de logs no console do Railway
                    print(f"[{time.strftime('%H:%M:%S')}] Posição aberta monitorada...")
                
                time.sleep(60) # Varredura por minuto (eficiência de recursos)
            except Exception as e:
                print(f"Erro no loop principal: {e}")
                time.sleep(30)

if __name__ == "__main__":
    # Carregamento de Variáveis de Ambiente (Segurança de Elite)
    key = os.getenv("MEXC_API_KEY")
    sec = os.getenv("MEXC_SECRET")
    tok = os.getenv("TELEGRAM_TOKEN")
    cid = os.getenv("TELEGRAM_CHAT_ID")

    if not all([key, sec, tok, cid]):
        print("❌ ERRO: Variáveis de ambiente faltando!")
        sys.exit(1)

    bot = JordanEliteBot(key, sec, tok, cid)
    bot.run()
