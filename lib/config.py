"""
Global configuration constants for the CS2 monitor.
Most parameters are also stored per-item in state.json,
but these are sane defaults / fallbacks.
"""

import os
import shutil

# ============================================================
# Paths
# ============================================================
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# v2.1.0+：用户数据目录与代码目录分离，跨版本升级 0 迁移成本。
#
# 优先级：
#   1. SENTINEL_DATA_DIR 环境变量（高级用户多实例隔离用）
#   2. %APPDATA%\Sentinel\           Windows 默认，跟随用户账号 + 系统备份
#   3. ~/.local/share/sentinel       Linux/Mac 兜底
#   4. PROJECT_DIR                   最终兜底（保持老行为）
def _resolve_data_dir():
    env = os.environ.get("SENTINEL_DATA_DIR")
    if env:
        return env
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "Sentinel")
    home = os.path.expanduser("~")
    if home != "~":
        return os.path.join(home, ".local", "share", "sentinel")
    return PROJECT_DIR


DATA_DIR = _resolve_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)


# 首次启动自动迁移：DATA_DIR 没数据但 PROJECT_DIR 有 → 复制过去（旧文件保留作备份，不删）
def _migrate_legacy_once():
    target = os.path.join(DATA_DIR, "m4a4_buzz_kill_state.json")
    if os.path.isfile(target):
        return  # 已经在新位置了，无需迁移
    legacy = os.path.join(PROJECT_DIR, "m4a4_buzz_kill_state.json")
    if not os.path.isfile(legacy):
        return  # 全新安装，没有老数据可迁
    # 文件
    for f in [
        "m4a4_buzz_kill_state.json",
        "m4a4_buzz_kill_state.json.bak",
        "shadow_signals.json",
        "m4a4_errors.log",
    ]:
        src = os.path.join(PROJECT_DIR, f)
        dst = os.path.join(DATA_DIR, f)
        if os.path.isfile(src) and not os.path.isfile(dst):
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                print(f"[Sentinel] 迁移 {f} 失败：{e}")
    # 目录
    for d in [".playwright_profile", "screenshots", "logs", "daily_kline"]:
        src = os.path.join(PROJECT_DIR, d)
        dst = os.path.join(DATA_DIR, d)
        if os.path.isdir(src) and not os.path.isdir(dst):
            try:
                shutil.copytree(src, dst)
            except Exception as e:
                print(f"[Sentinel] 迁移目录 {d} 失败：{e}")
    print(f"[Sentinel] 首次启动 v2.1+：用户数据已从 {PROJECT_DIR} 迁移到 {DATA_DIR}")
    print(f"[Sentinel] 旧文件保留作备份，确认无问题后可手动删除。")


_migrate_legacy_once()


STATE_FILE = os.path.join(DATA_DIR, "m4a4_buzz_kill_state.json")
ERROR_LOG = os.path.join(DATA_DIR, "m4a4_errors.log")
PLAYWRIGHT_PROFILE = os.path.join(DATA_DIR, ".playwright_profile")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "screenshots")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
DAILY_KLINE_DIR = os.path.join(DATA_DIR, "daily_kline")

# ============================================================
# Frequencies (minutes)
# ============================================================
FREQUENCY_FAST_MINUTES = 10   # monitor_fast cron interval
FREQUENCY_SLOW_MINUTES = 60   # monitor_slow cron interval

# ============================================================
# History limits
# ============================================================
HISTORY_MAX_ENTRIES = 13000   # ~90 days at 10min frequency
SIGNALS_LOG_MAX = 720         # ~5 days at 10min
RECOMMENDATIONS_LOG_MAX = 200
DAILY_REVIEW_LOG_MAX = 90

# ============================================================
# Multi-timeframe MA window sizes (in number of 10min entries)
# ============================================================
MA_MICRO_N = 6        # 1 hour
MA_INTRADAY_N = 72    # 12 hours
MA_WEEK_N = 1008      # 7 days
MA_MONTH_N = 4320     # 30 days
VOL_WINDOW_N = 6      # 1 hour delta volume

# ============================================================
# Default thresholds (can be overridden per item in state.json)
# ============================================================
DEFAULT_THRESHOLDS = {
    "today_pct_for_d1": 2.5,         # 上调（CS2 适配）
    "rapid_drop_pct_1h": 7,
    "rapid_rise_pct_1h": 10,
    "d1_distance_to_r1_min": 0.035,
    "min_volume_d1": 8,
    "fixed_stop_pct": 0.15,
    "trailing_stop_pct": 0.12,
}

# ============================================================
# Take-profit tier defaults
# ============================================================
TP_LEVELS = [0.20, 0.40, 0.70]    # +20% / +40% / +70%
TP_CLOSE_PCT = [0.30, 0.30, 0.0]
ENTRY_TIER_PCT = [0.30, 0.30, 0.40]

# ============================================================
# Volume / momentum signal thresholds
# ============================================================
BULLISH_BREAKOUT_VOL_RATIO = 2.0   # vol > avg × 2 + price up
WEAK_PULLBACK_VOL_RATIO = 0.7
FALSE_BREAKOUT_LOOKBACK = 10

# ============================================================
# Dedup
# ============================================================
DEDUP_WINDOW_MINUTES = 30   # 同信号 30 分钟不重复推送（10min 频率适配）

# ============================================================
# Push
# ============================================================
PUSHPLUS_URL = "https://www.pushplus.plus/send"
PUSH_TIMEOUT_SECONDS = 10

# ============================================================
# Browser
# ============================================================
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)
PAGE_LOAD_WAIT_MS = 6000      # 等待页面 JS 渲染
HOMEPAGE_WAIT_MS = 4000

# ============================================================
# Circuit breaker thresholds
# ============================================================
CB_MARKET_DAILY_DROP = -0.05
CB_MARKET_3D_DROP = -0.08
CB_ITEM_DAILY_DROP = -0.15
CB_REVIEW_INTERVAL_HOURS = 4

# ============================================================
# SteamDT homepage
# ============================================================
HOMEPAGE_URL = "https://www.steamdt.com"

# ============================================================
# Ensure dirs exist
# ============================================================
def ensure_dirs():
    for d in [SCREENSHOT_DIR, LOGS_DIR, DAILY_KLINE_DIR]:
        os.makedirs(d, exist_ok=True)
