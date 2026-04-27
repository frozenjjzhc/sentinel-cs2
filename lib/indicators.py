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
