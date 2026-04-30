# v3.0.0 — React UI · 桌面应用 · 局域网访问 · per-strategy AI

## 重点

**这是 Sentinel 自 1.0 以来最大的一次跃迁**：dashboard 从单文件 HTML 升级到 React + Vite + TypeScript SPA；新增**原生桌面应用**（pywebview + 系统托盘）；**局域网访问**就绪——电脑跑后端、手机连同 WiFi 直接输 URL 即可使用所有功能；策略参数移到 state 后 AI 提案可针对**单个策略**精调，每位用户的 Sentinel 都将沿着自己的交易习惯演化成不同的样子。

## 新增

### 🪟 原生桌面应用
- 双击 `Sentinel-Desktop.bat` → 弹出原生窗口（pywebview + WebView2），无 cmd 黑窗
- **关闭窗口 = 最小化到托盘**，监控/调度/API 持续运行
- 系统托盘（任务栏右下角紫色盾牌图标）：单击恢复窗口、右键「退出 Sentinel」才真正终止
- attach 模式：先开 `Sentinel.bat`（浏览器模式）再开 desktop，会自动只附加窗口不重复启动 uvicorn

### 📱 手机直接访问
- 设置页 → **📱 局域网访问** 卡片 → 勾选「允许局域网访问」+ 重启 backend → backend 绑定 `0.0.0.0:8000`
- 勾选「内网设备免 token」（实时生效）→ **手机 Chrome 直接输 `http://192.168.x.x:8000` 即可使用所有 CRUD**
- 不开「内网信任」时仍可用扫 QR 模式：QR 码内容是 `http://IP:8000/?token=...`，扫码后 token 自动入库 localStorage
- 信任范围：RFC1918（192.168/10/172.16）+ CGNAT（100.64.0.0/10）+ 链路本地（169.254/16）+ IPv6 ULA（fc00::/7）
- 公网 IP 仍然要求 token（即使开了信任内网）

### ⚛️ React + Vite + TypeScript SPA
- 6 页 URL 路由化：`/` 概览 · `/charts` 走势图 · `/positions` 仓位管理 · `/strategy` 策略管控 · `/ai` AI 复盘 · `/settings` 设置
- 移动端响应式：Nav 在 < md 收为 hamburger 菜单；Hero 字号三档；Charts 支持触摸 hover
- 视觉资产完整保留：Liquid Glass 玻璃拟态、战术 UI 网格、3D AK-47 SVG（hover 浮动）、WebGL Doppler 着色器、磁吸按钮
- TanStack Query 缓存所有 API 调用，30s 自动刷新
- gzip 后约 110KB JS + 7KB CSS（远小于原 186KB 单文件 HTML）

### 🤖 AI 复盘 / 参数提案每日自动跑
- v2 时勾选「每日复盘评论」「参数调整提案」需要在 dashboard 手动点按钮才生效（实现疏漏，已修）
- v3 起 daily_review.py 每次 23:00 cycle 自动调：
  - `llm_analyst.daily_review_commentary` → 写入 `state.global.ai_review[]`
  - `llm_analyst.propose_parameter_changes` → 生成提案进 `state.global.parameter_proposals[]` 等待审批
- 新闻语义分类频率改为**每天**（`state.global.fundamentals.refresh_days = 1`，可改为任意天数）

### 🎯 per-strategy AI 调参
- `rsi-reversion-v1` / `mean-reversion-v1` / `grid-half-v1` 三套策略的 PARAMS 从模块常量搬到 `state.global.strategies[sid].params`
- AI 提案 schema 新增 `scope: "strategy"` + `strategy_id` 字段
- LLM prompt 列出每策略的可调字段、合理范围、调参逻辑（"win_rate < 40% → tighten" 等）
- 应用提案时 `apply_proposal` 三分支：global → `state.global[field]`，item → `item.thresholds[field]`，strategy → `state.global.strategies[sid].params[field]`，**全部自动备份原值**
- 切换 active 策略不会丢失之前 AI 调过的参数（按策略 id 隔离存储）

