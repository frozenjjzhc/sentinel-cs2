"""
Technical indicators: multi-timeframe MA, momentum, volume_quality.
"""

from statistics import mean, stdev
from . import config


def _safe_mean(seq):
    seq = [x for x in seq if x is not None]
    if not seq:
        return None
    return mean(seq)


def _safe_stdev(seq):
    seq = [x for x in seq if x is not None]
    if len(seq) < 2:
        return None
    return stdev(seq)


def compute_indicators(history: list) -> dict:
    """
    Compute all derived indicators from history.
    history: list of entries (oldest → newest).
    Returns dict with ma_micro / intraday / week / month, momentum_score,
    volume_quality, delta_volume, vol_avg_short, etc.
    """
    if not history:
        return {}

    prices = [h.get("price") for h in history]
    volumes = [h.get("today_volume") for h in history]

    P = prices[-1] if prices else None
    prev = prices[-2] if len(prices) >= 2 else None
    prev2 = prices[-3] if len(prices) >= 3 else None

    # Multi-timeframe MAs
    ma_micro = _safe_mean(prices[-config.MA_MICRO_N:]) if len(prices) >= config.MA_MICRO_N else None
    ma_intraday = _safe_mean(prices[-config.MA_INTRADAY_N:]) if len(prices) >= config.MA_INTRADAY_N else None
    ma_week = _safe_mean(prices[-config.MA_WEEK_N:]) if len(prices) >= config.MA_WEEK_N else None
    ma_month = _safe_mean(prices[-config.MA_MONTH_N:]) if len(prices) >= config.MA_MONTH_N else None

    prev_ma_micro = _safe_mean(prices[-config.MA_MICRO_N-1:-1]) if len(prices) >= config.MA_MICRO_N + 1 else None
    prev_ma_intraday = _safe_mean(prices[-config.MA_INTRADAY_N-1:-1]) if len(prices) >= config.MA_INTRADAY_N + 1 else None

    # Volume averages
    valid_vol = [v for v in volumes if v is not None]
    vol_window = valid_vol[-config.VOL_WINDOW_N:] if len(valid_vol) >= config.VOL_WINDOW_N else valid_vol
    vol_avg = _safe_mean(vol_window) if vol_window else None

    # Delta volume (今日累计 → 增量)
    delta_volume = None
    if len(volumes) >= 2 and volumes[-1] is not None and volumes[-2] is not None:
        delta_volume = volumes[-1] - volumes[-2]
        # 跨日清零情况：负数视为新一天开始
        if delta_volume < 0:
            delta_volume = volumes[-1]

    # Momentum score
    momentum_score = 0
    if P is not None and prev is not None and prev2 is not None and P != prev and prev != prev2:
        if P > prev > prev2:
            if (P - prev) > (prev - prev2):
                momentum_score = 2
            else:
                momentum_score = 1
        elif P < prev < prev2:
            if (prev - P) > (prev2 - prev):
                momentum_score = -2
            else:
                momentum_score = -1

    # Volume quality
    volume_quality = None
    if P is not None and prev is not None and volumes[-1] is not None and vol_avg is not None and vol_avg > 0:
        v = volumes[-1]
        if v > vol_avg * config.BULLISH_BREAKOUT_VOL_RATIO and P > prev:
            volume_quality = "bullish_breakout"
        elif v < vol_avg * config.WEAK_PULLBACK_VOL_RATIO and P < prev:
            volume_quality = "weak_pullback"
        else:
            # Check false breakout: price hits new high but volume new low (last 10)
            recent_prices = prices[-config.FALSE_BREAKOUT_LOOKBACK:]
            recent_vols = [vv for vv in volumes[-config.FALSE_BREAKOUT_LOOKBACK:] if vv is not None]
            if (
                len(recent_prices) >= 5 and len(recent_vols) >= 5
                and P == max(recent_prices)
                and v == min(recent_vols)
            ):
                volume_quality = "false_breakout"

    # Volatility
    volatility = None
    if len(prices) >= 24:
        recent_window = prices[-72:] if len(prices) >= 72 else prices[-24:]
        sd = _safe_stdev(recent_window)
        m = _safe_mean(recent_window)
        if sd is not None and m and m > 0:
            volatility = sd / m

    return {
        "P": P,
        "prev": prev,
        "prev2": prev2,
        "ma_micro": ma_micro,
        "ma_intraday": ma_intraday,
        "ma_week": ma_week,
        "ma_month": ma_month,
        "prev_ma_micro": prev_ma_micro,
        "prev_ma_intraday": prev_ma_intraday,
        "vol_avg": vol_avg,
        "delta_volume": delta_volume,
        "momentum_score": momentum_score,
        "volume_quality": volume_quality,
        "volatility": volatility,
        "history_len": len(history),
    }


def compute_change_pct(history: list, hours_back: float) -> float:
    """Compute price change over last N hours (using 10min entries)."""
    if not history or len(history) < 2:
        return 0
    n = max(1, int(hours_back * 6))   # 10min entries per hour = 6
    if len(history) <= n:
        return 0
    p_now = history[-1].get("price")
    p_then = history[-1 - n].get("price")
    if not p_now or not p_then:
        return 0
    return (p_now - p_then) / p_then


# ============================================================
# 日线降采样 + RSI 计算（用于 RSI Mean Reversion 策略）
# ============================================================
def daily_closes(history: list, num_days: int = 30) -> list:
    """
    把 10 分钟级 history 降采样为日收盘价列表。
    取每个日期的最后一个 price 作为该日 close。
    返回最近 num_days 天的 close 价（按时间升序）。
    """
    from datetime import datetime
    if not history:
        return []
    daily_map = {}
    for h in history:
        if h.get("price") is None:
            continue
        try:
            d = datetime.fromisoformat(h["t"]).date()
        except Exception:
            continue
        daily_map[d] = h["price"]   # 后值覆盖前值 = 当日 close
    sorted_days = sorted(daily_map.keys())[-num_days:]
    return [daily_map[d] for d in sorted_days]


def compute_rsi(closes: list, period: int = 14) -> float:
    """
    Wilder's RSI on a list of closing prices (oldest → newest).
    Returns RSI ∈ [0, 100], or None if data insufficient.
    """
    if not closes or len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-diff)
    # Initial avg from first `period` deltas
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    # Wilder smoothing for the rest
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def compute_daily_rsi(history: list, period: int = 14) -> float:
    """便捷封装：直接从 raw history 算日线 RSI。"""
    closes = daily_closes(history, num_days=period + 5)
    return compute_rsi(closes, period=period)


# ============================================================
# 价格分布统计 + z-score（用于 Mean Reversion 策略）
# ============================================================
def compute_daily_zscore(history: list, lookback_days: int = 20):
    """
    日线 z-score：当前价距 N 日均价的标准差倍数。
    返回 (z_score, mean, std) 元组；数据不足返回 (None, None, None)。

    z = (P - mean_N) / std_N

    z = -2 表示 "当前价比 N 日均价低 2 个标准差"（统计上罕见，约 5% 概率）。
    """
    closes = daily_closes(history, num_days=lookback_days + 1)
    if len(closes) < lookback_days:
        return None, None, None
    sample = closes[-lookback_days - 1:-1]   # 不含最新（最新是当前）
    if len(sample) < 2:
        return None, None, None
    m = sum(sample) / len(sample)
    var = sum((x - m) ** 2 for x in sample) / (len(sample) - 1)   # 样本方差
    sd = var ** 0.5
    if sd <= 0:
        return None, m, 0
    P = closes[-1]
    return (P - m) / sd, m, sd
