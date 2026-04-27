"""
daily_review.py — Every day at 23:00
Aggregates the day's data into a recap message and pushes to all tokens.
"""

import sys
import argparse
import traceback
from datetime import datetime, timedelta
from collections import Counter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from lib import config
from lib import utils
from lib import state as state_mod
from lib import pusher
from lib import shadow
from lib import portfolio as portfolio_mod
from lib import screenshots as screenshots_mod
from lib import news_monitor


def filter_today(history):
    today = datetime.now().astimezone().date().isoformat()
    return [h for h in history if h.get("t", "")[:10] == today]


def filter_today_signals(signals_log):
    today = datetime.now().astimezone().date().isoformat()
    return [s for s in signals_log if s.get("t", "")[:10] == today]


def build_item_summary(item) -> dict:
    today_hist = filter_today(item.get("history", []))
    today_signals = filter_today_signals(item.get("signals_log", []))

    if not today_hist:
        return {"id": item["id"], "no_data": True}

    prices = [h.get("price") for h in today_hist if h.get("price")]
    volumes = [h.get("today_volume") for h in today_hist if h.get("today_volume") is not None]
    if not prices:
        return {"id": item["id"], "no_data": True}

    p_open = prices[0]
    p_close = prices[-1]
    p_high = max(prices)
    p_low = min(prices)

    sig_categories = Counter([s.get("category", "NONE") for s in today_signals])
    pushed_count = sum(1 for s in today_signals if s.get("pushed"))

    pos = item.get("position", {})
    intraday_pnl = None
    if pos.get("tiers") and pos.get("avg_entry_price"):
        intraday_pnl = (p_close - pos["avg_entry_price"]) / pos["avg_entry_price"]

    return {
        "id": item["id"],
        "name": item.get("short_name", item["id"]),
        "open": p_open,
        "close": p_close,
        "high": p_high,
        "low": p_low,
        "change_pct": (p_close - p_open) / p_open if p_open else 0,
        "amplitude_pct": (p_high - p_low) / p_open if p_open else 0,
        "volume": volumes[-1] if volumes else None,
        "checks": len(today_hist),
        "current_stage": item.get("current_stage"),
        "signals": dict(sig_categories),
        "pushed": pushed_count,
        "rs_score_1h": item.get("rs_score_1h"),
        "position": {
            "qty_pct": pos.get("total_qty_pct", 0),
            "avg_entry": pos.get("avg_entry_price"),
            "intraday_pnl": intraday_pnl,
        } if pos.get("tiers") else None,
        "legacy_holding": item.get("legacy_holding"),
    }


def compose_review(state, items_summary, market_today):
    today = datetime.now().astimezone().date().isoformat()
    title = f"📊 当日复盘 {today}"

    lines = [
        f"📅 {today} CS2 饰品监控复盘",
        "━" * 18,
        "",
    ]

    # Market section
    if market_today:
        lines.append(
            f"🌐 大盘：{market_today['open']} → {market_today['close']} "
            f"({utils.fmt_pct(market_today['change_pct'])})"
        )
    fund = state.get("global", {}).get("fundamentals", {})
    lines.append(f"基本面偏置：{fund.get('bias', 'unknown')}")
    cb = state.get("global", {}).get("circuit_breaker", {})
    if cb.get("active"):
        lines.append(f"🚨 熔断中：{cb.get('reason')}")
    lines.append("━" * 18)
    lines.append("")

    # Per-item
    total_pushed = 0
    for s in items_summary:
        if s.get("no_data"):
            lines.append(f"📦 {s['id']}: 无当日数据")
            lines.append("")
            continue

        lines.append(f"📦 {s['name']}")
        lines.append(
            f"  价格：开 ¥{s['open']} → 收 ¥{s['close']} "
            f"({utils.fmt_pct(s['change_pct'])})"
        )
        lines.append(
            f"  区间：低 ¥{s['low']} ~ 高 ¥{s['high']} "
            f"(振幅 {utils.fmt_pct(s['amplitude_pct'])})"
        )
        lines.append(
            f"  成交：{s.get('volume')}  检查 {s['checks']} 次  "
            f"阶段 {s.get('current_stage', '?')}  "
            f"RS {s.get('rs_score_1h', '?')}"
        )

        sig = s.get("signals", {})
        sig_str = " ".join(f"{k}={v}" for k, v in sig.items())
        lines.append(f"  信号：{sig_str}（推送 {s['pushed']}）")
        total_pushed += s["pushed"]

        pos = s.get("position")
        if pos:
            pnl_str = utils.fmt_pct(pos["intraday_pnl"]) if pos.get("intraday_pnl") is not None else "n/a"
            lines.append(
                f"  持仓：多 {int(pos['qty_pct']*100)}% @¥{pos['avg_entry']:.2f} "
                f"浮盈 {pnl_str}"
            )
        else:
            lines.append("  持仓：无")

        legacy = s.get("legacy_holding")
        if legacy:
            avg = legacy.get("avg_entry_price")
            qty = legacy.get("quantity")
            P = s["close"]
            legacy_pnl = (P - avg) / avg if avg else 0
            lines.append(
                f"  套牢仓：{qty} 把 @¥{avg} → 当前 {utils.fmt_pct(legacy_pnl)}"
            )

        lines.append("")

    lines.append("━" * 18)

    # Portfolio summary
    portfolio_summary = portfolio_mod.compute_summary(state)
    if not portfolio_summary.get("empty"):
        lines.append("\n💼 总仓位")
        lines.append(portfolio_mod.format_summary_text(portfolio_summary))
        lines.append("")

    # Shadow signal stats
    stats = shadow.get_stats()
    if stats:
        lines.append("━" * 18)
        lines.append("🎯 影子信号回测（7 日收益胜率）")
        for label, s in sorted(stats.items(), key=lambda kv: kv[1]["count"], reverse=True):
            lines.append(
                f"  {label}: {s['count']} 次, "
                f"平均 {utils.fmt_pct(s['avg_return'])}, "
                f"胜率 {s['win_rate']*100:.0f}%, "
                f"最大 {utils.fmt_pct(s['max_return'])} / 最小 {utils.fmt_pct(s['min_return'])}"
            )
        pending = shadow.get_pending_count()
        if pending > 0:
            lines.append(f"  （待评估：{pending} 条）")
        lines.append("")

    lines.append("━" * 18)
    lines.append(f"📈 当日推送总数：{total_pushed}")
    lines.append(f"⏰ 生成时间：{utils.now_iso()}")

    return title, "\n".join(lines)


