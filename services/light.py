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

    # 文案原則：忠實描述市場狀態，不給行動指示、不揣測使用者的計畫
    if trend_up and vix < 20:
        color, title = GREEN, "市場平穩"
        reason = "大盤站在長期趨勢線之上，市場情緒平穩。"
    elif not trend_up and vix > 25:
        color, title = RED, "市場緊張"
        reason = "大盤跌破長期趨勢線，且恐慌指數處於偏高水位。"
    else:
        color, title = YELLOW, "訊號分歧"
        if not trend_up:
            reason = "大盤位於長期趨勢線之下，但市場情緒尚未明顯緊張。"
        else:
            reason = "大盤仍在長期趨勢線之上，但市場情緒偏向緊張。"

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
