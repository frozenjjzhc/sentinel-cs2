"""
Signal evaluation: BUY (5 types), SELL (4 types), and special signals.
This is the MVP — focuses on BUY-WHALE, BUY-WASHOUT, BUY-LAUNCH for now.
SELL signals are stubs (will be fully implemented in monitor_slow.py).

Bias-driven 调节（A+B 增强）：
  A. BUY 信号：emergency 完全屏蔽；正负 bias 调整 priority
  B. SELL 信号：止损阈值按 bias 缩放（负面 bias 收紧）
"""

from . import state
from . import utils


# ============================================================
# Bias modifier (A + B)
# ============================================================
# A. BUY 信号优先级修正
BIAS_BUY_PRIORITY_MOD = {
    "positive":                 +1.0,
    "positive_with_whale_buy":  +1.0,
    "neutral_positive":         +0.5,
    "neutral":                   0.0,
    "negative":                 -1.0,
    "emergency":               -10.0,   # 实质上屏蔽（priority 变成负数）
}


def is_buy_blocked_by_bias(bias: str) -> bool:
    """emergency bias 完全屏蔽所有 BUY 信号。"""
    return bias == "emergency"


def apply_bias_to_buy_signals(signals: list, bias: str) -> list:
    """对 BUY 信号列表应用 bias 调节，返回新列表（不修改原对象）。"""
    if not signals:
        return signals
    if is_buy_blocked_by_bias(bias):
        # 整组屏蔽，返回带说明的空 placeholder（caller 可决定显示与否）
        return []
    mod = BIAS_BUY_PRIORITY_MOD.get(bias, 0.0)
    if mod == 0:
        return signals
    out = []
    for s in signals:
        s2 = dict(s)
        s2["priority"] = s2.get("priority", 0) + mod
        s2["bias_applied"] = bias
        s2["bias_priority_mod"] = mod
        out.append(s2)
    return out


# B. SELL 阈值按 bias 缩放
# 返回：止损 pct 乘数（< 1 = 更紧）
BIAS_STOP_MULT = {
    "positive":                 1.00,    # 不变
    "positive_with_whale_buy":  1.10,    # 略放宽（庄家+正面，给更多空间）
    "neutral_positive":         1.00,
    "neutral":                  1.00,
    "negative":                 0.70,    # 收紧 30% (-15% → -10.5%)
    "emergency":                0.50,    # 收紧 50% (-15% → -7.5%)
}


def bias_stop_multiplier(bias: str) -> float:
    return BIAS_STOP_MULT.get(bias, 1.0)


# 取盈乘数（< 1 = 更早止盈，> 1 = 让利润奔跑）
BIAS_TP_MULT = {
    "positive":                 1.10,    # +20% → +22%
    "positive_with_whale_buy":  1.30,    # 让第三档奔跑（+70% → +91%）
    "neutral_positive":         1.05,
    "neutral":                  1.00,
    "negative":                 0.80,    # 提早止盈 (+20% → +16%)
    "emergency":                0.60,    # 立即清仓导向 (+20% → +12%)
}


def bias_tp_multiplier(bias: str) -> float:
    return BIAS_TP_MULT.get(bias, 1.0)


def get_current_bias(state_obj) -> str:
    return state_obj.get("global", {}).get("fundamentals", {}).get("bias", "neutral")


# ============================================================
# Helper: find next tier to add
# ============================================================
def get_next_tier(item):
    pos = item.get("position", {})
    tiers_count = len(pos.get("tiers", []))
    if tiers_count == 0:
        return 1, 0.30
    elif tiers_count == 1:
        return 2, 0.30
    elif tiers_count == 2:
        return 3, 0.40
    return None, 0


# ============================================================
# Whale signal helpers
# ============================================================
def whale_signals_enabled(state_obj) -> bool:
    """用户可在设置中关闭庄家相关逻辑。默认开启（False = 不屏蔽）。"""
    return not state_obj.get("global", {}).get("ignore_whale_signals", False)


