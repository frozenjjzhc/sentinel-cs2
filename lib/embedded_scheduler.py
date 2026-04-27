"""
lib/embedded_scheduler.py - Run monitor tasks inside the API process.

Default behavior: when backend_api.py starts, it auto-starts these tasks:
  - monitor_fast.run_cycle()    every 10 minutes
  - monitor_slow.run_cycle()    every 60 minutes
  - daily_review.run_cycle()    daily at 23:00 local

This eliminates the need for Windows Task Scheduler, making the whole
project deployable as "double-click Sentinel.bat -> done".

Users can still use Task Scheduler if they prefer (set
state.global.scheduler.mode = "external" via UI or directly).
"""

import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Callable, Dict

from . import config
from . import utils


# ============================================================
# Module-level state (single instance per process)
# ============================================================
_tasks: Dict[str, asyncio.Task] = {}

_status = {
    "enabled":   False,
    "started_at": None,
    "tasks": {
        "monitor_fast": {
            "label":    "monitor_fast",
            "schedule": "every 10 min",
            "running":  False,
            "last_run": None,
            "next_run": None,
            "last_ok":  None,
            "last_error": None,
            "errors":   0,
            "runs":     0,
        },
        "monitor_slow": {
            "label":    "monitor_slow",
            "schedule": "every 60 min",
            "running":  False,
            "last_run": None,
            "next_run": None,
            "last_ok":  None,
            "last_error": None,
            "errors":   0,
            "runs":     0,
        },
        "daily_review": {
            "label":    "daily_review",
            "schedule": "daily at 23:00",
            "running":  False,
            "last_run": None,
            "next_run": None,
            "last_ok":  None,
            "last_error": None,
            "errors":   0,
            "runs":     0,
        },
    },
}


# ============================================================
# Helpers
# ============================================================
async def _run_one_cycle(name: str, fn: Callable):
    """执行一次任务，更新状态。"""
    s = _status["tasks"][name]
    s["running"] = True
    started = datetime.now().astimezone()
    try:
        await asyncio.to_thread(fn, False, False)   # test_mode=False, verbose=False
        s["last_ok"] = utils.now_iso()
        s["last_error"] = None
    except Exception as e:
        s["errors"] += 1
        s["last_error"] = f"{type(e).__name__}: {e}"
        try:
            utils.log_error(
                config.ERROR_LOG,
                f"embedded_scheduler[{name}] FAIL: {e}\n{traceback.format_exc()}",
            )
        except Exception:
            pass
    finally:
        s["running"] = False
        s["last_run"] = utils.now_iso()
        s["runs"] += 1
        elapsed = (datetime.now().astimezone() - started).total_seconds()
        s["last_duration_sec"] = round(elapsed, 1)


async def _periodic_loop(name: str, fn: Callable, interval_seconds: int):
    """循环：先睡 → 跑一次 → 重复。"""
    s = _status["tasks"][name]
    # 启动后等一小段时间再首次执行（避免冷启动 race）
    await asyncio.sleep(15)
    while _status["enabled"]:
        s["next_run"] = (datetime.now().astimezone() + timedelta(seconds=interval_seconds)).isoformat()
        await _run_one_cycle(name, fn)
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break


async def _daily_at_loop(name: str, fn: Callable, hour: int, minute: int = 0):
    """每天 hour:minute 跑一次。"""
    s = _status["tasks"][name]
    while _status["enabled"]:
        now = datetime.now().astimezone()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        s["next_run"] = target.isoformat()
        sleep_secs = max(5, (target - now).total_seconds())
        try:
            await asyncio.sleep(sleep_secs)
        except asyncio.CancelledError:
            break
        if not _status["enabled"]:
            break
        await _run_one_cycle(name, fn)


# ============================================================
# Public API
# ============================================================
def start():
    """启动嵌入式调度器。重复调用幂等。"""
    if _status["enabled"]:
        return False
    _status["enabled"] = True
    _status["started_at"] = utils.now_iso()

    # 延迟导入：避免 lib 模块循环依赖 + 让 API 启动更快
    import monitor_fast as mf_mod
    import monitor_slow as ms_mod
    import daily_review as dr_mod

    loop = asyncio.get_event_loop()
    _tasks["fast"]  = loop.create_task(_periodic_loop("monitor_fast", mf_mod.run_cycle, 600))
    _tasks["slow"]  = loop.create_task(_periodic_loop("monitor_slow", ms_mod.run_cycle, 3600))
    _tasks["daily"] = loop.create_task(_daily_at_loop("daily_review", dr_mod.run_cycle, 23, 0))
    return True


async def stop():
    """停止调度器，等所有任务取消完成。"""
    if not _status["enabled"]:
        return False
    _status["enabled"] = False
    for t in _tasks.values():
        t.cancel()
    # 等所有取消完成（最多 3 秒）
    for t in _tasks.values():
        try:
            await asyncio.wait_for(asyncio.shield(t), timeout=3)
        except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
            pass
    _tasks.clear()
    return True


def get_status():
    return _status


async def trigger_now(task_name: str) -> dict:
    """手动立即触发一次某个 task。"""
    if task_name not in _status["tasks"]:
        return {"ok": False, "error": f"未知任务: {task_name}"}
    s = _status["tasks"][task_name]
    if s["running"]:
        return {"ok": False, "error": "任务正在运行中，请稍候"}
    func_map = {
        "monitor_fast": lambda: __import__("monitor_fast").run_cycle,
        "monitor_slow": lambda: __import__("monitor_slow").run_cycle,
        "daily_review": lambda: __import__("daily_review").run_cycle,
    }
    fn = func_map[task_name]()
    await _run_one_cycle(task_name, fn)
    return {"ok": True, "status": s}
