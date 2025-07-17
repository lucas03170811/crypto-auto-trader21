import pandas as pd
import time
import os
from binance.um_futures import UMFutures
from binance.error import ClientError
import ta

# 讀取環境變數中的 API 金鑰
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

# 建立 Binance 合約 API 客戶端
client = UMFutures(key=api_key, secret=api_secret)

# 支援交易的幣種與時間週期
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
intervals = ["15m", "1h"]

# 取得 K 線資料
def get_klines(symbol, interval, limit=100):
    try:
        klines = client.klines(symbol, interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
        return df
    except ClientError as e:
        print(f"Error fetching data for {symbol} - {interval}: {e}")
        return None

# 分析並自動下單
def check_and_trade():
    for symbol in symbols:
        for interval in intervals:
            df = get_klines(symbol, interval)
            if df is None