def get_active_whale_signal(state_obj, item):
    """Find a non-expired whale signal applicable to this item.
    返回 None 如果用户屏蔽了庄家信号。"""
    if not whale_signals_enabled(state_obj):
        return None
    fundamentals = state_obj.get("global", {}).get("fundamentals", {})
    for whale in fundamentals.get("whale_signals", []):
        if whale.get("expired"):
            continue
        if utils.is_expired(whale.get("expires_at")):
            continue
        applicable = whale.get("applicable_items", [])
        if item["id"] in applicable:
            return whale
    return None


def get_whale_buy_in_price(item):
    """Read item's whale buy-in price."""
    return item.get("whale_buy_in_price")


# ============================================================
# Dedup
# ============================================================
def is_duplicate(item, label, dedup_window_minutes):
    """Check if same label was pushed within dedup window."""
    last_pushed = item.get("last_signal_pushed")
    last_time = item.get("last_signal_time")
    if last_pushed != label or not last_time:
        return False
    minutes_since = utils.hours_since(last_time) * 60
    return minutes_since < dedup_window_minutes


# ============================================================
# BUY signals (10min frequency)
# ============================================================
def evaluate_buy_signals(state_obj, item, ind, stage, market) -> list:
    """
    Returns a list of signal dicts: [{label, category, advice, next_tier, qty}, ...]
    Only ONE signal per call (highest priority wins).
    """
    pos = item.get("position", {})
    if pos.get("total_qty_pct", 0) >= 1.0:
        return []   # Full position, no buy signals

    K = item.get("key_levels", {})
    T = item.get("thresholds", {})
    P = ind.get("P")
    if P is None:
        return []

    market_index = market.get("market_index")
    fundamentals = state_obj.get("global", {}).get("fundamentals", {})
    bias = fundamentals.get("bias", "neutral")

    next_tier, qty = get_next_tier(item)

    # ------------------------------------------------------------
    # BUY-WASHOUT (highest priority): SHAKEOUT stage
    # ------------------------------------------------------------
    if stage == "SHAKEOUT":
        return [{
            "label": "BUY-WASHOUT",
            "category": "BUY",
            "priority": 10,
            "advice": f"庄家洗盘买点（急跌未破前低），可建第{next_tier}档（{int(qty*100)}%）",
            "next_tier": next_tier,
            "qty": qty,
        }]

    # ------------------------------------------------------------
    # BUY-WHALE: price near whale floor
    # ------------------------------------------------------------
    whale = get_active_whale_signal(state_obj, item)
    whale_buy_in = get_whale_buy_in_price(item)
    if whale and whale_buy_in:
        if abs(P - whale_buy_in) / whale_buy_in < 0.02:   # within 2%
            return [{
                "label": "BUY-WHALE",
                "category": "BUY",
                "priority": 9,
                "advice": f"价格触庄家承诺底 ¥{whale_buy_in}，可跟买第{next_tier}档（{int(qty*100)}%）",
                "next_tier": next_tier,
                "qty": qty,
            }]

    # ------------------------------------------------------------
    # BUY-LAUNCH: MARKUP stage with breakout
    # ------------------------------------------------------------
    R1 = K.get("resistance_1")
    if (
        stage == "MARKUP"
        and R1 and P > R1 * 1.015
        and market_index and market_index > 1014
        and (ind.get("volume_quality") == "bullish_breakout" or ind.get("momentum_score", 0) >= 1)
    ):
        return [{
            "label": "BUY-LAUNCH",
            "category": "BUY",
            "priority": 8,
            "advice": f"拉升突破 R1=¥{R1}，建第{next_tier}档（{int(qty*100)}%）",
            "next_tier": next_tier,
            "qty": qty,
        }]

    # ------------------------------------------------------------
    # BUY-PULLBACK (D4): pullback to a recent C-signal price
    # ------------------------------------------------------------
    recent_c = None
    for rec in reversed(item.get("recommendations_log", [])):
        if rec.get("category") in ("C", "BUY-LAUNCH") and rec.get("trigger_price"):
            t_str = rec.get("t")
            if t_str and utils.hours_since(t_str) <= 24:
                recent_c = rec
                break

    if recent_c:
        breakout_price = recent_c["trigger_price"]
        # Price now in [-3%, +3%] of breakout_price
        if breakout_price * 0.97 <= P <= breakout_price * 1.03:
            # Find pullback low since breakout
            since = []
            for h in item.get("history", []):
                if h.get("t", "") > recent_c["t"]:
                    since.append(h)
            if len(since) >= 3:
                pullback_low = min(s.get("price", P) for s in since if s.get("price"))
                if (
                    pullback_low < breakout_price * 0.99
                    and P > pullback_low * 1.01
                    and ind.get("momentum_score", 0) >= 1
                ):
                    return [{
                        "label": "BUY-PULLBACK",
                        "category": "BUY",
                        "priority": 7,
                        "advice": f"突破后缩量回踩再启动，高质量入场；建第{next_tier}档（{int(qty*100)}%）",
                        "next_tier": next_tier,
                        "qty": qty,
                    }]

    # ------------------------------------------------------------
    # BUY-ACCUMULATE: ACCUMULATION + low position
    # ------------------------------------------------------------
    if stage == "ACCUMULATION" and pos.get("total_qty_pct", 0) < 0.3:
        return [{
            "label": "BUY-ACCUMULATE",
            "category": "BUY",
            "priority": 5,
            "advice": "吸筹阶段，可小仓位试探（10-15%）",
            "next_tier": 1,
            "qty": 0.15,
        }]

    return []


