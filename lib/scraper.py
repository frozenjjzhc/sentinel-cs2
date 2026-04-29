"""
SteamDT scraping via Playwright (headless Chromium with persistent context).

v2 fix: today_pct now prefers head-line value (right next to current price);
"今日" block fallback is more robust to skip "今日推算成交" prefix.
"""

import re
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

from . import config


# ============================================================
# Regex patterns (verified against real SteamDT pages)
# ============================================================

# Homepage market index: "1,014.03\n+0.87+0.09%" (no spaces)
RE_MARKET = re.compile(
    r"([\d,]+\.\d+)\s*([+-][\d,]+\.\d+)([+-]\d+\.\d+)%"
)

# Item page header: "¥4348.5+ 1.19 %" (price + same-day change side-by-side)
RE_HEAD_PRICE = re.compile(
    r"¥\s*(\d+(?:\.\d+)?)\s*([+-])\s*(\d+\.\d+)\s*%"
)

# 今日 / 本周 / 本月 block: "今日 ↓\n¥-47.5(-1.11%)" or "今日 \n¥51 (+1.19%)"
RE_PERIOD_BLOCK = re.compile(
    r"¥\s*([+-]?[\d.]+)\s*\(\s*(-?\d+\.\d+)\s*%\s*\)"
)

# 今日推算成交
RE_TODAY_VOLUME = re.compile(r"今日推算成交[:：]?\s*([\d,]+)")

# 存世量
RE_STOCK = re.compile(r"存世量[:：]?\s*([\d,]+)")


def _extract_period_pct(text: str, label: str):
    """
    Find label like "今日 " (with trailing space) or "今日\n" (with newline)
    to skip past "今日推算成交:" header which uses 今日推算 prefix.
    Returns the percentage or None.
    """
    # Patterns that mark the *real* period block (not the volume header)
    candidates = [
        f"{label} ↑",
        f"{label} ↓",
        f"{label} \n",
        f"{label}\n¥",
        f"{label} ¥",
    ]
    idx = -1
    for cand in candidates:
        i = text.find(cand)
        if i >= 0 and (idx < 0 or i < idx):
            idx = i
    if idx < 0:
        # Fallback: just find label and skip if next chars look like "推算成交"
        i = text.find(label)
        while i >= 0:
            if text[i:i+8].startswith(label + "推算"):
                i = text.find(label, i + 1)
                continue
            idx = i
            break
    if idx < 0:
        return None

    # Take a 100-char slice from idx, look for "¥X (Y%)" pattern
    slice_ = text[idx : idx + 100]
    m = RE_PERIOD_BLOCK.search(slice_)
    if m:
        try:
            return float(m.group(2))
        except ValueError:
            return None
    return None


