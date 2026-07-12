"""API 路由。端點刻意用同步 def——FastAPI 會丟進 threadpool 並行跑，
避免 yfinance 的阻塞 I/O 卡住 event loop。"""
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db
from services import brief, checkup as checkup_svc, light, market

router = APIRouter()

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def _clean_ticker(raw: str) -> str:
    ticker = raw.strip().upper()
    if not TICKER_RE.match(ticker):
        raise HTTPException(422, "股票代號格式不對，例如：AAPL、NVDA、BRK-B")
    return ticker


@router.get("/brief")
def get_brief():
    return brief.daily_brief()


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
    return db.watchlist()


@router.post("/watchlist", status_code=201)
def add_watch(item: WatchItem):
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
    if not db.remove_ticker(_clean_ticker(ticker)):
        raise HTTPException(404, "清單裡沒有這支股票")
    return {"ok": True}


@router.get("/health")
def health():
    return {"status": "ok"}
