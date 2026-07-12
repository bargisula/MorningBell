"""所有市場資料的唯一入口（yfinance 門面）。

其他模組不得直接 import yfinance——資料源要換、要修，只改這一個檔。
快取放在行程記憶體：報價類 10 分鐘、基本面 12 小時。
"""
import threading
import time
from typing import Any, Callable

import pandas as pd
import yfinance as yf

_cache: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()

QUOTE_TTL = 600        # 10 分鐘
INFO_TTL = 43200       # 12 小時


class DataUnavailable(Exception):
    """資料源抓不到資料。寧可大聲報錯，不默默給舊數據。"""


def _cached(key: str, ttl: int, fetch: Callable[[], Any]) -> Any:
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    value = fetch()
    with _lock:
        _cache[key] = (now, value)
    return value


def history(symbol: str, period: str = "1y") -> pd.DataFrame:
    def fetch() -> pd.DataFrame:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        if df is None or df.empty:
            raise DataUnavailable(f"{symbol} 抓不到歷史價格")
        return df

    return _cached(f"hist:{symbol}:{period}", QUOTE_TTL, fetch)


def last_close(symbol: str) -> tuple[float, float, pd.Timestamp]:
    """回傳（最新收盤價、對前一日漲跌幅 %、收盤日期）。"""
    df = history(symbol, "10d")
    close = df["Close"].dropna()
    if len(close) < 2:
        raise DataUnavailable(f"{symbol} 價格資料不足")
    last, prev = float(close.iloc[-1]), float(close.iloc[-2])
    return last, (last / prev - 1) * 100, close.index[-1]


def info(symbol: str) -> dict:
    def fetch() -> dict:
        data = yf.Ticker(symbol).info
        if not data or data.get("regularMarketPrice") is None and data.get(
            "currentPrice"
        ) is None:
            raise DataUnavailable(f"{symbol} 抓不到基本資料")
        return data

    return _cached(f"info:{symbol}", INFO_TTL, fetch)


def next_earnings_date(symbol: str):
    """下一次財報日（datetime.date），抓不到回 None——財報日缺漏不該弄壞晨報。"""
    def fetch():
        try:
            cal = yf.Ticker(symbol).calendar
            dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
            return dates[0] if dates else None
        except Exception:
            return None

    return _cached(f"earnings:{symbol}", INFO_TTL, fetch)
