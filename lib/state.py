"""
state.json read/write + history maintenance.
"""

import uuid
from . import config
from . import utils


def _ensure_lan_config(s: dict) -> bool:
    """v2.2+：保证 global.lan 节点和 lan_token 存在。返回是否做了修改。"""
    glb = s.setdefault("global", {})
    changed = False
    lan = glb.get("lan")
    if not isinstance(lan, dict):
        glb["lan"] = {"host": "127.0.0.1", "enabled": False, "trust_private": False}
        changed = True
    else:
        if "host" not in lan:
            lan["host"] = "127.0.0.1"
            changed = True
        if "enabled" not in lan:
            lan["enabled"] = lan.get("host") == "0.0.0.0"
            changed = True
        if "trust_private" not in lan:
            lan["trust_private"] = False
            changed = True
    if not glb.get("lan_token"):
        glb["lan_token"] = uuid.uuid4().hex
        changed = True
    return changed


def _ensure_strategy_params(s: dict) -> bool:
    """
    v2.3+：保证 global.strategies[sid].params 节点存在，缺失字段用模块默认 PARAMS 补全。
    AI 提案改 state.global.strategies[sid].params[field] 后，这里读出来就拿到新值。
    延迟 import 避免循环：lib.strategies → lib.state → ...
    """
    glb = s.setdefault("global", {})
    strategies = glb.setdefault("strategies", {})
    changed = False
    try:
        from . import strategies as _strats_mod
        defaults_by_sid = _strats_mod.get_strategy_param_defaults()
    except Exception:
        return False
    for sid, defaults in defaults_by_sid.items():
        slot = strategies.setdefault(sid, {})
        if not isinstance(slot, dict):
            strategies[sid] = slot = {}
        params = slot.get("params")
        if not isinstance(params, dict):
            slot["params"] = dict(defaults)
            changed = True
            continue
        for k, v in defaults.items():
            if k not in params:
                params[k] = v
                changed = True
    return changed


def _ensure_fundamentals_refresh(s: dict) -> bool:
    """v2.3+：fundamentals.refresh_days 默认 1（每天调 LLM 分类）。"""
    fund = s.setdefault("global", {}).setdefault("fundamentals", {})
    if "refresh_days" not in fund:
        fund["refresh_days"] = 1
        return True
    return False


def load_state():
    """Load state from disk."""
    s = utils.read_json(config.STATE_FILE)
    if s is None:
        raise FileNotFoundError(f"State file not found: {config.STATE_FILE}")
    # 自愈：补全 LAN / 策略 params / 基本面刷新频率（首次启动新版本会触发一次写盘）
    changed = False
    changed |= _ensure_lan_config(s)
    changed |= _ensure_strategy_params(s)
    changed |= _ensure_fundamentals_refresh(s)
    if changed:
        try:
            utils.write_json(config.STATE_FILE, s)
        except Exception:
            pass
    return s


def save_state(state):
    """Persist state to disk (atomic)."""
    state.setdefault("global", {})["last_run_time"] = utils.now_iso()
    utils.write_json(config.STATE_FILE, state)


def append_history_entry(item, entry):
    """
    Append one history entry and trim to HISTORY_MAX_ENTRIES.
    Updates highest_observed/lowest_observed.
    """
    item.setdefault("history", []).append(entry)
    if len(item["history"]) > config.HISTORY_MAX_ENTRIES:
        item["history"] = item["history"][-config.HISTORY_MAX_ENTRIES:]

    p = entry.get("price")
    if p is not None:
        if item.get("highest_observed") is None or p > item["highest_observed"]:
            item["highest_observed"] = p
        if item.get("lowest_observed") is None or p < item["lowest_observed"]:
            item["lowest_observed"] = p

    # Update highest_since_first_entry if holding
    pos = item.get("position", {})
    tiers = pos.get("tiers", [])
    if tiers and p is not None:
        first_entry = tiers[0].get("entry_price", p)
        prev_high = pos.get("highest_since_first_entry") or first_entry
        pos["highest_since_first_entry"] = max(prev_high, p)


def append_signal_log(item, log_entry):
    item.setdefault("signals_log", []).append(log_entry)
    if len(item["signals_log"]) > config.SIGNALS_LOG_MAX:
        item["signals_log"] = item["signals_log"][-config.SIGNALS_LOG_MAX:]


def append_recommendation_log(item, log_entry):
    item.setdefault("recommendations_log", []).append(log_entry)
    if len(item["recommendations_log"]) > config.RECOMMENDATIONS_LOG_MAX:
        item["recommendations_log"] = item["recommendations_log"][-config.RECOMMENDATIONS_LOG_MAX:]


def get_threshold(item, key, default=None):
    """Get item's threshold or fall back to default."""
    if default is None:
        default = config.DEFAULT_THRESHOLDS.get(key)
    return item.get("thresholds", {}).get(key, default)


def is_holding(item) -> bool:
    return len(item.get("position", {}).get("tiers", [])) > 0


def compute_position_summary(item):
    """
    Recompute summary fields:
      - avg_entry_price  按 qty_pieces 加权（真实成本均价）
      - total_qty_pct    Σ qty_pct（占计划满仓的总比例，展示用）
      - total_pieces     Σ qty_pieces（真实把数）
    """
    pos = item.get("position", {})
    tiers = pos.get("tiers", [])
    if not tiers:
        pos["avg_entry_price"] = None
        pos["total_qty_pct"] = 0
        pos["total_pieces"] = 0
        return pos

    def _pieces(t):
        # 优先 qty_pieces；缺失回落 qty_pct（向后兼容）
        v = t.get("qty_pieces")
        return v if v is not None else t.get("qty_pct", 0)

    total_pieces = sum(_pieces(t) for t in tiers)
    total_pct    = sum(t.get("qty_pct", 0) for t in tiers)

    if total_pieces <= 0:
        pos["avg_entry_price"] = None
        pos["total_qty_pct"] = 0
        pos["total_pieces"] = 0
        return pos

    weighted = sum(t.get("entry_price", 0) * _pieces(t) for t in tiers)
    pos["avg_entry_price"] = weighted / total_pieces
    pos["total_qty_pct"]   = total_pct
    pos["total_pieces"]    = total_pieces
    return pos


def compute_pnl_pct(item, current_price):
    pos = item.get("position", {})
    avg_entry = pos.get("avg_entry_price")
    if not avg_entry or current_price is None:
        return 0
    return (current_price - avg_entry) / avg_entry
