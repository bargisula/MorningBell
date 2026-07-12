"""市場紅綠燈：把 risk-on / risk-off 濃縮成一顆燈 + 一句人話。

判斷邏輯（刻意簡單，讓人講得清楚）：
  - 趨勢：S&P 500（SPY）是否站在 200 日均線之上
  - 情緒：VIX 恐慌指數的高低
"""
from services import market

GREEN, YELLOW, RED = "green", "yellow", "red"


def market_light() -> dict:
    spy = market.history("SPY", "1y")["Close"].dropna()
    price = float(spy.iloc[-1])
    ma200 = float(spy.rolling(200).mean().iloc[-1])
    trend_up = price > ma200
    trend_gap = (price / ma200 - 1) * 100

    vix, _, _ = market.last_close("^VIX")

    if trend_up and vix < 20:
        color, title = GREEN, "一切正常"
        reason = "大盤站在長期趨勢線之上，市場情緒平穩。照你原本的計畫走就好。"
    elif not trend_up and vix > 25:
        color, title = RED, "小心行事"
        reason = "大盤跌破長期趨勢線，而且市場明顯緊張。這種時候先別急著加碼，看清楚再說。"
    else:
        color, title = YELLOW, "保持觀望"
        if not trend_up:
            reason = "大盤跌到長期趨勢線之下，但市場還沒到恐慌的程度。多留意、少動作。"
        else:
            reason = "大盤趨勢還在，但市場情緒偏緊張。不用慌，但別追高。"

    return {
        "color": color,
        "title": title,
        "reason": reason,
        "details": {
            "spy_price": round(price, 2),
            "spy_ma200": round(ma200, 2),
            "trend_gap_pct": round(trend_gap, 1),
            "trend_up": trend_up,
            "vix": round(vix, 1),
        },
    }
