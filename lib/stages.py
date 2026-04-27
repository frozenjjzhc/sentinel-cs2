"""
Whale stage detection (6 stages).

Each stage's threshold reads from item.thresholds first, falling back to defaults.
This allows low-liquidity items (e.g. driver gloves) to use wider thresholds.
"""

from statistics import mean, stdev


STAGES = [
    "ACCUMULATION",
    "SHAKEOUT",
    "COILING",
    "MARKUP",
    "DISTRIBUTION",
    "MARKDOWN",
    "UNKNOWN",
]


def _stdev_safe(seq):
    seq = [x for x in seq if x is not None]
    if len(seq) < 2:
        return 0
    return stdev(seq)


def _mean_safe(seq):
    seq = [x for x in seq if x is not None]
    if not seq:
        return 0
    return mean(seq)


def _get_threshold(item, key, default):
    return item.get("thresholds", {}).get(key, default)


def detect_stage(item: dict, ind: dict) -> str:
    history = item.get("history", [])
    if len(history) < 6:
        return "UNKNOWN"

    P = ind.get("P")
    prev = ind.get("prev")
    if P is None:
        return "UNKNOWN"

    # Per-item thresholds (gloves etc. use wider)
    shakeout_drop_1h = _get_threshold(item, "shakeout_drop_pct_1h", 0.05)
    coiling_volatility_ratio = _get_threshold(item, "coiling_volatility_ratio", 0.5)
    coiling_distance_pct = _get_threshold(item, "coiling_distance_pct", 0.03)
    accumulation_below_week_pct = _get_threshold(item, "accumulation_below_week_pct", 0.05)
    accumulation_vol_ratio = _get_threshold(item, "accumulation_vol_ratio", 0.6)
    markup_breakout_pct = _get_threshold(item, "markup_breakout_pct", 0.005)
    markup_min_change_24h = _get_threshold(item, "markup_min_change_24h", 0.05)
    markdown_drop_24h = _get_threshold(item, "markdown_drop_24h", 0.03)

    prices_72h = [h.get("price") for h in history[-432:]]
    prices_24h = [h.get("price") for h in history[-144:]]
    prices_6h  = [h.get("price") for h in history[-36:]]
    volumes_24h = [h.get("today_volume") for h in history[-144:] if h.get("today_volume") is not None]

    ma_week = ind.get("ma_week")
    ma_month = ind.get("ma_month")
    volatility = ind.get("volatility")

    long_volatility = None
    if len(prices_72h) >= 36:
        sd = _stdev_safe(prices_72h)
        m = _mean_safe(prices_72h)
        if m > 0:
            long_volatility = sd / m

    # 1. SHAKEOUT
    if len(prices_6h) >= 6 and len(history) >= 7:
        p_1h_ago = history[-7].get("price")
        if p_1h_ago and P:
            drop_1h = (P - p_1h_ago) / p_1h_ago
            if drop_1h <= -shakeout_drop_1h:
                recent_lows = [p for p in prices_24h[:-7] if p is not None]
                recent_low = min(recent_lows) if recent_lows else P
                if P >= recent_low * 0.99:
                    return "SHAKEOUT"

    # 2. MARKUP
    if len(prices_24h) >= 12:
        non_null = [p for p in prices_24h[:-1] if p is not None]
        if non_null:
            recent_max = max(non_null)
            if P > recent_max * (1 + markup_breakout_pct) and ind.get("volume_quality") == "bullish_breakout":
                return "MARKUP"
            first_p = next((p for p in prices_24h if p is not None), None)
            if first_p:
                recent_change = (P - first_p) / first_p
                if recent_change > markup_min_change_24h and P > recent_max * (1 + markup_breakout_pct):
                    return "MARKUP"

    # 3. COILING
    if volatility is not None and long_volatility:
        if volatility < long_volatility * coiling_volatility_ratio:
            if ma_week and abs(P - ma_week) / ma_week < coiling_distance_pct:
                return "COILING"

    # 4. ACCUMULATION
    if ma_week and P < ma_week * (1 - accumulation_below_week_pct):
        if volumes_24h:
            avg_vol = _mean_safe(volumes_24h)
            volumes_72h = [h.get("today_volume") for h in history[-432:] if h.get("today_volume") is not None]
            long_avg_vol = _mean_safe(volumes_72h) if volumes_72h else avg_vol
            if long_avg_vol > 0 and avg_vol < long_avg_vol * accumulation_vol_ratio:
                return "ACCUMULATION"

    # 5. DISTRIBUTION
    if ma_month and P > ma_month * 1.05:
        false_count = sum(1 for h in history[-144:] if h.get("volume_quality") == "false_breakout")
        if false_count >= 2:
            return "DISTRIBUTION"

    # 6. MARKDOWN
    if ma_week and ma_month and P < ma_week and ma_week < ma_month:
        if len(prices_24h) >= 12:
            first_p = next((p for p in prices_24h if p is not None), None)
            if first_p:
                net_change = (P - first_p) / first_p
                if net_change < -markdown_drop_24h:
                    return "MARKDOWN"

    return "UNKNOWN"