### 📈 主板块跟涨整合到 phase-sync
- 原 monitor_slow 每小时推送的「🔗 主板块跟涨机会」独立消息**已删除**（信号噪音大，干扰主决策）
- 改为 phase-sync 策略多因子加成：主板块强领涨（leader 1H RS ≥ 2）+ 本品种相对滞后（gap ≥ 2%）→ 原 BUY 信号 priority +0.5 + advice 末尾自动加 `[📈 板块「武库」领涨 +5.2% 跟涨候选]`
- signal dict 新增 `sector_boost` 字段，shadow 复盘可追踪

### 🆕 新板块「刀」「贴纸」
- 设置页 → 监控品种 → 板块下拉新增 2 项

### 🎨 视觉打磨
- Nav 左上角 logo：从单色方块换为**盾牌 + 渐变 + 准星 SVG**，hover 微旋转，Sentinel 文字渐变
- Hero「总仓位预算」卡片显示「已用 ¥X.Yk (NN%)」+ 颜色编码（80% 黄 / 100%+ 红）
- 设置页基本面「逐条分析」修复字段错位（兼容 `topic` / `title` / `summary`），加 type 中文翻译 + impact 缩写

### 🔒 写端点鉴权
- 新中间件 [`lan_auth_middleware`](backend_api.py)：POST/DELETE 来自非本机时强制 `X-Sentinel-Token` header
- 本机 127.0.0.1 / ::1 永远免 token（桌面/浏览器模式不受影响）
- LAN 信任模式下私网/CGNAT IP 也免 token

### 新端点
- `GET /api/global/lan` — 返回当前 LAN 配置 + 本机 IP 列表 + token + 端口
- `POST /api/global/lan` — 切换 enabled / trust_private（trust_private 实时生效，enabled 需重启 backend）
- `POST /api/global/lan/reset_token` — 重置 token（旧 token 立即失效）

## 升级方法

### v2.1+ → v3.0.0（最简单）

```powershell
cd D:\你的旧 sentinel 目录
# 解压新 zip 到临时目录
Expand-Archive Sentinel-v3.0.0.zip -DestinationPath $env:TEMP\sentinel-v3 -Force
$src = "$env:TEMP\sentinel-v3\sentinel-cs2"
# 覆盖代码（数据原封不动 — 已经在 %APPDATA%\Sentinel\）
Copy-Item "$src\*.py","$src\*.bat","$src\*.md","$src\requirements.txt","$src\state.example.json" . -Force
Copy-Item "$src\lib","$src\frontend" . -Recurse -Force
# 装新依赖（pywebview / pystray / Pillow / 前端 npm 包）
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
# 启动 — 任选一个
.\Sentinel.bat              # 浏览器模式（保留）
.\Sentinel-Desktop.bat      # 桌面应用模式（v3 新）
```

首启时 backend 会自愈写入新字段（`global.lan` / `global.strategies[*].params` / `global.fundamentals.refresh_days`）。

### git 用户

```bash
git pull origin main
git checkout v3.0.0
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
.\Sentinel-Desktop.bat
```

## 兼容性

- ✅ **100% 向后兼容**：state 自愈补全所有新字段；老 `Sentinel.bat` 依然工作；4 套策略 ID 与默认参数都不变
- ✅ **数据完全不动**：v2.1+ 的 `%APPDATA%\Sentinel\` 数据目录沿用；旧 `m4a4_buzz_kill_state.json` 全字段保留
- ✅ **active 策略保持**：升级前如果用的是 `phase-sync-v1`，升级后还是 `phase-sync-v1`
- ⚠️ **新依赖**：`pywebview / pystray / Pillow` 必须 pip install；如果不想装可以继续用 `Sentinel.bat` 浏览器模式（这条路径不依赖新包）
- ⚠️ **WebView2 Runtime**：桌面模式需要 Edge 内核运行时，Win10/11 通常预装；如果没有去 https://developer.microsoft.com/microsoft-edge/webview2/ 下载 Evergreen Standalone Installer
- ⚠️ **首次开 LAN 模式**：Windows 防火墙会弹询问，选「专用网络」即可

## 路线图

- [ ] PWA manifest + service worker（手机「添加到主屏」）
- [ ] iOS / Android 原生 app（PWA 跑通后再说）
- [ ] PyInstaller exe 二进制 release（让没有 Python 的朋友也能用）
- [ ] 暗色模式
- [ ] LLM 庄家公告自动解析（Phase 2）

---

完整变更日志：[CHANGELOG.md](https://github.com/frozenjjzhc/sentinel-cs2/blob/main/CHANGELOG.md)
