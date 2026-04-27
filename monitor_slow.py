"""
monitor_slow.py — Every hour (run at minute 5 to avoid overlap with monitor_fast at :00)
- Re-reads state (history already updated by monitor_fast)
- Computes complete indicators on most-recent data
- Re-detects stage with longer-window context
- Detects stage changes (vs last hour)
- Evaluates SELL signals (with T+7 timing markers)
- Computes cross-item RS
- Reviews circuit breaker
- Pushes SELL alerts

Does NOT scrape (avoid race with monitor_fast).
"""

import sys
import argparse
import traceback

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from lib import config
from lib import utils
from lib import state as state_mod
from lib import indicators as ind_mod
from lib import stages as stages_mod
from lib import signals as signals_mod
from lib import pusher
from lib import circuit_breaker as cb_mod
from lib import correlation as corr_mod


def detect_stage_change(item, new_stage: str) -> bool:
    last = item.get("current_stage")
    if last != new_stage:
        item.setdefault("stage_changes", []).append({
            "t": utils.now_iso(),
            "from": last,
            "to": new_stage,
            "trigger_price": item.get("history", [{}])[-1].get("price") if item.get("history") else None,
        })
        # Trim stage_changes to last 100
        if len(item["stage_changes"]) > 100:
            item["stage_changes"] = item["stage_changes"][-100:]
        item["current_stage"] = new_stage
        return last is not None   # don't alert on first set
    return False


def compute_rs_score(item, anchor_history) -> float:
    """Relative strength: item 1H change / market 1H change."""
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
        return 1.0
    return item_change / market_change


def compose_sell_push(item, ind, stage, signal, market):
    P = ind.get("P")
    title = f"【{signal['label']}】{item.get('short_name', item['id'])} ¥{P}"

    pos = item.get("position", {})
    pnl_pct = state_mod.compute_pnl_pct(item, P) if pos.get("tiers") else 0

    # T+7 timing
    t7_note = ""
    if pos.get("tiers"):
        first_t = pos["tiers"][0].get("time")
        if first_t:
            days_held = utils.days_since(first_t)
            days_to_unlock = max(0, 7 - days_held)
            if days_to_unlock > 0:
                t7_note = f"\nT+7 锁定中：还需 {days_to_unlock:.1f} 天可执行卖出"
            else:
                t7_note = "\nT+7 已解锁：可立即执行"

    body_lines = [
        f"信号：{signal['label']}",
        f"品种：{item.get('name')}",
        f"当前价：¥{P}",
        f"阶段：{stage}",
        f"持仓：多 {int(pos.get('total_qty_pct',0)*100)}% @均价¥{pos.get('avg_entry_price',0):.2f} 浮盈 {pnl_pct*100:.2f}%",
        f"建议：{signal.get('advice', '-')}{t7_note}",
        f"大盘：{market.get('market_index')} ({utils.fmt_pct((market.get('market_change_pct',0) or 0)/100)})",
        f"时间：{utils.now_iso()}",
    ]
    return title, "\n".join(body_lines)


def compose_stage_change_push(item, old_stage, new_stage):
    P = item.get("history", [{}])[-1].get("price")
    title = f"【阶段切换】{item.get('short_name', item['id'])}: {old_stage} → {new_stage}"
    body_lines = [
        f"品种：{item.get('name')}",
        f"当前价：¥{P}",
        f"阶段切换：{old_stage} → {new_stage}",
        f"含义：{stage_meaning(new_stage)}",
        f"时间：{utils.now_iso()}",
    ]
    return title, "\n".join(body_lines)


def stage_meaning(stage: str) -> str:
    return {
        "ACCUMULATION": "庄家吸筹期：低位低量，可小仓位试探",
        "SHAKEOUT":     "洗盘期：急跌但未破底，恐慌买入机会",
        "COILING":      "蓄力期：波动率收敛，等待方向选择",
        "MARKUP":       "拉升期：放量突破，让利润奔跑",
        "DISTRIBUTION": "派发期：高位无量新高，准备分批止盈",
        "MARKDOWN":     "下跌期：跌破均线放量，T+7 解锁后优先卖",
        "UNKNOWN":      "数据不足或形态不明",
    }.get(stage, "未知")


