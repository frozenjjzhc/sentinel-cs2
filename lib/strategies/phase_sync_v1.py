"""
Sentinel · 分阶共振 V1
==========================
当前主力策略。包装现有 lib/signals.py 的 BUY 评估逻辑。

设计理念：
  6 阶段庄家识别 + 多重过滤 + bias 调节
  适合 CS2 高波动 + T+7 锁仓 + 庄家活跃市

完整说明：见 dashboard 「策略管控」页 / strategy_v2.md
"""

from .. import signals as signals_mod


META = {
    "id":          "phase-sync-v1",
    "name":        "Sentinel · 分阶共振 V1",
    "tagline":     "6 阶段识别 + 5 重过滤 + bias 调节",
    "version":     "1.0",
    "status":      "stable",
    "description": (
        "针对 CS2 饰品市场设计的 技术 + 庄家行为 + 基本面 三层共振策略。"
        "6 阶段识别庄家意图，5 种 BUY 信号按优先级竞争，"
        "bias 调节器实时影响 priority 与止损/止盈阈值。"
    ),
    "best_for":  "缓慢修复市 / 庄家活跃市 / 阶段切换明确的市场",
    "weak_for":  "纯横盘市（无明显阶段）/ 流动性极差品种 / 极端单边趋势",
    "signals":   ["BUY-WASHOUT", "BUY-WHALE", "BUY-LAUNCH", "BUY-PULLBACK", "BUY-ACCUMULATE"],
}


def evaluate_buy_signals(state, item, ind, stage, market) -> list:
    """直接复用 signals.py 的 BUY 逻辑（已含 bias 调节）。"""
    return signals_mod.evaluate_buy_signals(state, item, ind, stage, market)
