"""调试数据检查"""
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import time

def download_klines(symbol="BTCUSDT", interval="5m", limit=1000):
    url = "https://api.binance.com/api/v3/klines"
    all_data = []
    end_time = int(datetime.now().timestamp() * 1000)
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "endTime": end_time,
        "limit": limit
    }
    
    response = requests.get(url, params=params, timeout=30)
    data = response.json()
    
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    
    df["timestamp"] = pd.to_datetime(df["open_time"].astype(float), unit="ms")
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

df = download_klines(limit=1000)
print(f"数据量: {len(df)}")
print(f"\n前5行:")
print(df.head())
print(f"\n数据类型:")
print(df.dtypes)
print(f"\nClose 统计:")
print(df["close"].describe())

# 测试区间计算
window = 48
df["range_high"] = df["high"].rolling(window).max()
df["range_low"] = df["low"].rolling(window).min()

print(f"\n区间统计:")
print(f"Range High 非空数: {df['range_high'].notna().sum()}")
print(f"Range Low 非空数: {df['range_low'].notna().sum()}")
print(f"\n最近10个区间:")
print(df[["timestamp", "close", "range_high", "range_low"]].tail(10))

# 测试突破
df["breakout_up"] = df["close"] > df["range_high"]
df["breakout_dn"] = df["close"] < df["range_low"]
print(f"\n突破统计:")
print(f"向上突破: {df['breakout_up'].sum()}")
print(f"向下突破: {df['breakout_dn'].sum()}")
