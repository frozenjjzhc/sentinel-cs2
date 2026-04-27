"""
monitor_fast.py — Every 10 minutes
Scrapes data, computes indicators, evaluates BUY signals + legacy alerts,
pushes to PushPlus, persists state.

Usage:
    python monitor_fast.py             # Normal run (silent unless errors)
    python monitor_fast.py --test      # Verbose, doesn't push
    python monitor_fast.py --once      # Run one cycle (default behavior)
"""

import sys
import time
import argparse
import traceback

# --- Force UTF-8 output on Windows (避免 gbk 编码 ¥ 等中文符号失败) ---
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from lib import config
from lib import utils
from lib import state as state_mod
from lib import scraper as scraper_mod
from lib import indicators as ind_mod
from lib import stages as stages_mod
from lib import signals as signals_mod
from lib import pusher
from lib import shadow


def make_history_entry(scrape_data: dict, market: dict) -> dict:
    """Build a history entry from scraped data."""
    return {
        "t": utils.now_iso(),
        "price": scrape_data.get("price"),
        "today_pct": scrape_data.get("today_pct"),
        "week_pct": scrape_data.get("week_pct"),
        "today_volume": scrape_data.get("today_volume"),
        "stock": scrape_data.get("stock"),
        "market_index": market.get("market_index"),
        "market_pct": market.get("market_change_pct"),
    }


def make_signal_log(item, ind, stage, signal=None, suppress_reason=None):
    return {
        "t": utils.now_iso(),
        "price": ind.get("P"),
        "today_pct": item["history"][-1].get("today_pct") if item.get("history") else None,
        "week_pct": item["history"][-1].get("week_pct") if item.get("history") else None,
        "market_index": item["history"][-1].get("market_index") if item.get("history") else None,
        "momentum_score": ind.get("momentum_score"),
        "volume_quality": ind.get("volume_quality"),
        "stage": stage,
        "label": signal["label"] if signal else "NONE",
        "category": signal["category"] if signal else "NONE",
        "pushed": False,   # set later if pushed
        "advice": signal.get("advice") if signal else None,
        "next_tier": signal.get("next_tier") if signal else None,
        "_suppress_reason": suppress_reason,
    }


def make_recommendation_log(item, ind, signal):
    return {
        "t": utils.now_iso(),
        "label": signal["label"],
        "category": signal["category"],
        "trigger_price": ind.get("P"),
        "key_levels_at_time": dict(item.get("key_levels", {})),
        "fundamentals_bias": None,
        "advice": signal.get("advice"),
        "tier_suggestion": (
            f"第{signal['next_tier']}档 {int(signal['qty']*100)}%"
            if signal.get("next_tier") else None
        ),
        "tp_level": None,
        "pushed": True,
    }


def compose_push(item, ind, stage, signal, market, fundamentals):
    P = ind.get("P")
    title = f"【{signal['label']}】{item.get('short_name', item['id'])} ¥{P}"

    pos = item.get("position", {})
    legacy = item.get("legacy_holding")
    if pos.get("tiers"):
        position_str = (
            f"多 {int(pos.get('total_qty_pct',0)*100)}% 仓 "
            f"@均价¥{pos.get('avg_entry_price', 0):.2f}（"
            f"最高¥{pos.get('highest_since_first_entry', 0)}，"
            f"浮盈 {state_mod.compute_pnl_pct(item, P)*100:.2f}%）"
        )
    else:
        position_str = "无"
        if legacy:
            position_str += (
                f"（注：legacy 套牢仓 {legacy.get('quantity')} 把 "
                f"@¥{legacy.get('avg_entry_price')} 已心理隔离）"
            )

    body_lines = [
        f"信号：{signal['label']}",
        f"品种：{item.get('name')}",
        f"当前价：¥{P}",
        f"今日：{utils.fmt_pct((item['history'][-1].get('today_pct', 0) or 0)/100) if item.get('history') else 'n/a'}",
        f"本周：{utils.fmt_pct((item['history'][-1].get('week_pct', 0) or 0)/100) if item.get('history') else 'n/a'}",
        f"量价：成交 {ind.get('vol_avg') and item['history'][-1].get('today_volume')}（{ind.get('volume_quality') or '常规'}）",
        f"动能：score={ind.get('momentum_score', 0)}",
        f"阶段：{stage}",
        f"大盘：{market.get('market_index')} ({utils.fmt_pct((market.get('market_change_pct',0) or 0)/100)})",
        f"基本面：{fundamentals.get('bias', 'unknown')}",
        f"关键位：支撑 ¥{item.get('key_levels', {}).get('primary_support')}/¥{item.get('key_levels', {}).get('strong_support')} ｜ 阻力 ¥{item.get('key_levels', {}).get('resistance_1')}/¥{item.get('key_levels', {}).get('resistance_2')}",
        f"持仓：{position_str}",
        f"建议：{signal.get('advice', '-')}",
        f"时间：{utils.now_iso()}",
    ]
    return title, "\n".join(body_lines)


def compose_legacy_alert_push(item, alert):
    P = item["history"][-1].get("price") if item.get("history") else 0
    legacy = item["legacy_holding"]
    avg = legacy.get("avg_entry_price")
    pnl = (P - avg) / avg if avg and P else 0
    title = f"【{alert.get('label')}】套牢仓提醒 {item.get('short_name', item['id'])} ¥{P}"
    body_lines = [
        f"套牢仓：{legacy.get('quantity')} 把 @均价¥{avg}",
        f"当前价：¥{P}",
        f"浮亏率：{utils.fmt_pct(pnl)}",
        f"提示：{alert.get('msg', '')}",
        f"时间：{utils.now_iso()}",
    ]
    return title, "\n".join(body_lines)


