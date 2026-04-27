"""
Cross-item correlation: 2-tier sector classification (primary + secondary).

Sectors are defined in state.global.sectors:
{
  "primary": {
    "一代手套板块": [item_ids...],
    "收藏品板块": [...],
    ...
  },
  "secondary": {
    "M4A4_系列": [...],
    ...
  },
  "weights": {"primary": 0.7, "secondary": 0.3}
}

Combined RS = primary_RS × w_primary + secondary_RS × w_secondary
"""

DEFAULT_WEIGHTS = {"primary": 0.7, "secondary": 0.3}


# ============================================================
# RS computation per item (vs market)
# ============================================================
def compute_rs_score_1h(item, anchor_history):
    item_hist = item.get("history", [])
    if len(item_hist) < 7 or len(anchor_history) < 7:
        return 1.0
    p_now = item_hist[-1].get("price")
    p_1h = item_hist[-7].get("price")
    m_now = anchor_history[-1].get("market_index")
    m_1h = anchor_history[-7].get("market_index")
    if not (p_now and p_1h and m_now and m_1h):
        return 1.0
    item_change = (p_now - p_1h) / p_1h
    market_change = (m_now - m_1h) / m_1h
    if abs(market_change) < 0.0005:
        return item_change * 100 if abs(item_change) > 0.005 else 1.0
    return item_change / market_change


def compute_rs_score_24h(item, anchor_history):
    item_hist = item.get("history", [])
    if len(item_hist) < 145 or len(anchor_history) < 145:
        return 1.0
    p_now = item_hist[-1].get("price")
    p_24h = item_hist[-145].get("price")
    m_now = anchor_history[-1].get("market_index")
    m_24h = anchor_history[-145].get("market_index")
    if not (p_now and p_24h and m_now and m_24h):
        return 1.0
    item_change = (p_now - p_24h) / p_24h
    market_change = (m_now - m_24h) / m_24h
    if abs(market_change) < 0.0005:
        return item_change * 100 if abs(item_change) > 0.005 else 1.0
    return item_change / market_change


def _change_1h(item):
    h = item.get("history", [])
    if len(h) < 7:
        return 0
    p_now = h[-1].get("price")
    p_1h = h[-7].get("price")
    if not (p_now and p_1h):
        return 0
    return (p_now - p_1h) / p_1h


# ============================================================
# Sector analysis (per tier)
# ============================================================
def _filter_real_groups(group_dict):
    """跳过 _template_xxx 占位组（空的且以 _template 开头）。"""
    return {
        name: ids for name, ids in group_dict.items()
        if not (name.startswith("_template") and not ids)
    }


def detect_tier_leaders(state: dict, tier: str) -> dict:
    """
    对指定 tier (primary 或 secondary) 中的每个 group，
    按 RS_1H 排序找领涨/拖后腿。
    """
    sectors = state.get("global", {}).get("sectors", {})
    tier_groups = _filter_real_groups(sectors.get(tier, {}))
    items = state.get("items", [])
    if not items:
        return {}
    anchor = items[0].get("history", [])
    items_dict = {it["id"]: it for it in items}

    result = {}
    for group_name, item_ids in tier_groups.items():
        if not item_ids:
            continue
        rs_dict = {}
        for iid in item_ids:
            it = items_dict.get(iid)
            if it:
                rs_dict[iid] = round(compute_rs_score_1h(it, anchor), 2)
        if not rs_dict:
            continue
        sorted_ids = sorted(rs_dict.items(), key=lambda kv: kv[1], reverse=True)
        result[group_name] = {
            "leader": {"id": sorted_ids[0][0], "rs": sorted_ids[0][1]} if sorted_ids else None,
            "laggard": {"id": sorted_ids[-1][0], "rs": sorted_ids[-1][1]} if len(sorted_ids) > 1 else None,
            "all_rs": rs_dict,
            "avg_rs": round(sum(rs_dict.values()) / len(rs_dict), 2),
        }
    return result


