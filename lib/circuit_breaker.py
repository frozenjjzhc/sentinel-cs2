"""
Emergency halt mechanism.
When market crashes or any item drops dramatically, suspend BUY signals.
"""

from . import config
from . import utils


def _change_over_hours(history: list, hours: float) -> float:
    """Compute price change over last N hours (10min entries)."""
    if not history or len(history) < 2:
        return 0
    n = max(1, int(hours * 6))   # 6 entries per hour
    if len(history) <= n:
        return 0
    p_now = history[-1].get("price")
    p_then = history[-1 - n].get("price")
    if not p_now or not p_then:
        return 0
    return (p_now - p_then) / p_then


def _market_change_over_entries(history: list, n_entries: int) -> float:
    """Track market index change over last N history entries."""
    if not history or len(history) < n_entries + 1:
        return 0
    m_now = history[-1].get("market_index")
    m_then = history[-(n_entries + 1)].get("market_index")
    if not m_now or not m_then:
        return 0
    return (m_now - m_then) / m_then


def check_circuit_breaker(state: dict) -> tuple:
    """
    Returns (active: bool, reason: str | None).
    Walks all items + market to detect emergency conditions.
    """
    items = state.get("items", [])
    if not items:
        return False, None

    # Use first item's history as a market-time-series anchor
    anchor = items[0].get("history", [])
    if not anchor:
        return False, None

    # 1. Market 1-day drop
    market_1d = _market_change_over_entries(anchor, 144)   # 144 × 10min = 24h
    if market_1d <= config.CB_MARKET_DAILY_DROP:
        return True, f"MARKET_CRASH_1D ({market_1d*100:.2f}%)"

    # 2. Market 3-day cumulative drop
    market_3d = _market_change_over_entries(anchor, 432)   # 72h
    if market_3d <= config.CB_MARKET_3D_DROP:
        return True, f"MARKET_DECLINE_3D ({market_3d*100:.2f}%)"

    # 3. Any item daily drop ≥ 15%
    for item in items:
        change_24h = _change_over_hours(item.get("history", []), 24)
        if change_24h <= config.CB_ITEM_DAILY_DROP:
            return True, f"ITEM_CRASH {item['id']} ({change_24h*100:.2f}%)"

    # 4. Emergency keywords from fundamentals
    fund = state.get("global", {}).get("fundamentals", {})
    if fund.get("emergency_keywords_detected"):
        return True, "EMERGENCY_NEWS"

    return False, None


def activate(state: dict, reason: str) -> dict:
    cb = state.setdefault("global", {}).setdefault("circuit_breaker", {})
    cb["active"] = True
    cb["activated_at"] = utils.now_iso()
    cb["reason"] = reason
    cb["scheduled_review_at"] = utils.now_iso()   # let next slow run review
    return cb


def deactivate(state: dict):
    cb = state.get("global", {}).get("circuit_breaker", {})
    cb["active"] = False
    cb["deactivated_at"] = utils.now_iso()


def is_active(state: dict) -> bool:
    return state.get("global", {}).get("circuit_breaker", {}).get("active", False)


def auto_review(state: dict) -> bool:
    """
    Check if circuit breaker should be deactivated.
    Returns True if just deactivated.
    """
    cb = state.get("global", {}).get("circuit_breaker", {})
    if not cb.get("active"):
        return False

    activated_at = cb.get("activated_at")
    if not activated_at:
        return False

    hours_active = utils.hours_since(activated_at)
    if hours_active < config.CB_REVIEW_INTERVAL_HOURS:
        return False

    # Re-check current conditions
    active_now, reason_now = check_circuit_breaker(state)
    if not active_now:
        deactivate(state)
        return True

    # Update reason and reset review clock
    cb["reason"] = reason_now
    cb["scheduled_review_at"] = utils.now_iso()
    return False
