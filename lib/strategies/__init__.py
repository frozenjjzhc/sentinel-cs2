"""
策略注册表 + 分发器。

新增策略只需：
  1. 写一个 lib/strategies/<name>.py 模块
  2. 模块里导出 META 字典 + evaluate_buy_signals(state, item, ind, stage, market) 函数
  3. 在下面 REGISTRY 里登记一行
"""

from . import phase_sync_v1
from . import rsi_reversion_v1
from . import mean_reversion_v1
from . import grid_half_v1


REGISTRY = {
    phase_sync_v1.META["id"]:     phase_sync_v1,
    rsi_reversion_v1.META["id"]:  rsi_reversion_v1,
    mean_reversion_v1.META["id"]: mean_reversion_v1,
    grid_half_v1.META["id"]:      grid_half_v1,
}


def get_strategy(strategy_id: str):
    """按 id 拿策略模块。"""
    return REGISTRY.get(strategy_id)


def list_meta() -> list:
    """所有策略的元信息列表。"""
    return [m.META for m in REGISTRY.values()]


def get_active_id(state: dict) -> str:
    """读取当前启用策略 id；默认 phase-sync-v1。"""
    return state.get("global", {}).get("active_strategy", "phase-sync-v1")


def get_strategy_params(state: dict, strategy_id: str) -> dict:
    """
    返回某策略的合并后参数（state 覆盖 + 模块默认 PARAMS 兜底）。
    AI 提案应用到 state.global.strategies[sid].params 后，这里读出来就拿到新值；
    缺失字段自动从模块的 PARAMS 常量补全。
    """
    mod = REGISTRY.get(strategy_id)
    defaults = getattr(mod, "PARAMS", {}) if mod else {}
    overrides = (
        state.get("global", {})
        .get("strategies", {})
        .get(strategy_id, {})
        .get("params", {})
    ) or {}
    merged = dict(defaults)
    merged.update(overrides)
    return merged


def get_strategy_param_defaults() -> dict:
    """
    所有已注册策略的默认 PARAMS。用于 state 自愈 + LLM 提案 prompt 上下文。
    形如 {"rsi-reversion-v1": {rsi_period: 14, ...}, ...}
    """
    out = {}
    for sid, mod in REGISTRY.items():
        defaults = getattr(mod, "PARAMS", None)
        if defaults:
            out[sid] = dict(defaults)
    return out


def evaluate_buy_signals(state, item, ind, stage, market, strategy_id: str = None) -> list:
    """
    分发到指定策略（默认当前 active）。
    """
    sid = strategy_id or get_active_id(state)
    mod = REGISTRY.get(sid)
    if not mod:
        return []
    return mod.evaluate_buy_signals(state, item, ind, stage, market)


def evaluate_all(state, item, ind, stage, market) -> dict:
    """
    并行评估所有策略的 BUY 信号 → {strategy_id: [signals]}。
    用于 shadow 双跟跑：active 策略实际推送，其他策略只记 shadow 做对比。
    """
    return {
        sid: mod.evaluate_buy_signals(state, item, ind, stage, market)
        for sid, mod in REGISTRY.items()
    }


def evaluate_sell(state, item, ind, strategy_id: str = None) -> list:
    """
    评估指定策略的 SELL 信号（仅网格策略实现了；其他策略走 stop_loss/TP）。
    """
    sid = strategy_id or get_active_id(state)
    mod = REGISTRY.get(sid)
    if not mod or not hasattr(mod, "evaluate_sell_signals"):
        return []
    return mod.evaluate_sell_signals(state, item, ind)


def apply_grid_fill(item, signal, fill_price=None, state=None):
    """
    网格策略专用：买入/卖出成交后更新 grid_state。
    state 可选；用于读 tplus7_days 等可调参数。
    """
    grid_action = signal.get("grid_action")
    if grid_action == "buy":
        grid_half_v1.apply_buy_fill(
            item, signal, fill_price or signal.get("level_price", 0), state=state
        )
    elif grid_action == "sell":
        grid_half_v1.apply_sell_fill(item, signal)