# ============================================================
# Wrap evaluate_buy_signals — 让所有 BUY 信号都过 bias 调节（A）
# ============================================================
_original_evaluate_buy_signals = evaluate_buy_signals


def evaluate_buy_signals(state_obj, item, ind, stage, market):
    raw = _original_evaluate_buy_signals(state_obj, item, ind, stage, market)
    bias = get_current_bias(state_obj)
    return apply_bias_to_buy_signals(raw, bias)


# ============================================================
# Legacy holding alerts (independent stream)
# ============================================================
def check_legacy_alerts(item) -> list:
    """
    Returns a list of alert dicts that should be pushed.
    Marks them as fired in state immediately to prevent re-fire.
    """
    legacy = item.get("legacy_holding")
    if not legacy:
        return []

    P = None
    if item.get("history"):
        P = item["history"][-1].get("price")
    if P is None:
        return []

    triggered = []
    for alert in legacy.get("recovery_alerts", []):
        if alert.get("fired"):
            continue
        if P >= alert.get("price", float("inf")):
            alert["fired"] = True
            alert["fired_at"] = utils.now_iso()
            alert["fired_price"] = P
            triggered.append(alert)
    return triggered


# ============================================================
# A-class stop-loss (for held positions)
# ============================================================
def evaluate_stop_loss(state_obj, item, ind) -> list:
    """
    Evaluates A-class stops. Returns list (usually 0 or 1).
    Note: with T+7, these are "advance warnings" — actual sell is delayed.

    B 增强：bias 缩放止损阈值
      negative  → 阈值 × 0.7 (更紧，更早触发)
      emergency → 阈值 × 0.5 (急速止损)
      positive  → 阈值不变（让 trailing 给空间）
    """
    if not state.is_holding(item):
        return []

    pos = item.get("position", {})
    K = item.get("key_levels", {})
    P = ind.get("P")
    prev = ind.get("prev")
    if P is None:
        return []

    avg_entry = pos.get("avg_entry_price")
    highest = pos.get("highest_since_first_entry")
    T = item.get("thresholds", {})

    fixed_pct_raw = T.get("fixed_stop_pct", 0.15)
    trailing_pct_raw = T.get("trailing_stop_pct", 0.12)
    rapid_drop_raw = T.get("rapid_drop_pct_1h", 7)

    # === B 增强：按 bias 缩放止损阈值 ===
    bias = get_current_bias(state_obj)
    stop_mult = bias_stop_multiplier(bias)
    fixed_pct = fixed_pct_raw * stop_mult
    trailing_pct = trailing_pct_raw * stop_mult
    rapid_drop = rapid_drop_raw * stop_mult
    bias_tag = f"[bias={bias} ×{stop_mult}]" if stop_mult != 1.0 else ""

    # A1 fixed stop: whale-floor-aware（受 ignore_whale_signals 开关影响）
    whale_stop_price = T.get("use_whale_stop_price")
    whale_active_until = item.get("whale_active_until")
    use_whale_stop = (
        whale_signals_enabled(state_obj)
        and whale_stop_price
        and whale_active_until
        and not utils.is_expired(whale_active_until)
    )
    if use_whale_stop:
        if P < whale_stop_price:
            return [{
                "label": "A1-WHALE-STOP",
                "category": "SELL",
                "priority": 10,
                "advice": f"跌破庄家承诺底 ¥{whale_stop_price}！T+7 解锁后立即清仓",
                "bias_applied": bias,
            }]
    elif avg_entry and P < avg_entry * (1 - fixed_pct):
        return [{
            "label": "A1-FIXED-STOP",
            "category": "SELL",
            "priority": 10,
            "advice": f"固定止损 -{fixed_pct*100:.1f}%！T+7 解锁后清仓 {bias_tag}",
            "bias_applied": bias,
            "bias_stop_mult": stop_mult,
        }]

    # A2 trailing stop
    if highest and avg_entry and highest > avg_entry:
        if P < highest * (1 - trailing_pct):
            return [{
                "label": "A2-TRAILING-STOP",
                "category": "SELL",
                "priority": 9,
                "advice": f"移动止损：从最高 ¥{highest:.2f} 回撤 {trailing_pct*100:.1f}% {bias_tag}",
                "bias_applied": bias,
                "bias_stop_mult": stop_mult,
            }]

    # A3 strong support break
    strong = K.get("strong_support")
    if strong and P < strong:
        return [{
            "label": "A3-STRONG-SUPPORT",
            "category": "SELL",
            "priority": 9,
            "advice": f"跌破强支撑 ¥{strong}，建议先减半观察",
            "bias_applied": bias,
        }]

    # A4 1H rapid drop
    if prev and prev != P:
        drop_pct = (P - prev) / prev
        if drop_pct < -rapid_drop / 100:
            return [{
                "label": "A4-RAPID-DROP",
                "category": "SELL",
                "priority": 8,
                "advice": f"1H 急跌 {drop_pct*100:.1f}%，先观察是否破前低 {bias_tag}",
                "bias_applied": bias,
                "bias_stop_mult": stop_mult,
            }]

    return []


