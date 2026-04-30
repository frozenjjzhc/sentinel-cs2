"""
Sentinel · 均值回归 V1
==========================
基于价格分布的纯统计均值回归策略，用 z-score 触发。

设计理念：
  - 假设：价格围绕一个"公允价值"（20 日均价）波动
  - 触发：当前价距 20 日均价 ≥ 2 个标准差（统计上罕见）
  - 出场：T+7 解锁后，价格回归均值附近

与 RSI 震荡战法的关键差异：
  ✓ 直接看价格分布，不依赖动量平滑 → 极端值反应更快
  ✓ 黑天鹅暴跌时优于 RSI（RSI 平滑慢半拍）
  ✓ 缓慢阴跌时优于 RSI（z-score 等到统计极端才触发，避免接刀）
  ✗ 在低波动品种上可能触发不灵敏（标准差小 → z-score 难达 -2）

适用与 RSI 战法基本一致：
  ✓ 中高存世量主流枪
  ✓ 横盘 / 震荡 / 缓慢阴跌后筑底
  ✗ 单边趋势市
  ✗ 庄家盘控期
"""

from .. import indicators as ind_mod
from .. import signals as signals_mod


META = {
    "id":          "mean-reversion-v1",
    "name":        "Sentinel · 均值回归 V1",
    "tagline":     "z-score 触发 · 价格分布统计反转",
    "version":     "1.0",
    "status":      "experimental",
    "description": (
        "基于价格分布的纯统计均值回归策略。计算 20 日均价 + 标准差，"
        "当前价距均价 ≥ 2 个标准差（z ≤ -2）时触发买入。"
        "与 RSI 战法形成对照组 — RSI 看动能，本策略看价格统计极端值。"
    ),
    "best_for":  "缓慢阴跌后筑底 / 黑天鹅短期暴跌 / 高波动震荡市",
    "weak_for":  "趋势市 / 庄家盘控期 / 低波动品种（σ 太小不触发）",
    "signals":   ["MR-OVERSOLD"],
}

PARAMS = {
    "lookback_days":         20,           # 用 20 日均价 + std
    "z_score_threshold":     -2.0,         # 距均价 ≥ 2σ 才触发
    "min_history_days":      40,           # 至少 40 天数据（让 σ 稳定）
    "min_distance_to_mean":  0.05,         # 双保险：距均价 ≥ 5%（覆盖 1% 手续费 + 利润）
    "blocked_stages":        ["MARKUP", "DISTRIBUTION", "MARKDOWN"],
}


def _p(state, key):
    """读 state.global.strategies['mean-reversion-v1'].params[key]，缺失回落 PARAMS。"""
    from . import get_strategy_params
    return get_strategy_params(state, META["id"]).get(key, PARAMS[key])


def evaluate_buy_signals(state, item, ind, stage, market) -> list:
    history = item.get("history", [])
    P = ind.get("P")
    if P is None:
        return []

    # 1. 仓位上限
    pos = item.get("position", {})
    if pos.get("total_qty_pct", 0) >= 1.0:
        return []

    # 2. 阶段过滤
    if stage in _p(state, "blocked_stages"):
        return []

    # 3. 历史天数充足
    days_of_data = len(history) // 144
    if days_of_data < _p(state, "min_history_days"):
        return []

    # 4. 庄家活跃 → 避开
    if signals_mod.get_active_whale_signal(state, item):
        return []

    # 5. 计算日线 z-score
    lookback = _p(state, "lookback_days")
    z, mean_p, std_p = ind_mod.compute_daily_zscore(history, lookback_days=lookback)
    if z is None or z > _p(state, "z_score_threshold"):
        return []

    # 6. 距均线绝对距离够大
    if not mean_p or mean_p <= 0:
        return []
    distance = (mean_p - P) / mean_p
    if distance < _p(state, "min_distance_to_mean"):
        return []

    return [{
        "label":    "MR-OVERSOLD",
        "category": "BUY",
        "priority": 8,
        "advice":   (
            f"距 {lookback} 日均价 z={z:.2f}σ "
            f"(-{distance*100:.1f}%)，统计意义上的极端超卖位"
        ),
        "next_tier": 1,
        "qty":       0.3,
        "z_score":   z,
        "distance_to_mean": distance,
        "lookback_mean":    mean_p,
        "lookback_std":     std_p,
    }]
