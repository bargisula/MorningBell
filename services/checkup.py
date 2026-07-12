"""個股健檢：輸入代號 → 三張卡（貴不貴 / 體質好不好 / 有沒有紅旗）。

每張卡結論先行（emoji + 一句人話），細節在 details 供前端摺疊顯示。
門檻刻意用整數、講得出口的標準——這是給新手的體檢表，不是量化模型。
"""
from services import market


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.0f}"


def _valuation_card(info: dict, price: float, pos52: float | None) -> dict:
    pe = info.get("trailingPE")
    details = []

    if pe and pe > 0:
        details.append({
            "label": "本益比",
            "value": f"{pe:.1f}",
            "note": f"以目前的獲利速度，大約要 {pe:.0f} 年才賺回你付的股價",
        })
        if pe < 15:
            grade = {"emoji": "😌", "headline": "以本益比看，不算貴"}
        elif pe < 25:
            grade = {"emoji": "🙂", "headline": "價格在合理範圍"}
        elif pe < 40:
            grade = {"emoji": "😰", "headline": "偏貴，市場已經給了很高的期待"}
        else:
            grade = {"emoji": "🥵", "headline": "非常貴，價格已計入極高的期待"}
    else:
        grade = {"emoji": "🤔", "headline": "公司目前沒賺錢或無本益比，不能用一般標準看貴俗"}
        ps = info.get("priceToSalesTrailing12Months")
        if ps:
            details.append({"label": "股價營收比", "value": f"{ps:.1f}",
                            "note": "沒賺錢的公司改看營收：這個數字越高，市場期待越高"})

    fpe = info.get("forwardPE")
    if fpe and fpe > 0:
        details.append({"label": "預估本益比", "value": f"{fpe:.1f}",
                        "note": "用分析師預估的未來獲利算，比較低代表獲利被看好會成長"})
    if pos52 is not None:
        details.append({"label": "股價位置", "value": f"{pos52 * 100:.0f}%",
                        "note": "位在過去一年價格區間的高度，100% = 一年最高點"})
    return {**grade, "details": details}


def _quality_card(info: dict) -> dict:
    checks = []

    margin = info.get("profitMargins")
    if margin is not None:
        checks.append({
            "label": "賺錢能力", "passed": margin > 0.10,
            "note": f"每做 100 元生意，最後留下 {_fmt_pct(margin)} 元"
            + ("（不錯）" if margin > 0.10 else "（偏薄）" if margin > 0 else "（在虧錢）"),
        })
    roe = info.get("returnOnEquity")
    if roe is not None:
        checks.append({
            "label": "資本效率", "passed": roe > 0.15,
            "note": f"股東每投入 100 元，一年幫你賺 {_fmt_pct(roe)} 元",
        })
    growth = info.get("revenueGrowth")
    if growth is not None:
        checks.append({
            "label": "營收成長", "passed": growth > 0.05,
            "note": f"生意規模一年{'成長' if growth >= 0 else '縮水'} {abs(growth) * 100:.0f}%",
        })
    fcf = info.get("freeCashflow")
    if fcf is not None:
        checks.append({
            "label": "現金流", "passed": fcf > 0,
            "note": "扣掉所有開銷後，口袋" + ("真的有進錢" if fcf > 0 else "其實在出血"),
        })
    dte = info.get("debtToEquity")
    if dte is not None:
        checks.append({
            "label": "負債水位", "passed": dte < 100,
            "note": f"借來的錢是自有資金的 {dte:.0f}%"
            + ("，還算保守" if dte < 100 else "，槓桿開得不小"),
        })

    passed = sum(1 for c in checks if c["passed"])
    if len(checks) < 3:
        grade = {"emoji": "🤷", "headline": "公開資料不足，看不出體質"}
    elif passed >= 4:
        grade = {"emoji": "💪", "headline": f"體質強健（{passed}/{len(checks)} 項達標）"}
    elif passed == 3:
        grade = {"emoji": "🙂", "headline": f"體質尚可（{passed}/{len(checks)} 項達標）"}
    else:
        grade = {"emoji": "😟", "headline": f"體質偏弱（{passed}/{len(checks)} 項達標）"}
    return {**grade, "checks": checks}


def _flags_card(info: dict, pos52: float | None) -> dict:
    flags = []
    margin = info.get("profitMargins")
    if margin is not None and margin < 0:
        flags.append("公司目前是虧錢的")
    growth = info.get("revenueGrowth")
    if growth is not None and growth < -0.05:
        flags.append(f"營收在衰退（一年 -{abs(growth) * 100:.0f}%），生意在變小")
    dte = info.get("debtToEquity")
    if dte is not None and dte > 200:
        flags.append(f"負債是自有資金的 {dte:.0f}%，槓桿很重")
    fcf = info.get("freeCashflow")
    if fcf is not None and fcf < 0:
        flags.append("自由現金流為負，帳面之外實際在燒錢")
    pe = info.get("trailingPE")
    if pe and pe > 60:
        flags.append(f"本益比高達 {pe:.0f}，價格已計入非常高的成長期待")
    if pos52 is not None and pos52 < 0.30:
        flags.append("股價位於過去一年價格區間的低檔（不到 30% 高度）")

    if not flags:
        grade = {"emoji": "✅", "headline": "沒有明顯紅旗"}
    elif len(flags) <= 2:
        grade = {"emoji": "⚠️", "headline": f"有 {len(flags)} 面紅旗"}
    else:
        grade = {"emoji": "🚩", "headline": f"紅旗多達 {len(flags)} 面"}
    return {**grade, "items": flags}


def checkup(ticker: str) -> dict:
    info = market.info(ticker)
    price, pct, _ = market.last_close(ticker)

    pos52 = None
    hist = market.history(ticker, "1y")["Close"].dropna()
    hi, lo = float(hist.max()), float(hist.min())
    if hi > lo:
        pos52 = (price - lo) / (hi - lo)

    return {
        "ticker": ticker,
        "name": info.get("longName") or info.get("shortName") or ticker,
        "price": round(price, 2),
        "pct": round(pct, 2),
        "currency": info.get("currency", "USD"),
        "cards": {
            "valuation": _valuation_card(info, price, pos52),
            "quality": _quality_card(info),
            "flags": _flags_card(info, pos52),
        },
        "disclaimer": "以上為公開數據的白話整理，僅供參考，不構成投資建議。",
    }
