"""API 路由。端點刻意用同步 def——FastAPI 會丟進 threadpool 並行跑，
避免 yfinance 的阻塞 I/O 卡住 event loop。"""
import os
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db
from services import brief, checkup as checkup_svc, light, market

router = APIRouter()

# Demo 模式（公開 Demo 站用）：清單存訪客自己的瀏覽器，伺服器不落地任何用戶資料
DEMO = os.getenv("MORNINGBELL_DEMO") == "1"

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def _clean_ticker(raw: str) -> str:
    ticker = raw.strip().upper()
    if not TICKER_RE.match(ticker):
        raise HTTPException(422, "股票代號格式不對，例如：AAPL、NVDA、BRK-B")
    return ticker


@router.get("/config")
def get_config():
    return {"demo": DEMO}


@router.get("/brief")
def get_brief(tickers: str | None = None):
    # Demo 模式下，前端把訪客瀏覽器裡的清單用 ?tickers=NVDA,TSM 帶進來，算完即忘
    ticker_list = None
    if tickers:
        ticker_list = [_clean_ticker(t) for t in tickers.split(",") if t.strip()][:20]
    return brief.daily_brief(ticker_list)


@router.get("/lookup/{ticker}")
def lookup(ticker: str):
    """確認代號存在並回公司名稱，不儲存任何東西（Demo 模式加清單用）。"""
    ticker = _clean_ticker(ticker)
    try:
        info = market.info(ticker)
    except market.DataUnavailable:
        raise HTTPException(404, f"找不到 {ticker}，確認代號拼對了嗎？")
    return {"ticker": ticker, "name": info.get("longName") or info.get("shortName") or ticker}


@router.get("/light")
def get_light():
    try:
        return light.market_light()
    except market.DataUnavailable as exc:
        raise HTTPException(503, str(exc))


@router.get("/checkup/{ticker}")
def get_checkup(ticker: str):
    ticker = _clean_ticker(ticker)
    try:
        return checkup_svc.checkup(ticker)
    except market.DataUnavailable:
        raise HTTPException(404, f"找不到 {ticker} 的資料，確認代號拼對了嗎？")


class WatchItem(BaseModel):
    ticker: str


@router.get("/watchlist")
def get_watchlist():
    if DEMO:
        return []
    return db.watchlist()


@router.post("/watchlist", status_code=201)
def add_watch(item: WatchItem):
    if DEMO:
        raise HTTPException(403, "Demo 站的清單存在你自己的瀏覽器裡，伺服器不代管")
    ticker = _clean_ticker(item.ticker)
    try:
        info = market.info(ticker)
    except market.DataUnavailable:
        raise HTTPException(404, f"找不到 {ticker}，確認代號拼對了嗎？")
    name = info.get("longName") or info.get("shortName") or ticker
    db.add_ticker(ticker, name)
    return {"ticker": ticker, "name": name}


@router.delete("/watchlist/{ticker}")
def remove_watch(ticker: str):
    if DEMO:
        raise HTTPException(403, "Demo 站的清單存在你自己的瀏覽器裡，伺服器不代管")
    if not db.remove_ticker(_clean_ticker(ticker)):
        raise HTTPException(404, "清單裡沒有這支股票")
    return {"ok": True}


@router.get("/health")
def health():
    return {"status": "ok"}
