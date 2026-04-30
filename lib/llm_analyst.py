"""
lib/llm_analyst.py - LLM-powered semantic analysis modules.

Each function:
  - takes structured input
  - calls llm_provider
  - returns structured output (JSON parsed)
  - writes one llm_audit_log entry
"""

import json
import uuid
from typing import Optional

from . import utils
from . import llm_provider


# ============================================================
# Phase 1: News classification (replaces keyword matching)
# ============================================================
NEWS_CLASSIFY_SYSTEM = """You are a CS2 (Counter-Strike 2) skin market analyst.

For each news item, classify its likely impact on existing skin prices.

Categories and default bias:
- new_case      new box -> negative (dilutes old skins)
- new_skin      new skin/finish -> negative
- major         Valve Major or big tournament -> positive
- operation     Premier Season / operation / service medal -> positive
- anti_cheat    VAC / anti-cheat / ban wave -> positive (long-term cleansing)
- policy        Trade policy change -> depends on impact
- tech_update   Engine/animation/perf/bug fix -> neutral
- emergency     Emergency announcement (delisted/permanent ban/major policy) -> emergency
- other         Not in above -> neutral

Requirements:
1. confidence in [0.0, 1.0], reflects your certainty
2. rationale in Chinese, <= 30 chars
3. Output strictly per JSON schema, no markdown, no extra text
4. Handle Chinese titles/contents correctly
"""

NEWS_CLASSIFY_SCHEMA = {
    "type": "object",
    "required": ["items", "aggregate_bias", "aggregate_summary"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "category", "bias", "confidence", "rationale"],
                "properties": {
                    "title":      {"type": "string"},
                    "category":   {"enum": ["new_case", "new_skin", "major", "operation",
                                            "anti_cheat", "policy", "tech_update",
                                            "emergency", "other"]},
                    "bias":       {"enum": ["positive", "negative", "neutral", "emergency"]},
                    "confidence": {"type": "number"},
                    "rationale":  {"type": "string"},
                },
            },
        },
        "aggregate_bias":    {"enum": ["positive", "negative", "neutral",
                                       "neutral_positive", "emergency"]},
        "aggregate_summary": {"type": "string"},
    },
}


def classify_news_with_llm(state: dict, news_items: list,
                           max_items: int = 12) -> Optional[dict]:
    """LLM-based news classification. Returns dict or None on failure."""
    provider = llm_provider.from_state(state)
    if not provider:
        return None
    if not news_items:
        return None

    compact = []
    for n in news_items[:max_items]:
        compact.append({
            "title":    (n.get("title") or "")[:200],
            "contents": (n.get("contents") or "")[:500],
            "date":     n.get("date"),
        })

    user_msg = "Please analyze these CS2 news items:\n\n" + json.dumps(compact, ensure_ascii=False, indent=2)

    try:
        result = provider.chat_json(
            system=NEWS_CLASSIFY_SYSTEM,
            user=user_msg,
            schema=NEWS_CLASSIFY_SCHEMA,
            max_tokens=3500,
            temperature=0.2,
        )
    except Exception as e:
        llm_provider.append_audit(state, "classify_news", "error", str(e))
        return None

    if not isinstance(result, dict) or "items" not in result:
        llm_provider.append_audit(state, "classify_news", "error",
                                  "bad format: " + str(result)[:200])
        return None

    result["model"] = provider.model
    result["analyzed_at"] = utils.now_iso()
    llm_provider.append_audit(
        state, "classify_news", "ok",
        "classified " + str(len(result.get("items", []))) + " items, bias=" + str(result.get("aggregate_bias")),
    )
    return result


# ============================================================
# Phase 2 placeholder
# ============================================================
def parse_whale_announcement(state: dict, text: str) -> Optional[dict]:
    raise NotImplementedError("Phase 2 implementation")


# ============================================================
# Phase 3: Daily review commentary
# ============================================================
DAILY_REVIEW_SYSTEM = """You are a CS2 skin trading advisor. Write a short daily review based on today's data.

Style:
- Chinese, professional but conversational, no platitudes
- Paragraph form, no bullet lists
- Focus: 1) what happened today 2) current position state 3) what to watch tomorrow
- Total length: 200-400 Chinese characters
- Output markdown text directly, no JSON, no code blocks

Avoid:
- Concrete buy/sell advice (rule engine handles this)
- Encouraging frequent trading
- Restating numbers (user can see the dashboard)
- Empty platitudes like "the market is full of opportunities"
"""


