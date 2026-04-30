# v3.0.1 — 监控加速 · 桌面单实例守卫

## 重点

**两件实用性补丁**：
1. **监控速度提升 ~2.5×**：原本每件饰品死等 6 秒已改为「等到价格元素出现就走」，单件 6.3s → ~2s，可监控品种上限从 ~75 件提升到 ~200 件
2. **桌面端单实例**：双击 `Sentinel-Desktop.bat` 第二次不再开新窗口/新托盘 — 自动把已有窗口拉到前台

## 性能改进

### ⚡ 动态 wait 替代固定 6 秒死等

[lib/scraper.py](https://github.com/frozenjjzhc/sentinel-cs2/blob/main/lib/scraper.py)：原逻辑 `goto → wait_for_timeout(6000) → 解析`，无论页面 1 秒就绪还是 5 秒，都强制睡 6 秒。

改为：
```python
page.wait_for_function("...价格 head 正则匹配...", timeout=8000)
page.wait_for_timeout(300)   # grace
```
价格元素一出现立刻继续，平均 1.5-2 秒命中。匹配失败有兜底回到固定 wait，零回归风险。

`fetch_market()` 同样改造（等"大盘指数"文本出现）。

### 🚫 拦截图片/字体/媒体下载

价格抓取只看文本，浏览器没必要拉饰品图、字体、视频。新增 `block_images=True` 默认开启，节省带宽 + 加快渲染。

例外：[monitor_fast.py](https://github.com/frozenjjzhc/sentinel-cs2/blob/main/monitor_fast.py) 检测到任何 item 还没拿到 `image_url` 时本轮放行图片，跑 1-2 个 cycle 自动补齐后所有后续 cycle 都拦截。

### 性能预估

| 场景 | v3.0.0 | v3.0.1 |
|---|---|---|
| 单件平均耗时 | 6.3s | 1.8-2.5s |
| 50 件 cycle | ~315s | ~100s |
| 100 件 cycle | **~630s 超时** | ~225s |
| 实际监控上限 | ~75 件 | ~200 件 |

## 新增

### 🔒 桌面端单实例守卫

[desktop_app.py](https://github.com/frozenjjzhc/sentinel-cs2/blob/main/desktop_app.py)：

- 启动时在 `%APPDATA%\Sentinel\desktop.lock` 拿 Windows 独占文件锁
- 第二次双击 `Sentinel-Desktop.bat` → 锁拿不到 → POST `/api/desktop/show` 通知第一个实例显示窗口 → 本进程退出
- POST 失败兜底：弹 Windows 消息框「Sentinel 已经在运行，请从托盘恢复」
- 进程崩溃时 OS 自动释放锁，不会留僵死锁文件挡死下次启动

**`Sentinel.bat` 浏览器模式不冲突**：浏览器模式不拿这个锁，desktop attach 模式（先开浏览器再开 desktop）行为保持不变。

### 新端点

- `POST /api/desktop/show` — 桌面模式专属，让窗口从托盘恢复并置前；返回 `{ok: true, desktop: true}`。Sentinel.bat 浏览器模式下此端点不存在。

## 升级方法

### v3.0.0 → v3.0.1

```powershell
cd D:\你的旧 sentinel 目录
Expand-Archive Sentinel-v3.0.1.zip -DestinationPath $env:TEMP\sentinel-v3.0.1 -Force
$src = "$env:TEMP\sentinel-v3.0.1\sentinel-cs2"
# 只覆盖 4 个改动文件，state 不动
Copy-Item "$src\desktop_app.py","$src\monitor_fast.py","$src\backend_api.py" . -Force
Copy-Item "$src\lib\scraper.py","$src\lib\config.py" .\lib\ -Force
Copy-Item "$src\frontend\package.json" .\frontend\ -Force
# 前端不需重新 build（package.json 只是版本号）
.\Sentinel-Desktop.bat
```

### git 用户

```bash
git pull origin main
git checkout v3.0.1
.\Sentinel-Desktop.bat
```

无新依赖，无 schema 变更，state 文件不动。

## 兼容性

- ✅ **100% 向后兼容**：动态 wait 失败有 fallback 回到原 6 秒死等，价格抓取逻辑零变化
- ✅ **Sentinel.bat 浏览器模式不受影响**：单实例锁仅 desktop_app 持有，浏览器模式可与 desktop attach 并存
- ✅ **数据完全不动**：state.json / Playwright profile 都沿用
- ⚠️ **图片首抓变慢一拍**：`block_images=True` 默认启用后，新加品种或重置 image_url 后第一轮 cycle 才能补齐图片（以前每轮都抓，现在只在需要时抓）

## 路线图

- [ ] PWA manifest + service worker（手机「添加到主屏」）
- [ ] iOS / Android 原生 app
- [ ] PyInstaller exe 二进制 release（让没有 Python 的朋友也能用）
- [ ] 暗色模式
- [ ] LLM 庄家公告自动解析（Phase 2）
- [ ] 监控并发：sync_playwright → async_playwright + page pool（如需冲 500+ 件）

---

完整变更日志：[CHANGELOG.md](https://github.com/frozenjjzhc/sentinel-cs2/blob/main/CHANGELOG.md)
