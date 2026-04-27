r"""
Shadow position backtest.

每次 BUY 信号被推送时，自动建一个"影子仓位"，跟踪 7 天后的实际回报。
不影响真实操作，纯统计用。

存储：D:\claude\xuanxiao\shadow_signals.json
"""

import os
import uuid
from . import config
from . import utils


SHADOW_FILE = os.path.join(config.PROJECT_DIR, "shadow_signals.json")


def _load():
    return utils.read_json(SHADOW_FILE) or {"shadows": []}


def _save(data):
    utils.write_json(SHADOW_FILE, data)


def record_signal(item_id: str, label: str, category: str, entry_price: float, context: dict = None):
    """每次 BUY 信号推送时调用。"""
    if entry_price is None:
        return None
    data = _load()
    sid = str(uuid.uuid4())[:8]
    data["shadows"].append({
        "id": sid,
        "item_id": item_id,
        "label": label,
        "category": category,
        "entry_price": entry_price,
        "entry_time": utils.now_iso(),
        "evaluated": False,
        "exit_price": None,
        "exit_time": None,
        "return_7d_pct": None,
        "context": context or {},
    })
    _save(data)
    return sid


def evaluate_due_shadows(state: dict):
    """
    遍历未评估的影子仓位，凡 entry_time 已过 7 天的，
    用当前价（state 中最新 history 条目）计算 return_7d_pct。
    """
    data = _load()
    now_local = utils.now_local()
    updated = 0
    for sp in data.get("shadows", []):
        if sp.get("evaluated"):
            continue
        days_held = utils.days_since(sp.get("entry_time", ""))
        if days_held < 7:
            continue
        # Find current price for this item
        item = next((it for it in state.get("items", []) if it["id"] == sp["item_id"]), None)
        if not item or not item.get("history"):
            continue
        current = item["history"][-1].get("price")
        if not current:
            continue
        sp["exit_price"] = current
        sp["exit_time"] = utils.now_iso()
        entry = sp.get("entry_price")
        if entry:
            sp["return_7d_pct"] = (current - entry) / entry
        sp["evaluated"] = True
        updated += 1
    if updated > 0:
        _save(data)
    return updated


def get_stats(only_label: str = None) -> dict:
    """
    返回每类信号的胜率与平均收益。
    {
      "BUY-WHALE": {"count": 5, "avg_return": 0.082, "win_rate": 0.6, "max": 0.15, "min": -0.04},
      ...
    }
    """
    data = _load()
    realized = [s for s in data.get("shadows", []) if s.get("evaluated") and s.get("return_7d_pct") is not None]
    if only_label:
        realized = [s for s in realized if s.get("label") == only_label]

    stats = {}
    for label in set(s["label"] for s in realized):
        subset = [s for s in realized if s["label"] == label]
        returns = [s["return_7d_pct"] for s in subset]
        stats[label] = {
            "count": len(subset),
            "avg_return": sum(returns) / len(returns),
            "win_rate": sum(1 for r in returns if r > 0) / len(returns),
            "max_return": max(returns),
            "min_return": min(returns),
        }
    return stats


def get_recent(limit: int = 10) -> list:
    """最近 N 条已评估的影子仓位。"""
    data = _load()
    realized = [s for s in data.get("shadows", []) if s.get("evaluated")]
    realized.sort(key=lambda s: s.get("exit_time", ""), reverse=True)
    return realized[:limit]


def get_pending_count() -> int:
    data = _load()
    return sum(1 for s in data.get("shadows", []) if not s.get("evaluated"))
