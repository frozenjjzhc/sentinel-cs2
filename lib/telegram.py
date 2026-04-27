"""
Telegram bot interface (stub — not yet connected).

To activate later, user provides:
- TELEGRAM_BOT_TOKEN (from @BotFather)
- TELEGRAM_CHAT_ID(s) for each recipient

Stored in state.global.telegram_config:
{
  "enabled": true,
  "bot_token": "1234:ABCD...",
  "recipients": [
      {"name": "primary", "chat_id": "123456789"},
      ...
  ]
}

API: https://api.telegram.org/bot<token>/sendMessage
"""

import requests


TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"
TIMEOUT_SECONDS = 10


def is_configured(state: dict) -> bool:
    cfg = state.get("global", {}).get("telegram_config", {})
    return (
        cfg.get("enabled")
        and cfg.get("bot_token")
        and cfg.get("recipients")
    )


def send_to_chat(bot_token: str, chat_id: str, title: str, body: str) -> tuple:
    """
    Send a single Telegram message.
    Returns (success: bool, response: str).
    """
    try:
        url = TELEGRAM_API_BASE.format(token=bot_token)
        text = f"*{title}*\n\n{body}"
        r = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=TIMEOUT_SECONDS,
        )
        ok = r.status_code == 200 and r.json().get("ok") is True
        return ok, str(r.json())[:300]
    except Exception as e:
        return False, str(e)


def send_to_all(state: dict, title: str, body: str) -> dict:
    """Push to all configured Telegram recipients. Stub-safe: returns empty if not configured."""
    if not is_configured(state):
        return {}
    cfg = state["global"]["telegram_config"]
    token = cfg["bot_token"]
    results = {}
    for rec in cfg.get("recipients", []):
        name = rec.get("name", "anon")
        chat_id = rec.get("chat_id")
        if not chat_id:
            results[name] = (False, "no_chat_id")
            continue
        ok, resp = send_to_chat(token, chat_id, title, body)
        results[name] = (ok, resp)
    return results


def setup_instructions() -> str:
    """Return human-readable setup steps."""
    return (
        "Telegram 接入步骤：\n"
        "1. 在 Telegram 中找 @BotFather → /newbot → 起名 → 拿到 bot_token\n"
        "2. 给你的 bot 发一条任意消息（必须先发，否则拿不到 chat_id）\n"
        "3. 浏览器打开 https://api.telegram.org/bot<TOKEN>/getUpdates\n"
        "   找到 result[0].message.chat.id → 这就是你的 chat_id\n"
        "4. 编辑 state.json 的 global.telegram_config:\n"
        "   {\n"
        "     \"enabled\": true,\n"
        "     \"bot_token\": \"1234:ABCD...\",\n"
        "     \"recipients\": [\n"
        "       {\"name\": \"primary\", \"chat_id\": \"123456789\"}\n"
        "     ]\n"
        "   }\n"
        "5. monitor_fast/slow/daily_review 会自动同时推送到 PushPlus 和 Telegram"
    )
