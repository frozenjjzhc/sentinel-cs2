"""
Sentinel · RSI 震荡 V1
==========================
横盘 / 震荡市超卖反转策略。基于日线 RSI(14)。

设计理念：
  - 1% 第三方平台手续费 → 反转 3% 即可盈利
  - T+7 锁仓 → 与 RSI MR 自然 7-21 天周期吻合
  - 高存世量品种散户主导 → MR 假设成立

适用范围（重要）：
  ✓ 中高存世量主流枪（AK 红线 / AWP 大蛇王 / M4A4 红色 DDPAT 等）
  ✓ 横盘震荡市（COILING / 中性阶段）
  ✓ 庄家不活跃期（无活跃庄家信号）
  ✗ 稀缺品种（喧嚣 FN / 手套等，庄家可主导）
  ✗ 趋势市（MARKUP / DISTRIBUTION → RSI 失效）
  ✗ 新品种 / 历史 < 60 天

参数（保守起步，shadow 跑出数据后再调）：
  RSI(14) < 30 → 入场
  距月线均价 ≥ 3% → 反转空间足够
  无活跃庄家信号 → 避免被盘控
"""

from .. import indicators as ind_mod
from .. import signals as signals_mod


META = {
    "id":          "rsi-reversion-v1",
    "name":        "Sentinel · RSI 震荡 V1",
    "tagline":     "横盘市超卖反转 · 日线 RSI(14)",
    "version":     "1.0",
    "status":      "experimental",
    "description": (
        "横盘 / 震荡市超卖反转策略。利用日线 RSI(14) 识别极端超卖位，"
        "在距月线均价 ≥ 3% 的位置入场，等待 7-21 天均值回归。"
        "在第三方 1% 手续费 + T+7 锁仓的现实约束下，与 RSI MR 的天然节奏吻合。"
    ),
    "best_for":  "震荡市 / 高存世量主流枪 / 庄家不活跃期",
    "weak_for":  "趋势市 / 稀缺品种被盘控期 / 新品种",
    "signals":   ["RSI-OVERSOLD"],
}

PARAMS = {
    "rsi_period":           14,            # 日线 14 天 RSI
    "rsi_oversold":         30,            # < 30 触发
    "rsi_overbought":       70,            # > 70 提示出场（仅展示用）
    "min_history_days":     30,            # 最少 30 天历史
    "min_distance_to_mean": 0.03,          # 距月线均价至少 -3%（覆盖 2% 手续费 + 1% 利润）
    "blocked_stages":       ["MARKUP", "DISTRIBUTION", "MARKDOWN"],
    # 注：不做流动性过滤，假设用户已人工筛选过监控品种
}


def evaluate_buy_signals(state, item, ind, stage, market) -> list:
    history = item.get("history", [])
    P = ind.get("P")
    if P is None:
        return []

    # 1. 仓位上限
    pos = item.get("position", {})
    if pos.get("total_qty_pct", 0) >= 1.0:
        return []

    # 2. 阶段过滤：只在横盘 / 中性 / 吸筹 / 洗盘期间触发
    if stage in PARAMS["blocked_stages"]:
        return []

    # 3. 历史天数充足
    days_of_data = len(history) // 144   # 10min × 144 = 24h
    if days_of_data < PARAMS["min_history_days"]:
        return []

    # 4. 庄家活跃 → 避开（盘控期 RSI 失效）
    if signals_mod.get_active_whale_signal(state, item):
        return []

    # 5. 计算日线 RSI
    rsi = ind_mod.compute_daily_rsi(history, period=PARAMS["rsi_period"])
    if rsi is None or rsi >= PARAMS["rsi_oversold"]:
        return []

    # 6. 距均线空间足够（覆盖手续费 + 利润）
    ma_month = ind.get("ma_month")
    if not ma_month or ma_month <= 0:
        return []
    distance = (ma_month - P) / ma_month
    if distance < PARAMS["min_distance_to_mean"]:
        return []

    # 满足所有条件 → 触发 RSI-OVERSOLD
    return [{
        "label":       "RSI-OVERSOLD",
        "category":    "BUY",
        "priority":    8,
        "advice":      (
            f"日线 RSI({PARAMS['rsi_period']}) = {rsi:.1f} 严重超卖，"
            f"距月均 -{distance*100:.1f}%，预期均值回归（7-21 天）"
        ),
        "next_tier":   1,
        "qty":         0.3,    # 试探仓 30%
        "rsi_value":   rsi,
        "distance_to_mean": distance,
    }]