def get_market_today(state):
    items = state.get("items", [])
    if not items:
        return None
    anchor = items[0].get("history", [])
    today_hist = filter_today(anchor)
    if not today_hist:
        return None
    indices = [h.get("market_index") for h in today_hist if h.get("market_index")]
    if not indices:
        return None
    return {
        "open": indices[0],
        "close": indices[-1],
        "high": max(indices),
        "low": min(indices),
        "change_pct": (indices[-1] - indices[0]) / indices[0] if indices[0] else 0,
    }


def append_review_log(state, items_summary, market_today, pushed_to):
    log = state.setdefault("global", {}).setdefault("daily_review_log", [])
    log.append({
        "date": datetime.now().astimezone().date().isoformat(),
        "t": utils.now_iso(),
        "items_summary": items_summary,
        "market": market_today,
        "fundamentals_bias": state.get("global", {}).get("fundamentals", {}).get("bias"),
        "pushed_to": pushed_to,
    })
    if len(log) > config.DAILY_REVIEW_LOG_MAX:
        state["global"]["daily_review_log"] = log[-config.DAILY_REVIEW_LOG_MAX:]


def run_cycle(test_mode: bool = False, verbose: bool = False):
    config.ensure_dirs()
    state_obj = state_mod.load_state()

    # Evaluate any shadow positions due for 7-day check
    n_evaluated = shadow.evaluate_due_shadows(state_obj)
    if verbose and n_evaluated > 0:
        print(f"Evaluated {n_evaluated} shadow positions (7-day-old)")

    # Auto-refresh fundamentals from Steam News if due
    try:
        if news_monitor.update_fundamentals(state_obj):
            if verbose:
                print(f"Fundamentals refreshed from Steam News. New bias: {state_obj['global']['fundamentals'].get('bias')}")
    except Exception as e:
        utils.log_error(config.ERROR_LOG, f"news_monitor failed: {e}")

    # K-line screenshots (best-effort; runs in test mode too for verification)
    screenshot_results = {}
    try:
        if verbose:
            print("Taking K-line screenshots (this may take ~30s)...")
        screenshot_results = screenshots_mod.screenshot_all_items(state_obj)
        ok_count = sum(1 for v in screenshot_results.values() if v)
        if verbose:
            print(f"Screenshots: {ok_count} / {len(screenshot_results)} succeeded")
            for item_id, path in screenshot_results.items():
                status = f"✓ {path}" if path else "✗ failed"
                print(f"  {item_id}: {status}")
        # Cleanup old (keep 30 days)
        n_deleted = screenshots_mod.cleanup_old_screenshots(days_to_keep=30)
        if verbose and n_deleted > 0:
            print(f"Cleaned up {n_deleted} old screenshot folders")
    except Exception as e:
        utils.log_error(config.ERROR_LOG, f"screenshots failed: {e}")
        if verbose:
            print(f"Screenshot error: {e}")

    items_summary = [build_item_summary(item) for item in state_obj.get("items", [])]
    market_today = get_market_today(state_obj)

    title, body = compose_review(state_obj, items_summary, market_today)

    # Append screenshot info to body if available
    if screenshot_results:
        ok_count = sum(1 for v in screenshot_results.values() if v)
        if ok_count > 0:
            today_str = utils.now_local().date().isoformat()
            body += f"\n\n📸 K线截图：{ok_count}/{len(screenshot_results)} 张已存档 → screenshots/{today_str}/"

    pushed_to = []
    if not test_mode:
        tokens = state_obj.get("global", {}).get("pushplus_tokens", [])
        results = pusher.push_to_all(tokens, title, body, state=state_obj)
        pushed_to = pusher.succeeded_names(results)
        if verbose:
            print(f"Pushed: {results}")

    append_review_log(state_obj, items_summary, market_today, pushed_to)
    state_mod.save_state(state_obj)

    print(f"[Daily Review {datetime.now().date()}] items={len(items_summary)} pushed_to={pushed_to}")
    if verbose:
        print("\n" + body)


def main():
    parser = argparse.ArgumentParser(description="CS2 Skin Monitor - Daily Review")
    parser.add_argument("--test", action="store_true", help="Verbose, no push")
    args = parser.parse_args()

    try:
        run_cycle(test_mode=args.test, verbose=args.test)
    except Exception as e:
        utils.log_error(config.ERROR_LOG, f"FATAL daily_review: {e}\n{traceback.format_exc()}")
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