class SteamDTScraper:
    """
    Context manager wrapping a persistent playwright browser.
    """

    def __init__(self, profile_dir=None, headless=True):
        self.profile_dir = profile_dir or config.PLAYWRIGHT_PROFILE
        self.headless = headless
        self._pw = None
        self._context = None
        self._page = None

    def __enter__(self):
        self._pw = sync_playwright().start()
        # 优先用系统已装的 Chrome（在国内不需要下载 Chromium，秒启）
        # 失败回落到 Playwright 自带的 Chromium
        common_kwargs = dict(
            user_data_dir=self.profile_dir,
            headless=self.headless,
            viewport={"width": 1400, "height": 900},
            user_agent=config.USER_AGENT,
        )
        try:
            self._context = self._pw.chromium.launch_persistent_context(
                **common_kwargs,
                channel="chrome",   # 系统 Chrome
            )
        except Exception:
            # 回落：用 Playwright 自带的 Chromium（如果通过 setup.bat 装了）
            self._context = self._pw.chromium.launch_persistent_context(**common_kwargs)
        self._page = (
            self._context.pages[0] if self._context.pages else self._context.new_page()
        )
        if STEALTH_AVAILABLE:
            try:
                stealth_sync(self._page)
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self._context:
                self._context.close()
        finally:
            if self._pw:
                self._pw.stop()

    # ------------------------------------------------------------
    # Market index (homepage)
    # ------------------------------------------------------------
    def fetch_market(self) -> dict:
        try:
            self._page.goto(config.HOMEPAGE_URL, wait_until="domcontentloaded")
            self._page.wait_for_timeout(config.HOMEPAGE_WAIT_MS)
            text = self._page.inner_text("body")
        except Exception as e:
            return {"market_index": None, "market_change_pct": None, "_error": str(e)}

        idx = text.find("大盘指数")
        if idx < 0:
            return {"market_index": None, "market_change_pct": None}
        slice_ = text[idx : idx + 200]
        m = RE_MARKET.search(slice_)
        if not m:
            return {"market_index": None, "market_change_pct": None}
        return {
            "market_index": float(m.group(1).replace(",", "")),
            "market_change_abs": float(m.group(2).replace(",", "")),
            "market_change_pct": float(m.group(3)),
        }

    # ------------------------------------------------------------
    # Item page
    # ------------------------------------------------------------
    def fetch_item(self, item: dict) -> dict:
        url = item["url"]
        image_url = None
        try:
            self._page.goto(url, wait_until="domcontentloaded")
            self._page.wait_for_timeout(config.PAGE_LOAD_WAIT_MS)
            text = self._page.inner_text("body")
            # 尝试抓饰品主图。优先级：
            # 1) img.zbt.com/e/steam/item/730/<base64-饰品名>.png  ← 真正的饰品独立图
            # 2) cdn.steamdt.com/common/<uuid>.webp 且 >=200x200，但要排除已知的共用 banner UUID
            # 3) 兼容旧 Steam 官方 CDN
            try:
                image_url = self._page.evaluate("""() => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    // SteamDT 页面顶部共用资源（每个页面都一样，不是饰品图）需要跳过
                    const SHARED_BANNERS = [
                        'c2c8ea0d-45d8-47df-a528-8665d48d5c53',  // 顶部 300x300 共用 banner
                    ];
                    // 1) img.zbt.com 饰品独立图（最优先）
                    for (const img of imgs) {
                        const src = img.src || '';
                        if (src.includes('img.zbt.com/e/steam/item/')) return src;
                    }
                    // 2) cdn.steamdt.com/common/<uuid>.webp，跳过共用 banner
                    for (const img of imgs) {
                        const src = img.src || '';
                        if (src.includes('cdn.steamdt.com/common/') &&
                            /\\.(webp|png|jpg|jpeg)$/i.test(src) &&
                            (img.naturalWidth || 0) >= 200 &&
                            (img.naturalHeight || 0) >= 200 &&
                            !SHARED_BANNERS.some(b => src.includes(b))) {
                            return src;
                        }
                    }
                    // 3) 兼容：Steam 官方 CDN
                    for (const img of imgs) {
                        const src = img.src || '';
                        if (src.includes('steamstatic') ||
                            src.includes('steamcommunity-a') ||
                            src.includes('cloudflare.steamstatic')) {
                            return src;
                        }
                    }
                    return null;
                }""")
            except Exception:
                pass
        except Exception as e:
            return {"price": None, "_error": str(e)}

        # 1. Head: price + today_pct (always right next to each other in DOM)
        head_m = RE_HEAD_PRICE.search(text)
        price = None
        today_pct = None
        if head_m:
            price = float(head_m.group(1))
            try:
                today_pct = float(head_m.group(2) + head_m.group(3))
            except ValueError:
                today_pct = None

        # 2. 今日 block (cross-check; prefer if it gives a saner value than head)
        today_block = _extract_period_pct(text, "今日")
        if today_block is not None:
            # Sanity check: if differs from head value by >1.5%, prefer block
            # (head value can sometimes be stale/multi-period in edge cases)
            if today_pct is None or abs(today_block - today_pct) > 1.5:
                today_pct = today_block

        # 3. 本周 block
        week_pct = _extract_period_pct(text, "本周")

        # 3b. 本月 block (informational)
        month_pct = _extract_period_pct(text, "本月")

        # 4. Volume
        today_volume = None
        vm = RE_TODAY_VOLUME.search(text)
        if vm:
            try:
                today_volume = int(vm.group(1).replace(",", ""))
            except ValueError:
                today_volume = None

        # 5. Stock
        stock = None
        sm = RE_STOCK.search(text)
        if sm:
            try:
                stock = int(sm.group(1).replace(",", ""))
            except ValueError:
                stock = None

        return {
            "price": price,
            "today_pct": today_pct,
            "week_pct": week_pct,
            "month_pct": month_pct,
            "today_volume": today_volume,
            "stock": stock,
            "image_url": image_url,   # Steam CDN 饰品图（首次抓取时存到 item.image_url）
        }

    def screenshot_kline(self, save_path: str, debug: bool = False, view: str = "日K") -> tuple:
        """
        截 SteamDT 主 K 线图。
        步骤：
        1. 切到 "K线图" tab（如果当前不在）
        2. 切到指定视图（默认日K）
        3. 找页面上面积最大的 canvas（K线主图）
        4. 包含 K 线 + VOL + MACD 三块的完整区域截图
        Returns (success: bool, method: str)
        """
        # 1. 确保切到 "K线图" tab
        try:
            for tab_text in ["K线图", "K线图"]:
                tab = self._page.locator(f"text={tab_text}").first
                if tab.count() > 0:
                    try:
                        tab.click(timeout=2000)
                        self._page.wait_for_timeout(800)
                        break
                    except Exception:
                        pass
        except Exception:
            pass

        # 2. 切到日K（或指定视图）
        try:
            view_tab = self._page.locator(f"text={view}").first
            if view_tab.count() > 0:
                view_tab.click(timeout=2000)
                self._page.wait_for_timeout(1500)
        except Exception:
            pass

        # 3. 用 JS 找到最大的 canvas（按面积），并把它的位置 + 父容器位置返回
        try:
            chart_info = self._page.evaluate("""
                () => {
                    const canvases = Array.from(document.querySelectorAll('canvas'));
                    if (canvases.length === 0) return null;
                    // 按面积排序，最大的是主 K 线图
                    const ranked = canvases.map(c => {
                        const r = c.getBoundingClientRect();
                        return {
                            width: c.width || r.width,
                            height: c.height || r.height,
                            area: (c.width || r.width) * (c.height || r.height),
                            x: r.x, y: r.y, w: r.width, h: r.height,
                            visible: r.width > 100 && r.height > 100,
                            // 找最近的 chart 容器
                            parent_rect: (() => {
                                let p = c.parentElement;
                                let depth = 0;
                                while (p && depth < 5) {
                                    if (p.className && (
                                        p.className.toString().includes('chart') ||
                                        p.className.toString().includes('kline')
                                    )) {
                                        const pr = p.getBoundingClientRect();
                                        return {x: pr.x, y: pr.y, w: pr.width, h: pr.height};
                                    }
                                    p = p.parentElement;
                                    depth++;
                                }
                                return null;
                            })()
                        };
                    }).filter(c => c.visible).sort((a, b) => b.area - a.area);
                    return ranked[0] || null;
                }
            """)
            if chart_info:
                # 优先用父容器范围（包含 K线 + VOL + MACD），fallback 到 canvas 本身
                clip_rect = chart_info.get("parent_rect") or {
                    "x": chart_info["x"],
                    "y": chart_info["y"],
                    "w": chart_info["w"],
                    "h": chart_info["h"],
                }
                # 防超出视口
                vp = self._page.viewport_size
                clip = {
                    "x": max(0, clip_rect["x"]),
                    "y": max(0, clip_rect["y"]),
                    "width": min(clip_rect["w"], vp["width"] - max(0, clip_rect["x"])),
                    "height": min(clip_rect["h"], vp["height"] - max(0, clip_rect["y"])),
                }
                if clip["width"] > 200 and clip["height"] > 200:
                    self._page.screenshot(path=save_path, clip=clip, full_page=False)
                    return True, f"main_canvas {int(clip['width'])}x{int(clip['height'])} ({view})"
        except Exception as e:
            if debug:
                print(f"  largest canvas method failed: {e}")

        # 4. Fallback: 视口右半部分（K 线通常在右边）
        try:
            vp = self._page.viewport_size
            self._page.screenshot(
                path=save_path,
                clip={
                    "x": int(vp["width"] * 0.40),
                    "y": int(vp["height"] * 0.35),
                    "width": int(vp["width"] * 0.55),
                    "height": int(vp["height"] * 0.55),
                },
            )
            return True, f"viewport_right_half ({view})"
        except Exception as e:
            if debug:
                print(f"  viewport clip failed: {e}")

        # 5. 最后兜底：全页
        try:
            self._page.screenshot(path=save_path, full_page=False)
            return True, "full_page"
        except Exception:
            return False, "all_failed"

    def push_via_browser(self, token: str, title: str, body: str) -> dict:
        result = self._page.evaluate(
            """
            async ({token, title, body}) => {
                const r = await fetch('https://www.pushplus.plus/send', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({token, title, content: body, template: 'txt'})
                });
                return {status: r.status, body: await r.text()};
            }
            """,
            {"token": token, "title": title, "body": body},
        )
        return result