def compose_cb_push(active: bool, reason: str):
    if active:
        title = f"🚨【熔断激活】{reason}"
        body = (
            f"原因：{reason}\n"
            f"动作：暂停所有 BUY 信号；A 类止损正常运行\n"
            f"复审：4 小时后自动检查\n"
            f"时间：{utils.now_iso()}"
        )
    else:
        title = "✅【熔断解除】市场恢复正常"
        body = f"全部信号恢复运行。\n时间：{utils.now_iso()}"
    return title, body


def run_cycle(test_mode: bool = False, verbose: bool = False):
    config.ensure_dirs()
    state_obj = state_mod.load_state()

    if verbose:
        print(f"[{utils.now_iso()}] monitor_slow cycle starting")

    # 1. Circuit breaker review
    cb_just_deactivated = cb_mod.auto_review(state_obj)
    cb_active_now, cb_reason = cb_mod.check_circuit_breaker(state_obj)
    cb_was_active = cb_mod.is_active(state_obj)

    if cb_active_now and not cb_was_active:
        cb_mod.activate(state_obj, cb_reason)
        if not test_mode:
            tokens = state_obj.get("global", {}).get("pushplus_tokens", [])
            title, body = compose_cb_push(True, cb_reason)
            pusher.push_to_all(tokens, title, body, state=state_obj)
        if verbose:
            print(f"  CIRCUIT BREAKER ACTIVATED: {cb_reason}")
    elif cb_just_deactivated:
        if not test_mode:
            tokens = state_obj.get("global", {}).get("pushplus_tokens", [])
            title, body = compose_cb_push(False, "")
            pusher.push_to_all(tokens, title, body, state=state_obj)
        if verbose:
            print("  CIRCUIT BREAKER DEACTIVATED")

    # 2. Use first item's history as anchor for market timing
    items = state_obj.get("items", [])
    anchor = items[0].get("history", []) if items else []
    market = {
        "market_index": anchor[-1].get("market_index") if anchor else None,
        "market_change_pct": anchor[-1].get("market_pct") if anchor else None,
    }

    # 3. Loop items: stage detection, RS, SELL signals
    for item in items:
        ind = ind_mod.compute_indicators(item.get("history", []))
        state_mod.compute_position_summary(item)

        new_stage = stages_mod.detect_stage(item, ind)
        stage_changed = detect_stage_change(item, new_stage)

        rs_score = compute_rs_score(item, anchor)
        item["rs_score_1h"] = round(rs_score, 3)

        # SELL signals — stop_loss + take_profit 合并，按 priority 选最高
        sell_signals = (
            signals_mod.evaluate_stop_loss(state_obj, item, ind)
            + signals_mod.evaluate_take_profit(state_obj, item, ind)
        )
        sell_signals.sort(key=lambda s: s.get("priority", 0), reverse=True)

        chosen = sell_signals[0] if sell_signals else None
        pushed = False

        if chosen and not test_mode:
            if signals_mod.is_duplicate(item, chosen["label"], 60):   # SELL dedup 1H
                if verbose:
                    print(f"  [{item['id']}] SELL {chosen['label']} suppressed (dedup)")
            else:
                tokens = state_obj.get("global", {}).get("pushplus_tokens", [])
                title, body = compose_sell_push(item, ind, new_stage, chosen, market)
                results = pusher.push_to_all(tokens, title, body, state=state_obj)
                pushed = pusher.any_succeeded(results)
                if pushed:
                    item["last_signal_pushed"] = chosen["label"]
                    item["last_signal_time"] = utils.now_iso()
                    # 如果是 TP 信号，标记为已执行，避免重复触发
                    if chosen.get("tp_level"):
                        pos = item.setdefault("position", {})
                        executed = pos.setdefault("tp_executed", [])
                        if chosen["tp_level"] not in executed:
                            executed.append(chosen["tp_level"])
                    state_mod.append_recommendation_log(item, {
                        "t": utils.now_iso(),
                        "label": chosen["label"],
                        "category": "SELL",
                        "trigger_price": ind.get("P"),
                        "key_levels_at_time": dict(item.get("key_levels", {})),
                        "advice": chosen.get("advice"),
                        "tier_suggestion": None,
                        "tp_level": chosen.get("tp_level"),
                        "bias_applied": chosen.get("bias_applied"),
                        "bias_stop_mult": chosen.get("bias_stop_mult"),
                        "bias_tp_mult": chosen.get("bias_tp_mult"),
                        "pushed": True,
                    })

        # Stage change push (independent of SELL)
        if stage_changed and not test_mode:
            old = item.get("stage_changes", [{}])[-1].get("from") if item.get("stage_changes") else None
            tokens = state_obj.get("global", {}).get("pushplus_tokens", [])
            title, body = compose_stage_change_push(item, old, new_stage)
            pusher.push_to_all(tokens, title, body, state=state_obj)
            if verbose:
                print(f"  [{item['id']}] Stage change: {old} → {new_stage}")

        print(
            f"  [{item['id']}] price=¥{ind.get('P')} "
            f"stage={new_stage} "
            f"rs={rs_score:.2f} "
            f"sell_signal={chosen['label'] if chosen else 'NONE'} "
            f"pushed={'Y' if pushed else 'N'} "
            f"hist={len(item.get('history', []))}"
        )

    # 4. Full 2-tier sector analysis
    full_analysis = corr_mod.detect_full_analysis(state_obj)
    state_obj.setdefault("global", {})["sector_analysis"] = full_analysis

    opportunities = corr_mod.find_following_opportunities(state_obj, full_analysis)
    if opportunities and not test_mode:
        tokens = state_obj.get("global", {}).get("pushplus_tokens", [])
        title = f"🔗【主板块跟涨机会】{len(opportunities)} 个品种"
        body_lines = ["主板块已有强领涨，以下品种未跟上 → 关注跟涨：\n"]
        items_dict = {it["id"]: it for it in state_obj.get("items", [])}
        for opp in opportunities[:5]:
            it = items_dict.get(opp["item_id"])
            if it:
                body_lines.append(
                    f"• {it.get('short_name', opp['item_id'])}: "
                    f"主板块「{opp['primary_sector']}」领涨 {opp['leader_id']} "
                    f"+{opp['gap_pct']*100:.1f}% (RS {opp['leader_rs']})"
                )
        body_lines.append(f"\n时间：{utils.now_iso()}")
        pusher.push_to_all(tokens, title, "\n".join(body_lines), state=state_obj)

    if verbose:
        print("\n  === 主板块（primary）===")
        for sec, info in full_analysis.get("primary", {}).items():
            avg = info.get("avg_rs", 0)
            led = info.get("leader") or {}
            print(f"    {sec}: avg={avg}, 领涨={led.get('id', 'n/a')} (RS {led.get('rs', 'n/a')})")
        print("  === 副板块（secondary）===")
        for sec, info in full_analysis.get("secondary", {}).items():
            avg = info.get("avg_rs", 0)
            led = info.get("leader") or {}
            print(f"    {sec}: avg={avg}, 领涨={led.get('id', 'n/a')} (RS {led.get('rs', 'n/a')})")
        print("  === 综合 RS（每品种）===")
        for iid, c in full_analysis.get("items", {}).items():
            print(
                f"    {iid}: 主={c.get('primary_sector_avg_rs')} "
                f"副={c.get('secondary_sector_avg_rs')} "
                f"自身={c.get('self_rs_1h')} → 综合={c.get('combined_rs')}"
            )

    state_mod.save_state(state_obj)
    if verbose:
        print(f"[{utils.now_iso()}] monitor_slow cycle done.")


def main():
    parser = argparse.ArgumentParser(description="CS2 Skin Monitor - Slow (1H)")
    parser.add_argument("--test", action="store_true", help="Verbose, no push")
    args = parser.parse_args()

    try:
        run_cycle(test_mode=args.test, verbose=args.test)
    except Exception as e:
        utils.log_error(config.ERROR_LOG, f"FATAL slow: {e}\n{traceback.format_exc()}")
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
