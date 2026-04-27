"""
K-line screenshot archiving.
Called from daily_review.py — opens playwright once, screenshots all items, saves PNGs.
"""

import os
from datetime import datetime
from . import config
from . import scraper as scraper_mod
from . import utils


def screenshot_all_items(state: dict) -> dict:
    """
    Walks all items in state, takes one K-line screenshot each.
    Saves to: screenshots/YYYY-MM-DD/<item_id>.png
    Returns: {item_id: relative_path_or_None}
    """
    today_str = datetime.now().astimezone().date().isoformat()
    dest_dir = os.path.join(config.SCREENSHOT_DIR, today_str)
    os.makedirs(dest_dir, exist_ok=True)

    results = {}
    items = state.get("items", [])
    if not items:
        return results

    try:
        with scraper_mod.SteamDTScraper() as scraper:
            for item in items:
                item_id = item["id"]
                save_path = os.path.join(dest_dir, f"{item_id}.png")
                rel_path = os.path.relpath(save_path, config.PROJECT_DIR)
                try:
                    scraper._page.goto(item["url"], wait_until="domcontentloaded")
                    scraper._page.wait_for_timeout(config.PAGE_LOAD_WAIT_MS)
                    # Wait extra for canvas to render
                    scraper._page.wait_for_timeout(2000)
                    success, method = scraper.screenshot_kline(save_path, debug=True)
                    if success:
                        results[item_id] = f"{rel_path} ({method})"
                    else:
                        results[item_id] = None
                        utils.log_error(
                            config.ERROR_LOG,
                            f"screenshot_kline {item_id} all methods failed",
                        )
                except Exception as e:
                    utils.log_error(
                        config.ERROR_LOG,
                        f"screenshot_kline {item_id} exception: {e}",
                    )
                    results[item_id] = None
    except Exception as e:
        utils.log_error(
            config.ERROR_LOG,
            f"screenshot_all_items playwright failed: {e}",
        )

    return results


def cleanup_old_screenshots(days_to_keep: int = 30):
    """Delete screenshot folders older than N days."""
    if not os.path.isdir(config.SCREENSHOT_DIR):
        return 0
    today = datetime.now().astimezone().date()
    deleted = 0
    for entry in os.listdir(config.SCREENSHOT_DIR):
        full = os.path.join(config.SCREENSHOT_DIR, entry)
        if not os.path.isdir(full):
            continue
        try:
            entry_date = datetime.fromisoformat(entry).date()
        except ValueError:
            continue
        age_days = (today - entry_date).days
        if age_days > days_to_keep:
            try:
                import shutil
                shutil.rmtree(full)
                deleted += 1
            except Exception:
                pass
    return deleted
