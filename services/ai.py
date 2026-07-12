"""選配的 AI 白話解讀。

有設 ANTHROPIC_API_KEY 就開，沒設就回 None，晨報照樣能用（模板文案）。
模型預設 claude-haiku-4-5（便宜、快），可用 MORNINGBELL_AI_MODEL 覆蓋。
"""
import json
import logging
import os

log = logging.getLogger("morningbell.ai")

SYSTEM = (
    "你是一位親切的美股晨間電台主持人，聽眾是完全沒有投資基礎的人。"
    "根據使用者提供的 JSON 市場數據，寫一段 120～180 字的繁體中文晨報開場白。"
    "要求：全部用人話，不用任何專有名詞；語氣像朋友聊天；"
    "只描述發生了什麼與這代表什麼氛圍，絕對不給任何買賣建議；"
    "不要條列，寫成一段自然的文字。"
)


def enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def narrative(brief: dict) -> str | None:
    if not enabled():
        return None
    try:
        import anthropic
    except ImportError:
        log.warning("已設定 ANTHROPIC_API_KEY 但未安裝 anthropic 套件")
        return None

    payload = {k: brief.get(k) for k in
               ("date_label", "market_note", "headline", "indices", "light", "watchlist")}
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=os.getenv("MORNINGBELL_AI_MODEL", "claude-haiku-4-5"),
            max_tokens=600,
            system=SYSTEM,
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        )
        return next((b.text for b in response.content if b.type == "text"), None)
    except anthropic.APIError as exc:
        log.warning("AI 解讀失敗：%s", exc)
        return None
