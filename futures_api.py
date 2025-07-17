from binance.um_futures import UMFutures
from binance.error import ClientError
import pandas as pd
import time
import os
import ta

# 從環境變數中讀取 Binance API 金鑰
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

client = UMFutures(key=API_KEY, secret=API_SECRET)

# 支援的交易對
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]

# 設定止損比例（例如虧損達 20% 就止損）
STOP_LOSS_THRESHOLD = -0.20

# 取得技術指標：RSI + 成交量
def get_technical_indicators(symbol, interval="1m", limit=100):
    try:
        klines = client.klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df["close"] = pd.to_numeric(df["close"])
        df["volume"] = pd.to_numeric(df["volume"])
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        return df
    except Exception as e:
        print(f"[{symbol}] 取得指標失敗: {e}")
        return None

# 下市價單
def place_market_order(symbol, side, quantity):
    try:
        order = client.new_order(symbol=symbol, side=side, type="MARKET", quantity=quantity)
        print(f"[{symbol}] 已下單 {side}，數量：{quantity}")
        return order
    except ClientError as e:
        print(f"[{symbol}] 下單失敗: {e}")
        return None

# 取得持倉資訊
def get_position(symbol):
    try:
        positions = client.get_position_risk()
        for p in positions:
            if p["symbol"] == symbol:
                return float(p["positionAmt"]), float(p["unRealizedProfit"])
        return 0, 0
    except Exception as e:
        print(f"[{symbol}] 查詢持倉錯誤: {e}")
        return 0, 0

# 判斷是否應進場
def should_open_position(df):
    if df is None or df["rsi"].isna().all():
        return False
    latest_rsi = df["rsi"].iloc[-1]
    latest_vol = df["volume"].iloc[-1]
    avg_vol = df["volume"].mean()

    return latest_rsi < 30 and latest_vol > avg_vol  # 超賣且爆量

# 主邏輯
def check_and_trade():
    for symbol in SYMBOLS:
        print(f"分析：{symbol}")
        df = get_technical_indicators(symbol)

        if df is None:
            continue

        qty = 0.01 if "BTC" in symbol else 1  # 根據幣種調整下單量
        position_amt, unrealized_pnl = get_position(symbol)

        if position_amt == 0:  # 沒有持倉，可開倉
            if should_open_position(df):
                place_market_order(symbol, side="BUY", quantity=qty)
        else:
            # 若持倉虧損達止損線，平倉
            pnl_ratio = unrealized_pnl / (qty * df["close"].iloc[-1])
            print(f"[{symbol}] 持倉損益比率：{pnl_ratio:.2%}")
            if pnl_ratio <= STOP_LOSS_THRESHOLD:
                side = "SELL" if position_amt > 0 else "BUY"
                place_market_order(symbol, side=side, quantity=abs(position_amt))

        time.sleep(1)  # 暫停避免 API 過度頻繁 
