"""
Sentinel · 半仓小网格 V1
==========================
基于价格区间的网格交易策略，用半仓资金分配到多个买入档。

设计理念：
  - 网格中心 = MA30（动态锚定，避免价格永久离开网格）
  - 上下各 3 档，间距 5%
  - 每档资金 = 该品种预算的 10%（5 档共 ~50% = 半仓）
  - 另一半留作"应急储备"（z < -2.5σ 时一次性加仓）
  - 价格突破 ±20% → 主动退出网格

核心 edge：
  - 不依赖趋势判断，靠区间内反复震荡赚小利润
  - 单循环净利约 4.2%（5% 档距 - 1% 卖出手续费）
  - 第三方平台只收卖出手续费，买入无费 → 数学上很友好

T+7 适配：
  - 每个买入档记录 unlock_time（买入时间 + 7 天）
  - 卖出信号必须等 unlock_time 之后才触发

适用：
  ✓ 横盘 / 窄幅震荡市
  ✓ 中高存世量主流枪
  ✗ 单边趋势市（价格突破 ±20% 退出）
  ✗ 庄家盘控期
  ✗ 流动性极差品种（成交不连续，levels 跳过）
"""

from datetime import datetime, timedelta
from .. import indicators as ind_mod
from .. import signals as signals_mod
from .. import utils


META = {
    "id":          "grid-half-v1",
    "name":        "Sentinel · 半仓小网格 V1",
    "tagline":     "区间震荡反复套利 · 半仓 + 应急储备",
    "version":     "1.0",
    "status":      "experimental",
    "description": (
        "上下各 3 档、间距 5% 的网格策略。网格中心动态锚定 MA30，"
        "每档投入 10% 仓位（5 档共半仓），另一半作为应急储备。"
        "T+7 感知：买入档独立计算解锁时间，未解锁不触发卖出。"
        "单循环净利约 4.2%，靠反复触达档位累积收益。"
    ),
    "best_for":  "纯横盘 / 窄幅震荡 / 价格中枢稳定的主流枪",
    "weak_for":  "单边趋势 / 庄家盘控 / 流动性极差品种",
    "signals":   ["GRID-BUY-L*", "GRID-SELL-L*", "GRID-EMERGENCY", "GRID-EXIT"],
}

PARAMS = {
    "grid_step_pct":          0.05,    # 每档 5%
    "grid_levels":            3,        # 上下各 3 档
    "max_pos_per_level":      0.10,    # 每档 10% 资金
    "min_history_days":       30,       # 最少 30 天数据
    "blocked_stages":         ["MARKUP", "DISTRIBUTION", "MARKDOWN"],
    "breakout_exit_pct":      0.20,    # 价格突破 ±20% → 退出网格
    "emergency_zscore":       -2.5,     # z < -2.5 触发应急储备一次性加仓
    "tplus7_days":            7,        # T+7 锁仓
}


def _p(state, key):
    """读 state.global.strategies['grid-half-v1'].params[key]，缺失回落 PARAMS。"""
    from . import get_strategy_params
    return get_strategy_params(state, META["id"]).get(key, PARAMS[key])


# ============================================================
# 网格状态初始化（由 backend toggle_grid 调用，用最新 state.params）
# ============================================================
def _init_grid_state(item, ma_30, state=None):
    """首次启用网格策略时初始化 item.grid_state。"""
    # 兼容旧调用：若没传 state 则用模块默认 PARAMS
    if state is None:
        levels = PARAMS["grid_levels"]
        step_pct = PARAMS["grid_step_pct"]
        tier_size = PARAMS["max_pos_per_level"]
    else:
        levels = _p(state, "grid_levels")
        step_pct = _p(state, "grid_step_pct")
        tier_size = _p(state, "max_pos_per_level")
    return {
        "active":         True,
        "center_price":   ma_30,
        "step_pct":       step_pct,
        "levels":         levels,
        "tier_size_pct":  tier_size,
        "reserve_used":   False,
        "exited":         False,
        "positions":      [
            {"level": -i, "qty_pieces": 0, "entry_price": None, "entry_time": None, "unlock_time": None}
            for i in range(1, levels + 1)
        ],
        "initialized_at": utils.now_iso(),
    }


def _ensure_grid_state(item, ma_30):
    grid = item.get("grid_state")
    if not grid or not grid.get("active"):
        return None
    if grid.get("center_price") and ma_30:
        drift = abs(ma_30 - grid["center_price"]) / grid["center_price"]
        if drift > 0.10:
            grid["center_price"] = ma_30
    return grid


def _level_target_price(center, level, step_pct):
    """档位 → 目标价。level 是负数（买入档）或正数（卖出档）。"""
    return center * (1 + level * step_pct)


def _current_level(P, center, step_pct):
    """当前价对应的档位索引（向下取整，比如 -2.3% 算 0 档不算 -1 档）。"""
    if not center or center <= 0:
        return 0
    deviation = (P - center) / center
    return int(deviation / step_pct)   # round towards zero in python's int()