def run_cycle(test_mode: bool = False, verbose: bool = False):
    """One scan cycle."""
    config.ensure_dirs()
    state_obj = state_mod.load_state()

    # 1. Browser session
    if verbose:
        print(f"[{utils.now_iso()}] Starting cycle (test_mode={test_mode})")

    with scraper_mod.SteamDTScraper() as scraper:
        # 2. Market index
        market = scraper.fetch_market()
        if verbose:
            print(f"  Market: {market}")
        if market.get("_error"):
            utils.log_error(config.ERROR_LOG, f"market_fetch_error: {market['_error']}")

        # 3. Loop items
        for item in state_obj.get("items", []):
            if verbose:
                print(f"\n  → Scanning {item.get('short_name', item['id'])}")

            scraped = scraper.fetch_item(item)
            if verbose:
                print(f"    Scraped: {scraped}")

            price = scraped.get("price")
            if price is None:
                utils.log_error(
                    config.ERROR_LOG,
                    f"{item['id']} extract_failed: {scraped.get('_error', 'no_price')}",
                )
                state_mod.append_signal_log(item, {
                    "t": utils.now_iso(),
                    "label": "ERROR",
                    "category": "ERROR",
                    "_error": scraped.get("_error", "no_price"),
                })
                continue

            # 4. Append history
            entry = make_history_entry(scraped, market)
            state_mod.append_history_entry(item, entry)

            # 5. Indicators
            ind = ind_mod.compute_indicators(item["history"])
            stage = stages_mod.detect_stage(item, ind)

            # 6. Position summary
            state_mod.compute_position_summary(item)

            # 7. BUY signals
            buy_signals = signals_mod.evaluate_buy_signals(state_obj, item, ind, stage, market)

            # 8. Stop-loss (T+7 advisory)
            stop_signals = signals_mod.evaluate_stop_loss(state_obj, item, ind)

            all_signals = stop_signals + buy_signals
            chosen_signal = all_signals[0] if all_signals else None

            # 9. Dedup check
            if chosen_signal:
                if signals_mod.is_duplicate(item, chosen_signal["label"], config.DEDUP_WINDOW_MINUTES):
                    if verbose:
                        print(f"    Signal {chosen_signal['label']} suppressed (dedup)")
                    state_mod.append_signal_log(
                        item,
                        make_signal_log(item, ind, stage, chosen_signal, suppress_reason="dedup"),
                    )
                    chosen_signal = None

            # 10. Push
            pushed = False
            if chosen_signal and not test_mode:
                tokens = state_obj.get("global", {}).get("pushplus_tokens", [])
                fundamentals = state_obj.get("global", {}).get("fundamentals", {})
                title, body = compose_push(item, ind, stage, chosen_signal, market, fundamentals)
                results = pusher.push_to_all(tokens, title, body, state=state_obj)
                pushed = pusher.any_succeeded(results)
                if verbose:
                    print(f"    Push results: {results}")

                if pushed:
                    item["last_signal_pushed"] = chosen_signal["label"]
                    item["last_signal_time"] = utils.now_iso()
                    state_mod.append_recommendation_log(item, make_recommendation_log(item, ind, chosen_signal))
                    # Shadow position record (only for BUY signals)
                    if chosen_signal.get("category") == "BUY":
                        shadow.record_signal(
                            item_id=item["id"],
                            label=chosen_signal["label"],
                            category="BUY",
                            entry_price=ind.get("P"),
                            context={
                                "stage": stage,
                                "today_pct": item["history"][-1].get("today_pct"),
                                "market_index": market.get("market_index"),
                                "fundamentals_bias": state_obj.get("global", {}).get("fundamentals", {}).get("bias"),
                            },
                        )

            # 11. Signal log
            sig_entry = make_signal_log(item, ind, stage, chosen_signal)
            sig_entry["pushed"] = pushed
            state_mod.append_signal_log(item, sig_entry)

            # 12. Legacy alerts (independent of main signal stream)
            triggered_alerts = signals_mod.check_legacy_alerts(item)
            for alert in triggered_alerts:
                if test_mode:
                    if verbose:
                        print(f"    Legacy alert (test mode, not pushed): {alert['label']}")
                    continue
                tokens = state_obj.get("global", {}).get("pushplus_tokens", [])
                title, body = compose_legacy_alert_push(item, alert)
                results = pusher.push_to_all(tokens, title, body, state=state_obj)
                if verbose:
                    print(f"    Legacy alert push: {results}")

            # Print summary line
            print(
                f"  [{item['id']}] price=¥{price} "
                f"today={item['history'][-1].get('today_pct')}% "
                f"mkt={market.get('market_index')} "
                f"mom={ind.get('momentum_score')} "
                f"vol={ind.get('volume_quality') or 'normal'} "
                f"stage={stage} "
                f"signal={chosen_signal['label'] if chosen_signal else 'NONE'} "
                f"pushed={'Y' if pushed else 'N'} "
                f"hist={len(item.get('history', []))}"
            )

    # 13. Save state
    state_mod.save_state(state_obj)
    if verbose:
        print(f"\n[{utils.now_iso()}] Cycle complete. State saved.")


def main():
    parser = argparse.ArgumentParser(description="CS2 Skin Monitor - Fast (10min)")
    parser.add_argument("--test", action="store_true", help="Verbose mode, no pushes")
    parser.add_argument("--once", action="store_true", help="Run one cycle then exit (default)")
    args = parser.parse_args()

    try:
        run_cycle(test_mode=args.test, verbose=args.test)
    except Exception as e:
        utils.log_error(config.ERROR_LOG, f"FATAL: {e}\n{traceback.format_exc()}")
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
