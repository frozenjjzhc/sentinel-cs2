"""
Steam News auto-monitor for CS2 (App ID 730).
Replaces the weekly Claude WebSearch.

Public Steam API: no authentication needed.
Endpoint:
  https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=730&count=20

Each news item has: title, contents (HTML), date (unix), url.

We classify each into bias-relevant categories:
- new_case / new_skin                   → negative (旧饰品稀释)
- major / operation / event / season    → positive
- anti_cheat / vac / ban / policy       → positive (long-term)
- patch_minor / animation / bugfix      → neutral
- exchange_remove / market_change       → emergency_keyword
"""

import re
import time
import requests
from . import utils
from . import config


STEAM_NEWS_URL = (
    "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
    "?appid=730&count=20&maxlength=2000&format=json"
)

# Keyword classifiers (lower-case match against title + contents)
KEYWORDS = {
    "new_case":       ["new case", "new collection", "new weapon case", "new sticker capsule",
                       "case introduced", "新箱子", "新箱"],
    "new_skin":       ["new skin", "new finish", "weapon collection", "new sticker"],
    "major":          ["major", "valve major", "stockholm major", "rio major", "antwerp",
                       "intro stage", "challengers stage"],
    "operation":      ["operation", "premier season", "service medal"],
    "anti_cheat":     ["vac", "vacnet", "anti-cheat", "ban wave", "cheater"],
    "policy":         ["trade ban", "trade hold", "policy", "terms of service",
                       "regional restriction"],
    "tech_update":    ["fix", "bug", "animgraph", "engine", "performance",
                       "stability", "memory", "client update", "patch notes"],
    "emergency":      ["item removed", "skin removed", "permanent ban", "policy change",
                       "no longer tradeable", "untradeable", "delisted", "blocked"],
}

BIAS_BY_CATEGORY = {
    "new_case":    "negative",
    "new_skin":    "negative",
    "major":       "positive",
    "operation":   "positive",
    "anti_cheat":  "positive",
    "policy":      "neutral",
    "tech_update": "neutral",
    "emergency":   "emergency",
}


