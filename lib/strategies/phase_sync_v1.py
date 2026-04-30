"""
Sentinel · 分阶共振 V1
==========================
当前主力策略。包装 lib/signals.py 的 BUY 评估逻辑 + 跨品种板块联动加成。

设计理念：
  6 阶段庄家识别 + 多重过滤 + bias 调节 + 板块跟涨加成
  适合 CS2 高波动 + T+7 锁仓 + 庄家活跃市

板块跟涨加成（v2.3+）：
  当本品种所属主板块出现强领涨（leader RS ≥ 2.0）且本品种相对滞后
  （leader_change - self_change > 2%）时：
    - 给原始 BUY 信号 priority +0.5（机会信号优先）
    - advice 末尾追加 [📈 板块「X」领涨 + N% 跟涨候选]
    - 写到信号 dict 的 sector_boost 字段，便于 shadow / 复盘追踪

为什么不单独推「跟涨机会」：
  - 跟涨频次高、噪音大，独立推送干扰主决策
  - 作为加权因子嵌入到 BUY 评估里更有意义：BUY 信号本身已通过阶段+技术过滤，
    这时「板块还领涨」是额外的进场强度证据，而不是另一条独立信号

完整说明：见 dashboard 「策略管控」页 / strategy_v2.md
"""

from .. import signals as signals_mod
from .. import correlation as corr_mod


META = {
    "id":          "phase-sync-v1",
    "name":        "Sentinel · 分阶共振 V1",
    "tagline":     "6 阶段识别 + 5 重过滤 + bias 调节 + 板块联动加成",
    "version":     "1.1",
    "status":      "stable",
    "description": (
        "针对 CS2 饰品市场设计的 技术 + 庄家行为 + 基本面 + 板块联动 四层共振策略。"
        "6 阶段识别庄家意图，5 种 BUY 信号按优先级竞争，"
        "bias 调节器实时影响 priority 与止损/止盈阈值，"
        "v1.1 加入板块跟涨加成 — 主板块强势 + 本品种滞后时，原始 BUY priority +0.5。"
    ),
    "best_for":  "缓慢修复市 / 庄家活跃市 / 阶段切换明确的市场",
    "weak_for":  "纯横盘市（无明显阶段）/ 流动性极差品种 / 极端单边趋势",
    "signals":   ["BUY-WASHOUT", "BUY-WHALE", "BUY-LAUNCH", "BUY-PULLBACK", "BUY-ACCUMULATE"],
}


# 板块跟涨加成参数
SECTOR_LEADER_RS_THRESHOLD = 2.0    # 领涨者 1H RS ≥ 此值才算「强领涨」
SECTOR_GAP_PCT_THRESHOLD   = 0.02   # 本品种 1H 涨幅落后领涨者 ≥ 2% 才算「显著滞后」
SECTOR_BOOST_PRIORITY      = 0.5    # 满足条件时给 BUY 信号加的 priority


def _sector_boost_for(state, item) -> dict | None:
    """
    检查当前品种是否处于「板块跟涨候选」状态。
    优先用 monitor_slow 已写入的 state.global.sector_analysis（无需重算）；
    若没有则即时算一次。

    返回 None 表示无加成；返回 dict 表示触发，含描述文字 + 数据。
    """
    glb = state.get("global", {})
    cached = glb.get("sector_analysis")
    if cached and "primary" in cached:
        full = cached
    else:
        try:
            full = corr_mod.detect_full_analysis(state)
        except Exception:
            return None

    opportunities = corr_mod.find_following_opportunities(state, full)
    for opp in opportunities:
        if opp.get("item_id") != item.get("id"):
            continue
        if opp.get("leader_rs", 0) < SECTOR_LEADER_RS_THRESHOLD:
            continue
        if opp.get("gap_pct", 0) < SECTOR_GAP_PCT_THRESHOLD:
            continue
        return {
            "primary_sector": opp.get("primary_sector"),
            "leader_id":      opp.get("leader_id"),
            "leader_rs":      opp.get("leader_rs"),
            "gap_pct":        opp.get("gap_pct"),
            "tag":            f"[📈 板块「{opp.get('primary_sector')}」领涨 +{opp.get('gap_pct',0)*100:.1f}% 跟涨候选]",
        }
    return None


def evaluate_buy_signals(state, item, ind, stage, market) -> list:
    """
    复用 signals.py 的 BUY 逻辑（已含 bias 调节），再叠加板块跟涨加成：
      - 若本品种是跟涨候选 → 所有原始 BUY 信号 priority +0.5
      - advice 末尾追加 sector_boost.tag 标签
      - 信号 dict 写入 sector_boost 字段（shadow 可追踪）
    """
    raw = signals_mod.evaluate_buy_signals(state, item, ind, stage, market)
    if not raw:
        return raw

    boost = _sector_boost_for(state, item)
    if not boost:
        return raw

    out = []
    for s in raw:
        s2 = dict(s)
        s2["priority"]     = s2.get("priority", 0) + SECTOR_BOOST_PRIORITY
        s2["sector_boost"] = boost
        adv = s2.get("advice") or ""
        s2["advice"]       = f"{adv} {boost['tag']}".strip()
        out.append(s2)
    return out
