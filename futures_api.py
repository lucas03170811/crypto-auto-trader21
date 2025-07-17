import pandas as pd
import time
from binance.um_futures import UMFutures
from binance.error import ClientError
import ta
import os

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

client = UMFutures(key=api_key, secret=api_secret)

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
intervals = ["15m", "1h"]

def get_klines(symbol, interval, limit=100):
    try:
        klines = client.klines(symbol, interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close',
            'volume', 'close_time', 'quote_asset_volume',
            'number_of_trades', 'taker_buy_base_volume',
            'taker_buy_quote_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
        return df
    except ClientError as e:
        print(f"Error fetching data for {symbol} - {interval}: {e}")
        return None

def check_and_trade():
    for symbol in symbols:
        for interval in intervals:
            df = get_klines(symbol, interval)
            if df is None or len(df) < 50:
                continue

            df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
            df['ema'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()

            current_price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            ema = df['ema'].iloc[-1]
            volume = df['volume'].iloc[-1]

            if rsi < 30 and current_price > ema:
                print(f"[LONG] {symbol} at {current_price} (RSI: {rsi:.2f}, EMA: {ema:.2f})")
                try:
                    client.new_order(symbol=symbol, side="BUY", type="MARKET", quantity=0.01)
                except ClientError as e:
                    print(f"Order Error: {e}")

            elif rsi > 70 and current_price < ema:
                print(f"[SHORT] {symbol} at {current_price} (RSI: {rsi:.2f}, EMA: {ema:.2f})")
                try:
                    client.new_order(symbol=symbol, side="SELL", type="MARKET", quantity=0.01)
                except ClientError as e:
                    print(f"Order Error: {e}")