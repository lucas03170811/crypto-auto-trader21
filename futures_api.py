import time
import pandas as pd
from binance.client import Client
from binance.um_futures import UMFutures
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

API_KEY = '你的 API KEY'
API_SECRET = '你的 SECRET KEY'
client = Client(api_key=API_KEY, api_secret=API_SECRET)
um_futures = UMFutures(key=API_KEY, secret=API_SECRET)

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'ADAUSDT']
INTERVAL_SHORT = '15m'
INTERVAL_LONG = '1h'

POSITION_CACHE = {}

def get_klines(symbol, interval, limit=100):
    data = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close',
                                     'volume', 'close_time', 'quote_asset_volume',
                                     'number_of_trades', 'taker_buy_base',
                                     'taker_buy_quote', 'ignore'])
    df['close'] = pd.to_numeric(df['close'])
    return df

def get_trend_signal(symbol):
    short_df = get_klines(symbol, INTERVAL_SHORT)
    long_df = get_klines(symbol, INTERVAL_LONG)

    short_ema = EMAIndicator(short_df['close'], window=20).ema_indicator()
    long_ema = EMAIndicator(long_df['close'], window=20).ema_indicator()

    if short_df['close'].iloc[-1] > short_ema.iloc[-1] and long_df['close'].iloc[-1] > long_ema.iloc[-1]:
        return "LONG"
    elif short_df['close'].iloc[-1] < short_ema.iloc[-1] and long_df['close'].iloc[-1] < long_ema.iloc[-1]:
        return "SHORT"
    else:
        return "NEUTRAL"

def get_position(symbol):
    positions = um_futures.get_position_risk()
    for pos in positions:
        if pos['symbol'] == symbol:
            return float(pos['positionAmt']), float(pos['entryPrice'])
    return 0.0, 0.0

def place_order(symbol, side, quantity):
    um_futures.new_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)

def close_position(symbol, quantity, side):
    reverse = 'SELL' if side == 'BUY' else 'BUY'
    place_order(symbol, reverse, quantity)

def calculate_position_strategy(symbol):
    position_amt, entry_price = get_position(symbol)
    mark_price = float(um_futures.ticker_price(symbol=symbol)['price'])

    if position_amt == 0:
        return None

    pnl_percent = ((mark_price - entry_price) / entry_price) * 100 if position_amt > 0 else ((entry_price - mark_price) / entry_price) * 100

    if symbol not in POSITION_CACHE:
        POSITION_CACHE[symbol] = {'entry_price': entry_price, 'max_price': entry_price}

    POSITION_CACHE[symbol]['max_price'] = max(POSITION_CACHE[symbol]['max_price'], mark_price)
    drawdown = ((POSITION_CACHE[symbol]['max_price'] - mark_price) / POSITION_CACHE[symbol]['max_price']) * 100

    if pnl_percent >= 50:
        close_position(symbol, abs(position_amt) * 0.5, 'BUY' if position_amt > 0 else 'SELL')

    if drawdown >= 15:
        close_position(symbol, abs(position_amt), 'BUY' if position_amt > 0 else 'SELL')

    if pnl_percent >= 30:
        place_order(symbol, 'BUY' if position_amt > 0 else 'SELL', abs(position_amt) * 0.5)

def check_and_trade():
    for symbol in SYMBOLS:
        signal = get_trend_signal(symbol)
        position_amt, _ = get_position(symbol)

        if signal == "LONG" and position_amt <= 0:
            place_order(symbol, "BUY", 0.01)
        elif signal == "SHORT" and position_amt >= 0:
            place_order(symbol, "SELL", 0.01)

        calculate_position_strategy(symbol)