def fetch_news() -> list:
    """Fetch latest CS2 news. Returns list of items or []."""
    try:
        r = requests.get(STEAM_NEWS_URL, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("appnews", {}).get("newsitems", [])
    except Exception as e:
        return []


def classify_news(news_item: dict) -> tuple:
    """Returns (category, bias) or (None, None)."""
    title = (news_item.get("title") or "").lower()
    contents = (news_item.get("contents") or "").lower()
    text = title + " " + contents

    for cat, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return cat, BIAS_BY_CATEGORY.get(cat, "neutral")
    return None, None


def summarize_recent(news_items: list, days: int = 30) -> dict:
    """
    Summarize all news in last N days.
    Returns:
    {
      "summary": str (concat top items),
      "recent_updates": [{date, type, topic, impact}, ...],
      "bias": "positive"|"negative"|"neutral"|"emergency",
      "emergency_detected": bool
    }
    """
    cutoff = time.time() - days * 86400
    recent = [n for n in news_items if n.get("date", 0) >= cutoff]

    classified = []
    bias_votes = []
    emergency_detected = False

    for item in recent:
        cat, bias = classify_news(item)
        if not cat:
            continue
        date_str = utils.now_local().strftime("%Y-%m-%d")  # fallback
        try:
            from datetime import datetime
            date_str = datetime.fromtimestamp(item["date"]).date().isoformat()
        except Exception:
            pass
        classified.append({
            "date": date_str,
            "title": item.get("title", "")[:100],
            "url": item.get("url"),
            "type": cat,
            "topic": item.get("title", "")[:60],
            "impact": bias,
        })
        bias_votes.append(bias)
        if bias == "emergency":
            emergency_detected = True

    # Aggregate bias
    if emergency_detected:
        agg_bias = "emergency"
    elif "negative" in bias_votes and bias_votes.count("negative") >= 2:
        agg_bias = "negative"
    elif bias_votes.count("positive") > bias_votes.count("negative"):
        agg_bias = "positive"
    elif bias_votes:
        agg_bias = "neutral_positive"
    else:
        agg_bias = "neutral"

    summary_lines = [f"近 {days} 天 V社更新分类汇总（共 {len(classified)} 条）："]
    for c in classified[:5]:
        summary_lines.append(f"• [{c['date']}] {c['type']}: {c['topic']}")
    if len(classified) > 5:
        summary_lines.append(f"... 另 {len(classified)-5} 条")

    return {
        "summary": "\n".join(summary_lines),
        "recent_updates": classified,
        "bias": agg_bias,
        "emergency_detected": emergency_detected,
    }


def update_fundamentals(state: dict, frequency_days: int = 7) -> bool:
    """
    Refresh fundamentals if next_check_due is past.
    优先尝试 LLM 语义分类（如启用），失败回落到关键词。
    Returns True if updated.
    """
    fund = state.setdefault("global", {}).setdefault("fundamentals", {})
    next_due = fund.get("next_check_due")
    if next_due and not utils.is_expired(next_due):
        return False

    news_items = fetch_news()
    if not news_items:
        utils.log_error(config.ERROR_LOG, "news_monitor: failed to fetch Steam news")
        return False

    # === 优先尝试 LLM 分类 ===
    llm_result = None
    method = "keyword"
    try:
        from . import llm_provider
        if llm_provider.is_module_enabled(state, "news_classification"):
            from . import llm_analyst
            llm_result = llm_analyst.classify_news_with_llm(state, news_items)
            if llm_result:
                method = "llm"
    except Exception as e:
        utils.log_error(config.ERROR_LOG, f"news_monitor: LLM 分类异常 {e}（回落关键词）")
        llm_result = None

    if llm_result:
        # 用 LLM 结果填 fund — 按 title 匹配回原始 news_items 拿 date/url
        title_to_news = {(n.get("title") or "")[:200]: n for n in news_items}
        fund["summary"] = (
            f"[LLM/{llm_result.get('model','?')}] " + llm_result.get("aggregate_summary", "")
        )
        recent = []
        for it in llm_result.get("items", []):
            t = (it.get("title") or "")[:200]
            src = title_to_news.get(t)
            recent.append({
                "date":       _safe_date_from_item(src) if src else "",
                "title":      t[:120],
                "url":        (src or {}).get("url"),
                "type":       it.get("category"),
                "topic":      t[:60],
                "impact":     it.get("bias"),
                "confidence": it.get("confidence"),
                "rationale":  it.get("rationale"),
            })
        fund["recent_updates"] = recent
        bias = llm_result.get("aggregate_bias", "neutral")
        emergency_detected = bias == "emergency" or any(
            it.get("bias") == "emergency" for it in llm_result.get("items", [])
        )
    else:
        # 关键词回落
        result = summarize_recent(news_items, days=30)
        fund["summary"] = result["summary"]
        fund["recent_updates"] = result["recent_updates"]
        bias = result["bias"]
        emergency_detected = result["emergency_detected"]

    fund["last_check_time"] = utils.now_iso()
    fund["last_check_method"] = method
    # Set next due
    from datetime import timedelta
    next_due_dt = utils.now_local() + timedelta(days=frequency_days)
    fund["next_check_due"] = next_due_dt.isoformat()
    fund["emergency_keywords_detected"] = emergency_detected

    # Bias logic: if whale signals are active, keep positive_with_whale_buy
    has_active_whale = any(
        not w.get("expired") and not utils.is_expired(w.get("expires_at"))
        for w in fund.get("whale_signals", [])
    )
    if has_active_whale and bias not in ("emergency", "negative"):
        fund["bias"] = "positive_with_whale_buy"
    else:
        fund["bias"] = bias

    return True


def _safe_date_from_item(item):
    try:
        from datetime import datetime
        return datetime.fromtimestamp(item.get("date", 0)).date().isoformat()
    except Exception:
        return ""
