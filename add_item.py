"""
add_item.py — 交互式新增监控品种向导

用法：
    python add_item.py

流程：
1. 输入 SteamDT URL
2. 自动抓取当前价 + 名称
3. 选择主板块 / 副板块（可新建）
4. 输入关键位（strong/primary/R1/R2/R3）
5. 选择是否用默认阈值（或自定义）
6. 预览 → 确认 → 写入 state.json
"""

import sys
import re
import json
import shutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from lib import config
from lib import utils
from lib import state as state_mod
from lib import scraper as scraper_mod


# ============================================================
# Helpers
# ============================================================
def ask(prompt, default=None, required=True, validator=None):
    """带默认值 + 验证的 input。"""
    while True:
        suffix = f" [默认 {default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}：").strip()
        if not raw and default is not None:
            return default
        if not raw and not required:
            return None
        if not raw:
            print("  ⚠️ 必填，请重新输入")
            continue
        if validator:
            err = validator(raw)
            if err:
                print(f"  ⚠️ {err}")
                continue
        return raw


def ask_float(prompt, default=None, required=True, min_val=None, max_val=None):
    while True:
        raw = ask(prompt, str(default) if default is not None else None, required)
        if raw is None:
            return None
        try:
            v = float(raw)
            if min_val is not None and v < min_val:
                print(f"  ⚠️ 必须 ≥ {min_val}")
                continue
            if max_val is not None and v > max_val:
                print(f"  ⚠️ 必须 ≤ {max_val}")
                continue
            return v
        except ValueError:
            print("  ⚠️ 请输入数字")


def ask_choice(prompt, options, allow_new=True):
    """从列表选一个或新建。返回选中的字符串。"""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    if allow_new:
        print(f"  {len(options)+1}. ➕ 新建分组")
    print(f"  0. 跳过（不归类）")
    while True:
        raw = input("选择编号: ").strip()
        if raw == "0":
            return None
        try:
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
            if allow_new and idx == len(options) + 1:
                new_name = ask("新分组名称")
                return new_name
            print("  ⚠️ 编号不在范围")
        except ValueError:
            print("  ⚠️ 请输入数字")


def slugify(text):
    """转 kebab-case id"""
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:50]