# ============================================================
# BUY 信号评估
# ============================================================
def evaluate_buy_signals(state, item, ind, stage, market) -> list:
    P = ind.get("P")
    if P is None:
        return []

    # 1. 网格状态检查（用户必须先启用此品种的网格）
    ma_30 = ind.get("ma_month")  # 用 ma_month 作为中心（30 日均价）
    if not ma_30 or ma_30 <= 0:
        return []
    grid = _ensure_grid_state(item, ma_30)
    if not grid:
        return []
    if grid.get("exited"):
        return []   # 已突破退出，等待手动重启

    # 2. 阶段过滤
    if stage in _p(state, "blocked_stages"):
        return []

    # 3. 历史足够
    days_of_data = len(item.get("history", [])) // 144
    if days_of_data < _p(state, "min_history_days"):
        return []

    # 4. 庄家活跃 → 避开
    if signals_mod.get_active_whale_signal(state, item):
        return []

    # 5. 检查是否需要应急储备触发
    z, _, _ = ind_mod.compute_daily_zscore(item.get("history", []), lookback_days=20)
    if z is not None and z < _p(state, "emergency_zscore") and not grid.get("reserve_used"):
        return [{
            "label":    "GRID-EMERGENCY",
            "category": "BUY",
            "priority": 9,
            "advice":   f"z={z:.2f}σ 极端超卖，触发应急储备一次性加仓另一半（30%）",
            "qty_pct":  0.50,
            "qty_pieces": 0,
            "grid_action": "emergency",
        }]

    # 6. 突破退出检查
    breakout_pct = _p(state, "breakout_exit_pct")
    deviation = (P - grid["center_price"]) / grid["center_price"]
    if abs(deviation) > breakout_pct:
        grid["exited"] = True
        return [{
            "label":    "GRID-EXIT",
            "category": "ALERT",
            "priority": 8,
            "advice":   (
                f"价格距网格中心 {deviation*100:+.1f}%，超出 ±{int(breakout_pct*100)}%"
                f"，已自动退出网格策略。回到中心 ±5% 内可手动重启。"
            ),
        }]

    # 7. 普通网格触发
    target_level = _current_level(P, grid["center_price"], grid["step_pct"])
    if target_level <= -1 and target_level >= -grid["levels"]:
        for pos in grid["positions"]:
            if pos["level"] == target_level and pos["qty_pieces"] == 0:
                level_price = _level_target_price(grid["center_price"], target_level, grid["step_pct"])
                pct_per_level = _p(state, "max_pos_per_level")
                return [{
                    "label":    f"GRID-BUY-L{abs(target_level)}",
                    "category": "BUY",
                    "priority": 7,
                    "advice":   (
                        f"价格触 -{abs(target_level)} 档（¥{level_price:.0f}），"
                        f"建议买 1 把（每档 {int(pct_per_level*100)}% 仓位），"
                        f"7 天后可挂卖到 +1 档（约 +{grid['step_pct']*100:.0f}% 净利）"
                    ),
                    "qty_pieces":   1,
                    "level":         target_level,
                    "grid_action":   "buy",
                    "level_price":   level_price,
                }]

    return []


# ============================================================
# SELL 信号评估（网格独有，与 stop_loss / TP 并存）
# ============================================================
def evaluate_sell_signals(state, item, ind) -> list:
    """
    检查网格内已持仓的档是否有卖点 + T+7 已解锁。
    """
    P = ind.get("P")
    if P is None:
        return []

    grid = item.get("grid_state")
    if not grid or not grid.get("active") or grid.get("exited"):
        return []

    center = grid.get("center_price")
    if not center:
        return []

    now = datetime.now().astimezone()
    # 找已解锁 + 当前价高于其成本至少 1 个 step 的档
    for pos in grid.get("positions", []):
        if pos.get("qty_pieces", 0) <= 0:
            continue
        unlock_time_str = pos.get("unlock_time")
        if not unlock_time_str:
            continue
        try:
            unlock_time = utils.parse_iso(unlock_time_str)
        except Exception:
            continue
        if now < unlock_time:
            continue   # 仍在 T+7 锁仓中

        entry = pos.get("entry_price", 0)
        if entry <= 0:
            continue

        # 卖出条件：当前价 ≥ entry × (1 + 1 个档距)
        target_sell_price = entry * (1 + grid["step_pct"])
        if P >= target_sell_price:
            net_profit_pct = (P * 0.99 - entry) / entry  # 扣 1% 卖出费
            return [{
                "label":      f"GRID-SELL-L{abs(pos['level'])}",
                "category":   "SELL",
                "priority":   9,                 # 高优先级（赚钱机会）
                "advice":     (
                    f"GRID -{abs(pos['level'])} 档已解锁，当前价 ¥{P:.0f} 高于成本 ¥{entry:.0f}，"
                    f"净收益约 {net_profit_pct*100:.2f}%，建议卖出"
                ),
                "level":         pos["level"],
                "entry_price":   entry,
                "qty_pieces":    pos["qty_pieces"],
                "grid_action":   "sell",
            }]

    return []


# ============================================================
# 网格成交后的状态更新（由 monitor 调用）
# ============================================================
def apply_buy_fill(item, signal, fill_price, state=None):
    """
    网格 BUY 信号被推送 + 用户确认买入后调用。
    state 可选；若提供，则 T+N 锁仓天数从 state 读，否则用模块默认 PARAMS。
    """
    grid = item.get("grid_state")
    if not grid:
        return
    level = signal.get("level")
    if state is not None:
        tplus_days = _p(state, "tplus7_days")
    else:
        tplus_days = PARAMS["tplus7_days"]
    for pos in grid["positions"]:
        if pos["level"] == level:
            pos["qty_pieces"] = signal.get("qty_pieces", 1)
            pos["entry_price"] = fill_price
            pos["entry_time"] = utils.now_iso()
            now_dt = datetime.now().astimezone()
            pos["unlock_time"] = (now_dt + timedelta(days=tplus_days)).isoformat()
            break


def apply_sell_fill(item, signal):
    """网格 SELL 信号被推送 + 用户确认卖出后调用。"""
    grid = item.get("grid_state")
    if not grid:
        return
    level = signal.get("level")
    for pos in grid["positions"]:
        if pos["level"] == level:
            pos["qty_pieces"] = 0
            pos["entry_price"] = None
            pos["entry_time"] = None
            pos["unlock_time"] = None
            break