def daily_review_commentary(state: dict, *, force: bool = False) -> Optional[dict]:
    """Phase 3: have LLM write a daily review based on portfolio + signals + shadow + bias."""
    if not force and not llm_provider.is_module_enabled(state, "daily_review"):
        return None
    provider = llm_provider.from_state(state)
    if not provider:
        return None

    from . import portfolio as portfolio_mod
    from . import shadow as shadow_mod
    portfolio = portfolio_mod.compute_summary(state)
    shadow_stats = shadow_mod.get_stats()
    shadow_recent = shadow_mod.get_recent(limit=5)

    fund = state.get("global", {}).get("fundamentals", {})
    items = state.get("items", [])
    today_signals = []
    today_str = utils.now_iso()[:10]
    for it in items:
        for s in (it.get("signals_log") or [])[-30:]:
            t = s.get("t", "")
            if t and today_str == t[:10]:
                today_signals.append({
                    "item":  it.get("short_name") or it.get("name"),
                    "label": s.get("label"),
                    "price": s.get("trigger_price") or s.get("price"),
                })

    item_snapshots = []
    for it in items:
        last = (it.get("history") or [{}])[-1]
        pos = it.get("position", {})
        avg = pos.get("avg_entry_price")
        last_price = last.get("price")
        pnl_pct = None
        if avg and last_price:
            pnl_pct = round((last_price - avg) / avg * 100, 2)
        item_snapshots.append({
            "name":         it.get("short_name") or it.get("name"),
            "stage":        it.get("current_stage"),
            "price":        last_price,
            "today_pct":    last.get("today_pct"),
            "position_pct": pos.get("total_qty_pct", 0),
            "pnl_pct":      pnl_pct,
        })

    payload = {
        "date":              today_str,
        "fundamentals_bias": fund.get("bias"),
        "portfolio":         portfolio,
        "shadow_stats":      shadow_stats,
        "shadow_recent":     shadow_recent,
        "today_signals":     today_signals,
        "items":             item_snapshots,
        "active_whale":      [w for w in fund.get("whale_signals", []) if not w.get("expired")],
    }

    user_msg = "Please write today's review based on this data:\n\n" + json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    try:
        text = provider.chat(
            system=DAILY_REVIEW_SYSTEM,
            user=user_msg,
            max_tokens=1200,
            temperature=0.6,
            timeout=90,
        )
    except Exception as e:
        llm_provider.append_audit(state, "daily_review", "error", str(e))
        return None

    review = {
        "text":  (text or "").strip(),
        "model": provider.model,
        "ts":    utils.now_iso(),
        "date":  today_str,
    }
    log = state.setdefault("global", {}).setdefault("ai_review", [])
    log.append(review)
    if len(log) > 60:
        state["global"]["ai_review"] = log[-60:]
    llm_provider.append_audit(state, "daily_review", "ok",
                              "review " + str(len(review["text"])) + " chars, bias=" + str(fund.get("bias")))
    return review


