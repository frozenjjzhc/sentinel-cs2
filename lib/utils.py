"""
Time, formatting, error logging utilities.
"""

import os
import json
from datetime import datetime, timezone, timedelta


def now_iso() -> str:
    """Return ISO 8601 timestamp with local timezone offset."""
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def now_local() -> datetime:
    """Local time as datetime."""
    return datetime.now().astimezone()


def parse_iso(s: str) -> datetime:
    """Parse ISO timestamp."""
    return datetime.fromisoformat(s)


def hours_since(iso_str: str) -> float:
    """Hours between iso_str and now."""
    if not iso_str:
        return float("inf")
    return (now_local() - parse_iso(iso_str)).total_seconds() / 3600


def days_since(iso_str: str) -> float:
    return hours_since(iso_str) / 24


def is_expired(expires_at: str) -> bool:
    """Check whether an ISO date string is in the past."""
    if not expires_at:
        return False
    try:
        # Date-only string like "2026-05-03"
        if "T" not in expires_at:
            exp = datetime.fromisoformat(expires_at + "T23:59:59").astimezone()
        else:
            exp = parse_iso(expires_at)
        return exp < now_local()
    except Exception:
        return False


def fmt_pct(value: float, decimals: int = 2) -> str:
    """Format a fraction as percentage string with sign."""
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value*100:.{decimals}f}%"


def fmt_money(value: float, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"¥{value:,.{decimals}f}"


def safe_float(s, default=None):
    if s is None or s == "":
        return default
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return default


def safe_int(s, default=None):
    if s is None or s == "":
        return default
    try:
        return int(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return default


def log_error(error_log_path: str, message: str):
    """Append a timestamped line to error log."""
    os.makedirs(os.path.dirname(error_log_path) or ".", exist_ok=True)
    with open(error_log_path, "a", encoding="utf-8") as f:
        f.write(f"{now_iso()} {message}\n")


def write_json(path: str, data, indent=2):
    """Atomic write JSON via temp file + rename."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    os.replace(tmp, path)


def read_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
