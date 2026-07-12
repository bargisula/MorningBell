"""每日晨報：四段式，捲完就結束。

1. 昨夜盤勢（三大指數 + 一句總結）
2. 市場紅綠燈（嵌入 light 模組結果）
3. 你的觀察清單有沒有事
4. 接下來的大事（觀察清單的財報日）
"""
from datetime import date, datetime, timedelta

import db
from services import ai, light, market

INDICES = [
    ("^GSPC", "S&P 500"),
    ("^IXIC", "納斯達克"),
    ("^DJI", "道瓊"),
]

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


def _headline(rows: list[dict]) -> str:
    valid = [r for r in rows if r.get("pct") is not None]
    if not valid:
        return "指數資料暫時抓不到，稍後再試一次。"
    ups = sum(1 for r in valid if r["pct"] > 0)
    if ups == len(valid):
        opening = "三大指數全面收漲"
    elif ups == 0:
        opening = "三大指數全面收跌"
    else:
        opening = "三大指數漲跌互見"
    biggest = max(valid, key=lambda r: abs(r["pct"]))
    direction = "漲" if biggest["pct"] > 0 else "跌"
    return f"{opening}，其中{biggest['name']}變動最大，{direction}了 {abs(biggest['pct']):.2f}%。"


def _watch_note(pct: float, pos52: float | None) -> str:
    if pct >= 3:
        return f"大漲 {pct:.1f}%，值得點進健檢看看發生什麼事"
    if pct <= -3:
        return f"大跌 {abs(pct):.1f}%，先別慌，去健檢確認體質有沒有變"
    if pos52 is not None and pos52 >= 0.97:
        return "貼近 52 週最高點，市場對它很樂觀"
    if pos52 is not None and pos52 <= 0.05:
        return "貼近 52 週最低點，市場對它很悲觀"
    return "今天平穩，沒什麼特別的事"


def _watchlist_section() -> list[dict]:
    items = []
    for row in db.watchlist():
        t = row["ticker"]
        try:
            price, pct, _ = market.last_close(t)
            pos52 = None
            hist = market.history(t, "1y")["Close"].dropna()
            hi, lo = float(hist.max()), float(hist.min())
            if hi > lo:
                pos52 = (price - lo) / (hi - lo)
            items.append({
                "ticker": t,
                "name": row.get("name") or t,
                "price": round(price, 2),
                "pct": round(pct, 2),
                "note": _watch_note(pct, pos52),
            })
        except market.DataUnavailable as exc:
            items.append({"ticker": t, "name": row.get("name") or t,
                          "price": None, "pct": None, "note": f"資料抓取失敗：{exc}"})
    return items


def _events_section() -> list[dict]:
    events = []
    horizon = date.today() + timedelta(days=10)
    for row in db.watchlist():
        d = market.next_earnings_date(row["ticker"])
        if d is None:
            continue
        d = d.date() if isinstance(d, datetime) else d
        if date.today() <= d <= horizon:
            events.append({
                "ticker": row["ticker"],
                "name": row.get("name") or row["ticker"],
                "date": d.isoformat(),
                "label": f"{d.month}/{d.day} 公布財報",
            })
    return sorted(events, key=lambda e: e["date"])


def daily_brief() -> dict:
    today = date.today()

    indices, trade_date = [], None
    for symbol, name in INDICES:
        try:
            price, pct, ts = market.last_close(symbol)
            trade_date = trade_date or ts.date()
            indices.append({"symbol": symbol, "name": name,
                            "close": round(price, 2), "pct": round(pct, 2)})
        except market.DataUnavailable:
            indices.append({"symbol": symbol, "name": name, "close": None, "pct": None})

    try:
        light_data = light.market_light()
    except market.DataUnavailable as exc:
        light_data = {"color": "unknown", "title": "資料抓取失敗",
                      "reason": str(exc), "details": {}}

    brief = {
        "date": today.isoformat(),
        "date_label": f"{today.month} 月 {today.day} 日 星期{WEEKDAYS[today.weekday()]}",
        "trade_date": trade_date.isoformat() if trade_date else None,
        # 週五收盤到週一開盤前相隔 3 天都算正常，超過才視為資料過期
        "is_stale": bool(trade_date and (today - trade_date).days > 3),
        "market_note": "美股週末休市，以下是最近一個交易日的收盤情況。"
        if today.weekday() >= 5 else None,
        "headline": _headline(indices),
        "indices": indices,
        "light": light_data,
        "watchlist": _watchlist_section(),
        "events": _events_section(),
    }
    brief["ai_narrative"] = ai.narrative(brief)
    brief["ai_enabled"] = ai.enabled()
    return brief