# ============================================================
# Phase 4: Parameter adjustment proposals
# ============================================================
PARAM_PROPOSAL_SYSTEM = """You are a quant strategy iteration advisor. Based on past 30 days of shadow signal backtest data,
suggest whether to adjust key parameters of the rule engine.

Three scopes available:

A) scope="global" — engine-wide defaults, used when items don't have an override
   Fields: fixed_stop_pct, trailing_stop_pct, dedup_window_hours

B) scope="item" — per-item thresholds (item_id required)
   Used by phase-sync-v1 BUY logic + global stop_loss/take_profit on every cycle.
   Fields: today_pct_for_d1, d1_distance_to_r1_min, min_volume_d1,
           rapid_drop_pct_1h, rapid_rise_pct_1h,
           fixed_stop_pct, trailing_stop_pct

C) scope="strategy" — per-strategy params (strategy_id required)
   Used only by the matching strategy. Below are valid (strategy_id, field) pairs:
     rsi-reversion-v1:
       rsi_period (int, default 14)
       rsi_oversold (int 0-50, default 30)
       min_history_days (int >=20)
       min_distance_to_mean (decimal 0-0.2, default 0.03)
     mean-reversion-v1:
       lookback_days (int >=10, default 20)
       z_score_threshold (negative decimal, default -2.0; e.g. -1.8 = looser, -2.5 = stricter)
       min_history_days (int >=20)
       min_distance_to_mean (decimal, default 0.05)
     grid-half-v1:
       grid_step_pct (decimal 0.02-0.10, default 0.05)
       grid_levels (int 2-5, default 3)
       max_pos_per_level (decimal 0-0.30, default 0.10)
       breakout_exit_pct (decimal 0.10-0.40, default 0.20)
       emergency_zscore (negative decimal, default -2.5)
       tplus7_days (int >=1, default 7)

Logic:
- Filter shadow_stats by strategy first to know which knob is causing problems.
- win_rate < 40% with count >= 5 -> threshold too loose -> tighten (e.g. raise rsi_oversold from 30 to 25,
  raise min_distance_to_mean, lower z_score_threshold from -2 to -2.5)
- win_rate > 60% with count < 5 -> threshold too strict -> loosen
- avg_return < 0 with count > 5 -> the signal class loses money overall -> significantly tighten or block_stage
- Don't propose changes if total samples per strategy < 5 (not enough signal).

Each proposal must have:
  - scope (one of global/item/strategy)
  - if scope=item: item_id
  - if scope=strategy: strategy_id (must be one of: rsi-reversion-v1, mean-reversion-v1, grid-half-v1)
  - field (must match field allowed by that scope)
  - current_value, proposed_value (numbers)
  - rationale (<=80 Chinese chars)
  - confidence (0-1)

If nothing to change, return empty proposals list.
Output strict JSON per schema, no markdown wrapping.
"""

PARAM_PROPOSAL_SCHEMA = {
    "type": "object",
    "required": ["proposals", "summary"],
    "properties": {
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["scope", "field", "current_value", "proposed_value", "rationale", "confidence"],
                "properties": {
                    "scope":          {"enum": ["global", "item", "strategy"]},
                    "item_id":        {"type": "string"},
                    "strategy_id":    {"type": "string"},
                    "field":          {"type": "string"},
                    "current_value":  {"type": "number"},
                    "proposed_value": {"type": "number"},
                    "rationale":      {"type": "string"},
                    "confidence":     {"type": "number"},
                },
            },
        },
        "summary":   {"type": "string"},
    },
}