# ============================================================
# Take-profit signals (B 增强 — 新功能)
# ============================================================
def evaluate_take_profit(state_obj, item, ind) -> list:
    """
    分档止盈信号。读 state.global.tier_plan.tp_levels_from_avg 作为基准，
    按 bias 缩放后判断当前是否触达。

    bias=positive_with_whale_buy → tp 拉到 1.3x（让利润奔跑）
    bias=negative                → tp 缩到 0.8x（提早止盈）
    bias=emergency               → tp 缩到 0.6x（导向清仓）
    """
    if not state.is_holding(item):
        return []

    pos = item.get("position", {})
    avg_entry = pos.get("avg_entry_price")
    if not avg_entry:
        return []

    P = ind.get("P")
    if P is None:
        return []

    tier_plan = state_obj.get("global", {}).get("tier_plan", {})
    tp_levels = tier_plan.get("tp_levels_from_avg", [0.20, 0.40, 0.70])
    tp_close = tier_plan.get("tp_close_pct", [0.30, 0.30, 0.0])

    bias = get_current_bias(state_obj)
    tp_mult = bias_tp_multiplier(bias)

    executed = set(pos.get("tp_executed", []))   # ["TP1", "TP2"...]

    # 找第一个未执行的档
    for i, level in enumerate(tp_levels):
        label = f"TP{i+1}"
        if label in executed:
            continue
        adjusted_level = level * tp_mult
        target_price = avg_entry * (1 + adjusted_level)
        if P >= target_price:
            close_pct = tp_close[i] if i < len(tp_close) else 0.30
            advice = (
                f"达 {label} 目标 ¥{target_price:.2f}（基准 +{level*100:.0f}% × bias 乘数 {tp_mult}）"
                f" → T+7 解锁后卖出 {int(close_pct*100)}%"
                if close_pct > 0 else
                f"达 {label} 目标 ¥{target_price:.2f} → 让利润奔跑（A2 移动止损保护）"
            )
            return [{
                "label": f"SELL-{label}",
                "category": "SELL",
                "priority": 7,
                "advice": advice,
                "tp_level": label,
                "target_price": target_price,
                "close_pct": close_pct,
                "bias_applied": bias,
                "bias_tp_mult": tp_mult,
            }]

    return []
