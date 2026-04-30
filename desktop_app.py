"""
desktop_app.py — Sentinel 桌面壳（pywebview + pystray）

行为：
  - 启动：后台线程跑 uvicorn(backend_api)，主线程开 pywebview 窗口 + 系统托盘
  - 关闭窗口：仅隐藏到托盘，监控/API 持续运行
  - 托盘菜单：「打开 Sentinel」恢复窗口、「退出」真正结束所有进程
  - 单击托盘图标 = 恢复窗口

启动：
    pythonw desktop_app.py        # 无控制台窗口（Sentinel-Desktop.bat 推荐）
    python  desktop_app.py        # 带控制台，看日志用

打包：
    pyinstaller Sentinel.spec
"""

import os
import sys
import threading
import time
import traceback

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 错误日志：pythonw 模式下控制台输出不可见，写到磁盘兜底
ERROR_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "desktop_app_error.log")


def _log_error(msg: str):
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass
    try:
        print(msg, file=sys.stderr)
    except Exception:
        pass


try:
    import requests
    import uvicorn
    import webview
    import pystray
    from PIL import Image, ImageDraw
except ImportError as _e:
    _log_error(f"FATAL ImportError: {_e}\n请运行 pip install -r requirements.txt")
    sys.exit(1)


# 与 Sentinel.bat 一致：首次启动自动从 example 复制 state.json
from lib import config as _cfg
_state_file = _cfg.STATE_FILE
if not os.path.isfile(_state_file):
    _example = os.path.join(_cfg.PROJECT_DIR, "state.example.json")
    if os.path.isfile(_example):
        import shutil as _sh
        _sh.copy2(_example, _state_file)
        _log_error(f"[desktop] 首次启动：已从 state.example.json 创建 {_state_file}")


PORT = 8000


def _resolve_host() -> str:
    """从 state.global.lan.host 决定绑定地址；默认 127.0.0.1。"""
    try:
        from lib import state as _state_mod
        st = _state_mod.load_state()
        h = st.get("global", {}).get("lan", {}).get("host", "127.0.0.1")
        return "0.0.0.0" if h == "0.0.0.0" else "127.0.0.1"
    except Exception:
        return "127.0.0.1"


BIND_HOST = _resolve_host()
WEBVIEW_URL = f"http://127.0.0.1:{PORT}"


def _run_api():
    uvicorn.run(
        "backend_api:app",
        host=BIND_HOST,
        port=PORT,
        log_level="warning",
        access_log=False,
    )


def _is_api_alive() -> bool:
    try:
        r = requests.get(f"{WEBVIEW_URL}/api/health", timeout=0.4)
        return r.ok
    except Exception:
        return False


def _wait_ready(max_wait_sec: float = 8.0) -> bool:
    deadline = time.time() + max_wait_sec
    while time.time() < deadline:
        if _is_api_alive():
            return True
        time.sleep(0.15)
    return False


# ---------------- 托盘图标 ----------------
def _make_icon_image() -> "Image.Image":
    """生成托盘图标（CS2 紫渐变圆 + 中心瞄准星）。无外部图片依赖。"""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 渐变圆背景：用两个半透明同心圆模拟
    d.ellipse([2, 2, size - 2, size - 2], fill=(99, 102, 241, 255))      # indigo
    d.ellipse([12, 12, size - 12, size - 12], fill=(236, 72, 153, 255))  # pink center
    # 准星：白色十字
    cx = cy = size // 2
    d.line([(cx, cy - 14), (cx, cy + 14)], fill=(255, 255, 255), width=3)
    d.line([(cx - 14, cy), (cx + 14, cy)], fill=(255, 255, 255), width=3)
    d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=(255, 255, 255), width=2)
    return img


# 全局窗口/托盘引用，便于跨线程调用
_window: "webview.Window | None" = None
_tray: "pystray.Icon | None" = None
_quitting = False


def _show_window(icon=None, item=None):
    """从托盘菜单/双击调用：恢复窗口。"""
    if _window is not None:
        try:
            _window.show()
        except Exception as e:
            _log_error(f"show window error: {e}")


def _quit_app(icon=None, item=None):
    """从托盘菜单调用：彻底退出（停 uvicorn + 关窗口 + 关托盘）。"""
    global _quitting
    _quitting = True
    try:
        if _tray is not None:
            _tray.stop()
    except Exception:
        pass
    try:
        if _window is not None:
            _window.destroy()
    except Exception:
        pass
    # 强制结束（uvicorn 是 daemon thread，主线程 webview.start 会随 destroy 返回）
    os._exit(0)


def _on_window_closing():
    """关闭窗口时：隐藏到托盘 + 阻止 destroy。"""
    if _quitting:
        return True   # 正在真退出，放行 destroy
    try:
        if _window is not None:
            _window.hide()
    except Exception as e:
        _log_error(f"hide window error: {e}")
    return False   # 取消关闭


def _start_tray():
    """后台线程跑系统托盘。"""
    global _tray
    menu = pystray.Menu(
        pystray.MenuItem("打开 Sentinel", _show_window, default=True),
        pystray.MenuItem("退出 Sentinel", _quit_app),
    )
    _tray = pystray.Icon(
        "sentinel",
        icon=_make_icon_image(),
        title="Sentinel · CS2 监控（最小化中，点此恢复）",
        menu=menu,
    )
    # run_detached 让 pystray 在自己的线程跑，不阻塞主线程
    _tray.run_detached()


def main():
    global _window

    if _is_api_alive():
        _log_error(f"[desktop] 检测到 :8000 已有 API 在跑 → attach 模式（仅打开窗口）")
    else:
        _log_error(f"[desktop] backend bind = {BIND_HOST}:{PORT}, webview 将载入 {WEBVIEW_URL}")
        api_thread = threading.Thread(target=_run_api, daemon=True, name="sentinel-api")
        api_thread.start()
        if not _wait_ready():
            _log_error("WARN: API 8s 内未就绪，仍打开窗口（手动等加载）")

    # 启动托盘（后台线程，run_detached 内部自起）
    try:
        _start_tray()
    except Exception as e:
        _log_error(f"WARN: tray 启动失败（仍可用，但关窗口会真退出）: {e}\n{traceback.format_exc()}")

    try:
        _window = webview.create_window(
            "Sentinel · CS2 饰品智能监控",
            WEBVIEW_URL,
            width=1440,
            height=900,
            min_size=(1024, 700),
            background_color="#FFFFFF",
            confirm_close=False,
        )
        # 拦截关闭事件 → 改为隐藏到托盘
        _window.events.closing += _on_window_closing
        webview.start()   # 阻塞直到窗口被 destroy
        # 走到这里说明用户从托盘选了「退出」或异常，确保所有线程被结束
        _quit_app()
    except Exception as e:
        msg = (
            f"FATAL pywebview error: {type(e).__name__}: {e}\n"
            f"{traceback.format_exc()}\n"
            f"\n常见原因：\n"
            f"  1. WebView2 Runtime 未安装 — 去 https://developer.microsoft.com/microsoft-edge/webview2/ 下载安装\n"
            f"  2. 显卡驱动异常 / 远程桌面环境不支持\n"
            f"\n临时方案：浏览器打开 {WEBVIEW_URL} 也能用全部功能"
        )
        _log_error(msg)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:
        _log_error(f"FATAL main(): {type(e).__name__}: {e}\n{traceback.format_exc()}")
        sys.exit(1)
