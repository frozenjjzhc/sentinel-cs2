"""
Total portfolio risk panel.
Computed once per day at review time.
"""

from . import state as state_mod


def compute_summary(state: dict) -> dict:
    """
    Returns total portfolio metrics:
    - total_cost / total_market_value / total_pnl / total_pnl_pct
    - Per-item breakdown (active position + legacy)
    - Concentration: largest single-item exposure
    - Risk warnings
    """
    items = state.get("items", [])
    if not items:
        return {"empty": True}

    total_active_cost = 0
    total_active_value = 0
    total_legacy_cost = 0
    total_legacy_value = 0

    breakdown = []

    for item in items:
        current_price = None
        if item.get("history"):
            current_price = item["history"][-1].get("price")

        # Active position (new tiers)
        pos = item.get("position", {})
        tiers = pos.get("tiers", [])
        active_cost = 0
        active_value = 0
        active_pieces = 0     # 真实持有把数
        active_pct_sum = 0    # 占计划满仓的累计 %（仅展示用）
        if tiers:
            for t in tiers:
                # 优先用 qty_pieces（真实把数），若缺失回落到旧 qty_pct 字段（向后兼容）
                pieces = t.get("qty_pieces")
                if pieces is None:
                    pieces = t.get("qty_pct", 0)   # 旧数据
                entry = t.get("entry_price", 0)
                active_cost  += entry * pieces
                if current_price:
                    active_value += current_price * pieces
                active_pieces  += pieces
                active_pct_sum += t.get("qty_pct", 0)

        # Legacy holding (real units, not qty_pct)
        legacy = item.get("legacy_holding", {})
        legacy_qty = legacy.get("quantity", 0) if legacy else 0
        legacy_avg = legacy.get("avg_entry_price", 0) if legacy else 0
        legacy_cost = legacy_qty * legacy_avg
        legacy_value = legacy_qty * current_price if (legacy_qty and current_price) else 0

        total_active_cost += active_cost
        total_active_value += active_value
        total_legacy_cost += legacy_cost
        total_legacy_value += legacy_value

        item_total_cost = active_cost + legacy_cost
        item_total_value = active_value + legacy_value
        item_pnl = item_total_value - item_total_cost

        breakdown.append({
            "id": item["id"],
            "name": item.get("short_name", item["id"]),
            "current_price": current_price,
            "active_pieces": active_pieces,
            "active_pct": active_pct_sum,    # 占满仓计划的总比例（展示）
            "active_avg": pos.get("avg_entry_price"),
            "active_cost": active_cost,
            "active_value": active_value,
            "legacy_qty": legacy_qty,
            "legacy_avg": legacy_avg,
            "legacy_cost": legacy_cost,
            "legacy_value": legacy_value,
            "total_cost": item_total_cost,
            "total_value": item_total_value,
            "pnl": item_pnl,
            "pnl_pct": item_pnl / item_total_cost if item_total_cost else 0,
        })

    total_cost = total_active_cost + total_legacy_cost
    total_value = total_active_value + total_legacy_value
    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost if total_cost else 0

    # Concentration
    item_costs = [(b["id"], b["total_cost"]) for b in breakdown]
    item_costs.sort(key=lambda kv: kv[1], reverse=True)
    top_id, top_cost = item_costs[0] if item_costs else (None, 0)
    concentration_pct = top_cost / total_cost if total_cost else 0

    # Risk warnings
    warnings = []
    if concentration_pct > 0.7:
        warnings.append(f"⚠️ 集中度过高：{top_id} 占总仓位 {concentration_pct*100:.1f}%")
    if total_pnl_pct < -0.20:
        warnings.append(f"⚠️ 总浮亏 {total_pnl_pct*100:.1f}%，需评估止损")
    if total_active_cost > 0:
        active_pnl_pct = (total_active_value - total_active_cost) / total_active_cost
        if active_pnl_pct > 0.20:
            warnings.append(f"💡 新仓浮盈 {active_pnl_pct*100:.1f}%，关注止盈机会")

    return {
        "total_cost": total_cost,
        "total_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "active_cost": total_active_cost,
        "active_value": total_active_value,
        "legacy_cost": total_legacy_cost,
        "legacy_value": total_legacy_value,
        "concentration_top_id": top_id,
        "concentration_pct": concentration_pct,
        "breakdown": breakdown,
        "warnings": warnings,
    }


def format_summary_text(summary: dict) -> str:
    """Format for push message."""
    if summary.get("empty"):
        return "无持仓数据"

    lines = []
    lines.append(f"💰 总成本：¥{summary['total_cost']:,.0f}")
    lines.append(f"📊 总市值：¥{summary['total_value']:,.0f}")
    pnl = summary["total_pnl"]
    pnl_pct = summary["total_pnl_pct"]
    sign = "+" if pnl >= 0 else ""
    lines.append(f"📈 总浮盈：{sign}¥{pnl:,.0f} ({sign}{pnl_pct*100:.2f}%)")

    if summary.get("active_cost", 0) > 0:
        active_pnl = summary["active_value"] - summary["active_cost"]
        active_pnl_pct = active_pnl / summary["active_cost"]
        sign = "+" if active_pnl >= 0 else ""
        lines.append(
            f"  • 新仓：¥{summary['active_cost']:,.0f} → ¥{summary['active_value']:,.0f} "
            f"({sign}{active_pnl_pct*100:.2f}%)"
        )

    if summary.get("legacy_cost", 0) > 0:
        legacy_pnl = summary["legacy_value"] - summary["legacy_cost"]
        legacy_pnl_pct = legacy_pnl / summary["legacy_cost"]
        sign = "+" if legacy_pnl >= 0 else ""
        lines.append(
            f"  • 套牢：¥{summary['legacy_cost']:,.0f} → ¥{summary['legacy_value']:,.0f} "
            f"({sign}{legacy_pnl_pct*100:.2f}%)"
        )

    if summary.get("concentration_pct", 0) > 0.5:
        lines.append(
            f"⚖️ 集中度：{summary['concentration_top_id']} 占 {summary['concentration_pct']*100:.0f}%"
        )

    for w in summary.get("warnings", []):
        lines.append(w)

    return "\n".join(lines)