# ============================================================
# Combined RS for a single item (using both tiers)
# ============================================================
def compute_combined_rs(item, state, primary_analysis, secondary_analysis) -> dict:
    """
    返回该 item 的综合 RS 分析：
    {
      "primary_sector": "一代手套板块",
      "primary_sector_avg_rs": 1.8,
      "secondary_sector": "M4A4_系列",
      "secondary_sector_avg_rs": 0.9,
      "self_rs_1h": 1.2,
      "combined_rs": 1.53   (primary * 0.7 + secondary * 0.3)
    }
    """
    sectors = state.get("global", {}).get("sectors", {})
    weights = sectors.get("weights", DEFAULT_WEIGHTS)
    w_p = weights.get("primary", 0.7)
    w_s = weights.get("secondary", 0.3)

    primary_groups = _filter_real_groups(sectors.get("primary", {}))
    secondary_groups = _filter_real_groups(sectors.get("secondary", {}))

    # Find which group this item belongs to
    primary_group_name = None
    for name, ids in primary_groups.items():
        if item["id"] in ids:
            primary_group_name = name
            break
    secondary_group_name = None
    for name, ids in secondary_groups.items():
        if item["id"] in ids:
            secondary_group_name = name
            break

    primary_avg = primary_analysis.get(primary_group_name, {}).get("avg_rs", 1.0) if primary_group_name else 1.0
    secondary_avg = secondary_analysis.get(secondary_group_name, {}).get("avg_rs", 1.0) if secondary_group_name else 1.0

    items = state.get("items", [])
    anchor = items[0].get("history", []) if items else []
    self_rs = compute_rs_score_1h(item, anchor)

    combined = primary_avg * w_p + secondary_avg * w_s

    return {
        "primary_sector": primary_group_name,
        "primary_sector_avg_rs": primary_avg,
        "secondary_sector": secondary_group_name,
        "secondary_sector_avg_rs": secondary_avg,
        "self_rs_1h": round(self_rs, 2),
        "combined_rs": round(combined, 2),
        "weights_used": {"primary": w_p, "secondary": w_s},
    }


# ============================================================
# Main entry: full sector analysis
# ============================================================
def detect_sector_leaders(state: dict) -> dict:
    """
    Backward-compatible wrapper. Returns combined analysis
    (only primary tier) for compatibility with old code.
    Internal callers should use detect_full_analysis.
    """
    return detect_tier_leaders(state, "primary")


def detect_full_analysis(state: dict) -> dict:
    """
    Returns full 2-tier analysis:
    {
      "primary": {"一代手套板块": {leader, laggard, all_rs, avg_rs}, ...},
      "secondary": {"M4A4_系列": {...}, ...},
      "items": {item_id: combined_rs_dict, ...}
    }
    """
    primary = detect_tier_leaders(state, "primary")
    secondary = detect_tier_leaders(state, "secondary")
    items_combined = {}
    for it in state.get("items", []):
        items_combined[it["id"]] = compute_combined_rs(it, state, primary, secondary)
    return {
        "primary": primary,
        "secondary": secondary,
        "items": items_combined,
    }


# ============================================================
# Following opportunities (cross-item)
# ============================================================
def find_following_opportunities(state: dict, full_analysis: dict) -> list:
    """
    Find items that should be watching for跟涨 opportunities.
    Logic: when an item's primary sector has strong leader (RS>2) but the item itself
    hasn't followed (gap > 2%), it's a candidate for跟涨.

    Backward-compatible: also accepts old-style sector_analysis dict (primary-only).
    """
    # Detect format
    if "primary" in full_analysis and isinstance(full_analysis.get("primary"), dict):
        primary_analysis = full_analysis["primary"]
    else:
        primary_analysis = full_analysis  # old format

    opportunities = []
    items_dict = {it["id"]: it for it in state.get("items", [])}

    for sector_name, info in primary_analysis.items():
        leader = info.get("leader")
        if not leader or leader.get("rs", 0) < 2.0:
            continue
        leader_item = items_dict.get(leader["id"])
        if not leader_item:
            continue
        leader_change = _change_1h(leader_item)

        for fid, rs in info["all_rs"].items():
            if fid == leader["id"]:
                continue
            follower_item = items_dict.get(fid)
            if not follower_item:
                continue
            follower_change = _change_1h(follower_item)
            gap = leader_change - follower_change
            if gap > 0.02:
                opportunities.append({
                    "item_id": fid,
                    "primary_sector": sector_name,
                    "leader_id": leader["id"],
                    "leader_rs": leader["rs"],
                    "follower_rs": rs,
                    "gap_pct": gap,
                })

    return opportunities


# ============================================================
# Format helper
# ============================================================
def format_item_rs_summary(item_id: str, combined: dict) -> str:
    """Format a single item's combined RS analysis for push messages."""
    if not combined:
        return ""
    lines = []
    p_sec = combined.get("primary_sector") or "未分类"
    s_sec = combined.get("secondary_sector") or "未分类"
    lines.append(
        f"  主板块「{p_sec}」平均 RS={combined.get('primary_sector_avg_rs', 1.0)}"
    )
    lines.append(
        f"  副板块「{s_sec}」平均 RS={combined.get('secondary_sector_avg_rs', 1.0)}"
    )
    lines.append(
        f"  自身 RS_1h={combined.get('self_rs_1h', 1.0)}  →  综合 RS={combined.get('combined_rs', 1.0)}"
    )
    return "\n".join(lines)