def propose_parameter_changes(state: dict, *, force: bool = False) -> Optional[dict]:
    """Phase 4: LLM analyzes shadow data and proposes parameter changes."""
    if not force and not llm_provider.is_module_enabled(state, "param_proposal"):
        return None
    provider = llm_provider.from_state(state)
    if not provider:
        return None

    from . import shadow as shadow_mod
    shadow_stats = shadow_mod.get_stats()
    if not shadow_stats:
        llm_provider.append_audit(state, "param_proposal", "skip", "shadow has no evaluated data")
        return None

    total_samples = sum(s.get("count", 0) for s in shadow_stats.values())
    if total_samples < 5 and not force:
        llm_provider.append_audit(state, "param_proposal", "skip",
                                  "samples too few (" + str(total_samples) + "), need >=5")
        return None

    items_thresholds = [
        {
            "id":         it["id"],
            "name":       it.get("short_name") or it.get("name"),
            "thresholds": it.get("thresholds", {}),
        }
        for it in state.get("items", [])
    ]
    glb = state.get("global", {})

    # 按策略分组 shadow（让 LLM 看清是哪个策略胜率不行）
    shadow_by_strategy = shadow_mod.get_strategy_summary()

    # 各策略当前 params（合并默认 + state 覆盖）
    strategy_params = {}
    try:
        from . import strategies as _strats_mod
        for sid in ("rsi-reversion-v1", "mean-reversion-v1", "grid-half-v1"):
            strategy_params[sid] = _strats_mod.get_strategy_params(state, sid)
    except Exception:
        pass

    payload = {
        "shadow_stats_by_label":    shadow_stats,
        "shadow_stats_by_strategy": shadow_by_strategy,
        "global_thresholds": {
            "fixed_stop_pct":     glb.get("fixed_stop_pct"),
            "trailing_stop_pct":  glb.get("trailing_stop_pct"),
            "dedup_window_hours": glb.get("dedup_window_hours"),
        },
        "per_item_thresholds": items_thresholds,
        "strategy_params":     strategy_params,
        "active_strategy":     glb.get("active_strategy"),
        "current_bias":        glb.get("fundamentals", {}).get("bias"),
    }

    user_msg = "Shadow backtest + current parameters:\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)

    try:
        result = provider.chat_json(
            system=PARAM_PROPOSAL_SYSTEM,
            user=user_msg,
            schema=PARAM_PROPOSAL_SCHEMA,
            max_tokens=2500,
            temperature=0.2,
        )
    except Exception as e:
        llm_provider.append_audit(state, "param_proposal", "error", str(e))
        return None

    if not isinstance(result, dict) or "proposals" not in result:
        llm_provider.append_audit(state, "param_proposal", "error", "bad format")
        return None

    pending = state.setdefault("global", {}).setdefault("parameter_proposals", [])
    new_proposals = []
    for p in result.get("proposals", []):
        p["id"]         = str(uuid.uuid4())[:8]
        p["created_at"] = utils.now_iso()
        p["status"]     = "pending"
        p["model"]      = provider.model
        pending.append(p)
        new_proposals.append(p)

    if len(pending) > 50:
        state["global"]["parameter_proposals"] = pending[-50:]

    llm_provider.append_audit(
        state, "param_proposal", "ok",
        "generated " + str(len(new_proposals)) + " proposals, samples=" + str(total_samples),
    )
    return {
        "summary":   result.get("summary", ""),
        "proposals": new_proposals,
    }


def apply_proposal(state: dict, proposal_id: str) -> dict:
    """Apply a pending proposal, backing up original value."""
    pending = state.get("global", {}).get("parameter_proposals", [])
    target = next((p for p in pending if p["id"] == proposal_id), None)
    if not target:
        return {"ok": False, "error": "proposal not found"}
    if target["status"] != "pending":
        return {"ok": False, "error": "status is already " + target["status"]}

    field = target["field"]
    new_val = target["proposed_value"]
    scope = target.get("scope")

    if scope == "global":
        glb = state.setdefault("global", {})
        target["original_value"] = glb.get(field)
        glb[field] = new_val
    elif scope == "strategy":
        sid = target.get("strategy_id")
        if not sid:
            return {"ok": False, "error": "scope=strategy requires strategy_id"}
        glb = state.setdefault("global", {})
        slot = glb.setdefault("strategies", {}).setdefault(sid, {})
        params = slot.setdefault("params", {})
        target["original_value"] = params.get(field)
        params[field] = new_val
    elif scope == "item":
        item_id = target.get("item_id")
        item = next((it for it in state.get("items", []) if it["id"] == item_id), None)
        if not item:
            return {"ok": False, "error": "item " + str(item_id) + " not found"}
        thresholds = item.setdefault("thresholds", {})
        target["original_value"] = thresholds.get(field)
        thresholds[field] = new_val
    else:
        return {"ok": False, "error": "unknown scope: " + str(scope)}

    target["status"]     = "applied"
    target["applied_at"] = utils.now_iso()
    target_str = scope + (
        ":" + (target.get("strategy_id") or target.get("item_id") or "")
        if scope in ("strategy", "item") else ""
    )
    llm_provider.append_audit(
        state, "param_proposal", "applied",
        target_str + " " + field + ": " + str(target.get("original_value")) + " -> " + str(new_val),
    )
    return {"ok": True, "proposal": target}


def reject_proposal(state: dict, proposal_id: str) -> dict:
    pending = state.get("global", {}).get("parameter_proposals", [])
    target = next((p for p in pending if p["id"] == proposal_id), None)
    if not target:
        return {"ok": False, "error": "proposal not found"}
    if target["status"] != "pending":
        return {"ok": False, "error": "status is already " + target["status"]}
    target["status"]      = "rejected"
    target["rejected_at"] = utils.now_iso()
    llm_provider.append_audit(state, "param_proposal", "rejected", target["field"])
    return {"ok": True, "proposal": target}