# ============================================================
# Main wizard
# ============================================================
def main():
    print("=" * 50)
    print("  CS2 监控品种 - 新增向导")
    print("=" * 50)
    print()

    # 1. URL
    url = ask(
        "SteamDT 商品 URL",
        validator=lambda s: None if s.startswith("https://www.steamdt.com/") else "URL 必须以 https://www.steamdt.com/ 开头"
    )

    # 2. Load state first (确认能读到)
    try:
        state = state_mod.load_state()
    except Exception as e:
        print(f"\n❌ 无法读取 state.json：{e}")
        sys.exit(1)

    existing_ids = {it["id"] for it in state.get("items", [])}

    # 3. Scrape current price
    print("\n🌐 正在打开页面抓取数据（约 30 秒）...")
    try:
        with scraper_mod.SteamDTScraper() as scraper:
            scraped = scraper.fetch_item({"url": url})
    except Exception as e:
        print(f"❌ 抓取失败：{e}")
        sys.exit(1)

    price = scraped.get("price")
    if not price:
        print(f"❌ 无法解析当前价格。返回：{scraped}")
        if not ask("是否继续手动输入价格？(y/n)", "n").lower().startswith("y"):
            sys.exit(1)
        price = ask_float("当前价格 ¥", min_val=0.01)

    print(f"\n✓ 抓到当前价: ¥{price}")
    print(f"  今日: {scraped.get('today_pct')}%  |  本周: {scraped.get('week_pct')}%")
    print(f"  成交: {scraped.get('today_volume')}  |  存世: {scraped.get('stock')}")

    # 4. Item meta
    print("\n--- 品种元数据 ---")
    full_name = ask("完整中文名（如 'AWP | 二西莫夫 (崭新出厂)'）")
    short_name = ask("推送显示的简短名（如 'AWP 二西莫夫'）", default=full_name[:20])

    suggested_id = slugify(full_name)
    while True:
        item_id = ask("唯一 id（kebab-case）", default=suggested_id)
        if item_id in existing_ids:
            print(f"  ⚠️ id '{item_id}' 已存在，请改名")
            continue
        break

    # 5. Sector
    sectors = state.get("global", {}).setdefault("sectors", {})
    primary_groups = sectors.setdefault("primary", {})
    secondary_groups = sectors.setdefault("secondary", {})
    weights = sectors.setdefault("weights", {"primary": 0.7, "secondary": 0.3})

    print("\n--- 主板块（产出来源，权重 70%）---")
    primary_options = [k for k in primary_groups.keys() if not k.startswith("_template")]
    primary_choice = ask_choice("选择主板块", primary_options, allow_new=True)
    if primary_choice:
        primary_groups.setdefault(primary_choice, []).append(item_id)

    print("\n--- 副板块（武器系列，权重 30%）---")
    secondary_options = list(secondary_groups.keys())
    secondary_choice = ask_choice("选择副板块", secondary_options, allow_new=True)
    if secondary_choice:
        secondary_groups.setdefault(secondary_choice, []).append(item_id)

    # 6. Key levels
    print("\n--- 关键位（请打开网页看 K 线后填写）---")
    print(f"  当前价参考：¥{price}")
    print("  支撑通常在历史低点 / MA60 / 近期密集成交区")
    print("  阻力通常在前期高点 / MA10 / MA30")
    print()
    strong_support = ask_float("强支撑（历史最低附近）", min_val=0.01)
    primary_support = ask_float("主支撑（近期低点 / 心理位）", min_val=strong_support, default=round(price * 0.95, 2))
    r1 = ask_float("阻力 R1（近期反弹高）", min_val=price)
    r2 = ask_float("阻力 R2（中期阻力）", min_val=r1)
    r3 = ask_float("阻力 R3（历史峰附近）", min_val=r2)

    # 7. Thresholds
    print("\n--- 阈值参数 ---")
    use_default = ask("使用默认阈值？(y/n)", default="y").lower().startswith("y")
    if use_default:
        thresholds = {
            "today_pct_for_d1": 1.5,
            "rapid_drop_pct_1h": 4,
            "rapid_rise_pct_1h": 5,
            "d1_distance_to_r1_min": 0.02,
            "min_volume_d1": 8,
        }
    else:
        thresholds = {
            "today_pct_for_d1": ask_float("D1 触发今日涨幅阈值 %", default=1.5, min_val=0.1),
            "rapid_drop_pct_1h": ask_float("1H 急跌阈值 %", default=4.0, min_val=1.0),
            "rapid_rise_pct_1h": ask_float("1H 急涨阈值 %", default=5.0, min_val=1.0),
            "d1_distance_to_r1_min": ask_float("D1 距 R1 最小距离（小数，如 0.02 = 2%）", default=0.02, min_val=0.001),
            "min_volume_d1": int(ask_float("D1 触发最小当日成交量", default=8, min_val=1)),
        }

    # 8. Phase note
    phase_options = [
        "deep_correction_recovery",
        "high_consolidation_post_crash",
        "v_rebound_breakout",
        "stable_uptrend",
        "stable_downtrend",
        "sideways",
    ]
    print("\n--- 当前阶段判断 ---")
    phase = ask_choice("选择阶段标签", phase_options, allow_new=True)
    phase_note = ask("阶段备注（一句话描述当前 K 线形态）", required=False) or ""

    # 9. Build new item
    new_item = {
        "id": item_id,
        "name": full_name,
        "short_name": short_name,
        "url": url,
        "phase": phase or "unknown",
        "phase_note": phase_note,
        "key_levels": {
            "strong_support": strong_support,
            "primary_support": primary_support,
            "current_baseline": price,
            "resistance_1": r1,
            "resistance_2": r2,
            "resistance_3": r3,
        },
        "thresholds": thresholds,
        "history": [],
        "highest_observed": price,
        "lowest_observed": price,
        "position": {
            "tiers": [],
            "avg_entry_price": None,
            "total_qty_pct": 0,
            "highest_since_first_entry": None,
            "tp_executed": [],
        },
        "signals_log": [],
        "recommendations_log": [],
        "last_signal_pushed": None,
        "last_signal_time": None,
    }

    # 10. Preview
    print("\n" + "=" * 50)
    print("  预览新品种")
    print("=" * 50)
    print(f"  ID:          {item_id}")
    print(f"  名称:        {full_name}")
    print(f"  短名:        {short_name}")
    print(f"  URL:         {url}")
    print(f"  当前价:      ¥{price}")
    print(f"  主板块:      {primary_choice or '(未归类)'}")
    print(f"  副板块:      {secondary_choice or '(未归类)'}")
    print(f"  关键位:      支撑 ¥{strong_support} / ¥{primary_support} | 阻力 ¥{r1} / ¥{r2} / ¥{r3}")
    print(f"  阶段:        {phase or 'unknown'}")
    print(f"  阈值:        {json.dumps(thresholds, ensure_ascii=False)}")
    print()

    if not ask("确认写入 state.json？(y/n)", default="y").lower().startswith("y"):
        print("已取消，没有任何改动。")
        sys.exit(0)

    # 11. Backup state.json + write
    backup_path = config.STATE_FILE + ".bak"
    try:
        shutil.copy2(config.STATE_FILE, backup_path)
        print(f"✓ 已备份原 state 到 {backup_path}")
    except Exception as e:
        print(f"⚠️ 备份失败（不影响写入）：{e}")

    state.setdefault("items", []).append(new_item)
    try:
        state_mod.save_state(state)
        print(f"\n✅ 成功！state.json 已更新。")
        print(f"   当前监控品种数：{len(state['items'])}")
        print(f"   下次 monitor_fast 自动开始抓取该品种。")
    except Exception as e:
        print(f"\n❌ 写入失败：{e}")
        print(f"   原状态文件未变（备份在 {backup_path}）。")
        sys.exit(1)

    print("\n提示：")
    print("  • 前 5-10 小时 history 不足以算 ma_short，正常")
    print("  • 触发首次 BUY 信号约需积累 1-2 天数据")
    print("  • 想立刻测试：python monitor_fast.py --test")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消（Ctrl+C）。state.json 未改动。")
        sys.exit(0)
