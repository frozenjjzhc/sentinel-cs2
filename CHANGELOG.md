# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 格式，
版本号采用 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

---

## [3.0.0] — 2026-04-29

### 重大变更
- **前端整体迁移**：单文件 `frontend/preview.html`（3900+ 行）拆解为 **React + Vite + TypeScript** SPA，6 页 URL 路由化（`/` `/charts` `/positions` `/strategy` `/ai` `/settings`），dist 产物由 backend `/assets/*` 静态挂载 + SPA fallback 路由统一服务。Liquid Glass、战术网格、3D AK-47 SVG、WebGL Doppler 着色器全部按组件保留。
- **桌面应用化**：新增 `desktop_app.py`（pywebview）+ `Sentinel-Desktop.bat` 静默启动；窗口集成 **pystray 系统托盘**，关闭窗口=最小化到托盘，监控/调度持续运行；右键托盘「退出 Sentinel」才真正终止全部进程。
- **局域网访问 + Token 鉴权**：新增 `state.global.lan = { host, enabled, trust_private }` + `lan_token`。设置页 → 「📱 局域网访问」一键切 0.0.0.0:8000，POST/DELETE 来自非本机时强制 `X-Sentinel-Token` header。新「内网信任」开关：私网/CGNAT/链路本地 IP 段（RFC1918 + 100.64.0.0/10 + 169.254/16）免 token，**手机直接输 LAN URL 即可使用所有 CRUD**。
- **策略参数搬到 state**：`rsi-reversion-v1` / `mean-reversion-v1` / `grid-half-v1` 三套策略的 PARAMS 从模块常量改为 `state.global.strategies[sid].params`，由 `lib/strategies/get_strategy_params(state, sid)` 合并默认值与覆盖；`lib/state.py` 自愈节点首启自动写入。
- **AI 提案支持 `scope=strategy`**：`llm_analyst.propose_parameter_changes` schema 加 `strategy_id` 字段，prompt 显式列出每策略可调参数与合理范围；`apply_proposal` 三分支（global / item / strategy），写入对应 path 并自动备份原值。
- **daily_review 自动跑 LLM**：`daily_review.py` 现在每次 23:00 cycle 都会自动调 `daily_review_commentary` + `propose_parameter_changes`（用户勾选启用模块后）。修复了之前必须在 dashboard 手动点按钮才会跑的实现疏漏。
- **新闻分类频率改为每天**：`fundamentals.refresh_days` 默认 1（v2 是隐式 7 天）；可在 state 中改为任意天数。

### 新增
- 🪟 **原生桌面应用**：`Sentinel-Desktop.bat` → `pythonw desktop_app.py` 无 cmd 窗口启动；attach 模式（已有 backend 时只开窗口不重复启动 uvicorn）。
- 📱 **手机访问就绪**：设置页 LanAccessSection 显示本机所有 LAN IP 列表 + QR 码（token 模式 / 信任模式自动切换 QR 内容）；前端 `?token=...` query 自动入库 localStorage。
- 🎨 **Nav 新 logo**：盾牌轮廓 + 渐变填充 + 中心十字准星 SVG，呼应 Hero 区 AK-47 主题；hover 微旋转 + 阴影；Sentinel 文字渐变。
- 📊 **Hero 总仓位预算「已用」展示**：实时计算 `已用 ¥X.Yk (NN%)`，颜色编码（80% 黄 / 100%+ 红）。
- 📈 **板块联动 sector_boost**：原 monitor_slow「主板块跟涨」独立推送已删除（噪音过大），改为 phase-sync 策略多因子加成 — 主板块强领涨（leader RS ≥ 2）+ 本品种滞后（gap ≥ 2%）→ BUY 信号 priority +0.5 + advice 末尾追加 `[📈 板块「X」领涨 +N% 跟涨候选]`，写入 `signal.sector_boost` 字段供 shadow 复盘追踪。
- 🆕 **板块下拉新增**：`刀` / `贴纸`（原有 6 项加这 2 项共 8 项）。
- 📱 **响应式补齐**：Nav `<md` 收 hamburger（用 `<details>` 免依赖）；Charts 加 `onTouchStart/Move/End` 触摸 hover；Hero 字号三档 `text-5xl sm:text-6xl md:text-7xl lg:text-[88px]`；AK SVG `<sm` 隐藏；Settings 输入框去掉硬 `min-w` 改为 `w-full md:min-w-`。
- 🔧 **新端点**：`GET/POST /api/global/lan`、`POST /api/global/lan/reset_token`。
- 🔧 **TanStack Query** 缓存所有 API 调用，30s 自动刷新；`@tanstack/react-query` + `react-router-dom` + `qrcode` 加入前端依赖。
- 🔧 **`captureTokenFromQuery()`**：手机扫 QR 后 URL `?token=...` 自动写入 localStorage 并清掉 query。

### 修复
- **基本面「逐条分析」字段错位**：原 `recent_updates` 用 `topic` 字段而前端读 `title`，导致条目标题全显示 `—`。前端 fallback `u.title || u.topic || u.summary`，附带 `type` 翻译（whale → 庄家 / minor → 小更新 / tech → 技术 / season → 赛季）+ `impact` 缩写（`strong_positive_short_term` → `强positive·短期`）。
- **CSS 层级冲突**：自定义 CSS 中 `.tactical-grid > * { position: relative }` 覆盖了 Tailwind `.absolute` 工具类，导致 Hero 内 Doppler canvas / AK SVG / 玻璃卡片被压成 flex 行。修复：把所有自定义 CSS 包进 `@layer components`，让 utilities 层源序后置自然胜出。
- **饰品图 403 Forbidden**：`img.zbt.com` 检查 Referer，从 `127.0.0.1:8000` 发起的请求被拒。所有 `<img>` 加 `referrerPolicy="no-referrer"` 让浏览器不发 Referer header。

### 升级须知
- 从 v2.1+ 升级到 v3.0：直接覆盖代码即可，state 自愈会补全 `lan / strategies / fundamentals.refresh_days` 三个新节点。
- 第一次启动 `Sentinel-Desktop.bat` 需要 **WebView2 Runtime**（Win10/11 通常已预装）和已装 `pip install -r requirements.txt`（含 pywebview / pystray / Pillow）。
- 想用手机访问：设置页「📱 局域网访问」勾选①「允许局域网访问」+ 重启 backend；勾选②「内网设备免 token」无需重启实时生效。Windows 防火墙首次会询问，选「专用网络」。
- 切换 active 策略不会丢失 AI 调过的参数：每个策略的 params 独立存在 `state.global.strategies[sid].params`，切回来原样恢复。

### 删除
- `frontend/preview.html` 单文件 dashboard（备份保留为 `frontend/preview.legacy.html.bak`，已 gitignore）。
- monitor_slow 的「主板块跟涨机会」独立 PushPlus 推送（噪音过大；信号已重构为 phase-sync 内联加成）。

---

## [2.1.0] — 2026-04-28

### 新增
- **跨版本数据持久化**：用户数据（`state.json` / shadow / `.playwright_profile/` / `screenshots/` / `logs/` / `m4a4_errors.log`）默认保存到 **`%APPDATA%\Sentinel\`**，跨版本升级 0 迁移成本。
- **首次启动自动迁移**：v1.x / v2.0.x 用户首次跑 v2.1+，会自动把安装目录里的老数据复制到 `%APPDATA%\Sentinel\`，旧文件保留作备份。
- **`SENTINEL_DATA_DIR` 环境变量**：高级用户可自定义数据目录（用于多实例隔离 / 测试环境隔离）。
- **设置页 → 数据目录卡片**：显示当前路径来源，提供「📂 打开数据目录」+「📋 复制路径」按钮。
- 新端点：`GET /api/global/data_dir`（返回路径详情）、`POST /api/global/open_data_dir`（在资源管理器打开）。

### 升级须知
- 从 v1.x / v2.0.x 升级到 v2.1+：直接覆盖代码即可，无需手动迁移 state.json。第一次启动时控制台会打印迁移日志。
- 旧安装目录里的 state.json 等文件**不会被删除**，作为备份保留。确认 v2.1 跑稳之后可以手动清理。
- 重装 Windows 时，`%APPDATA%\Sentinel\` 会跟随系统备份 / OneDrive 同步还原。
- 想换回旧行为（数据放安装目录）：设置 `SENTINEL_DATA_DIR=<安装目录>` 环境变量即可。

### 路径示意
```
旧（v2.0.x 及之前）：
  D:\sentinel-cs2\                       ← 代码 + 数据全在一起
    ├── m4a4_buzz_kill_state.json        ← 数据
    ├── *.py / *.bat                      ← 代码
    └── ...

新（v2.1+）：
  D:\sentinel-cs2\                       ← 仅代码（每次升级整体覆盖）
    ├── *.py / *.bat / lib/ / frontend/
    └── ...
  C:\Users\<你>\AppData\Roaming\Sentinel\ ← 仅数据（跨版本永驻）
    ├── m4a4_buzz_kill_state.json
    ├── shadow_signals.json
    ├── .playwright_profile/
    ├── screenshots/ / logs/
    └── ...
```

---

## [2.0.0] — 2026-04-28

### 重大变更
- **多策略架构**：从单策略升级为 4 策略并行 — `phase-sync-v1`（趋势同步）/
  `rsi-reversion-v1`（RSI 反转）/ `mean-reversion-v1`（均值回归）/
  `grid-half-v1`（半网格）。Active 策略实际推送，其他 shadow 跟跑做对比回测。
- **state schema v3 → v4**：新增 `qty_pieces`、`planned_total_cny`、
  `active_strategy`、`strategies` 注册表、`grid_state`、`ignore_whale_signals`、
  `image_url` 等字段。首次启动自动迁移老 state。
- **视觉品牌重塑**：苹果式 Liquid Glass、战术 UI 网格、3D AK-47 SVG、
  WebGL Doppler 着色器，整套首页视觉重做。

### 新增
- 策略管控页：tab 选择 + 单策略详情面板 + 实时 shadow 对比 + 淡入淡出动画
- 真实 Steam 饰品图：自动从 SteamDT 抓取 `img.zbt.com` 主图，
  概览卡和设置页饰品列表都显示
- 总预算（`planned_total_cny`）→ 仓位百分比、可用余额计算
- `qty_pieces`：精确成本计算（修复了把 `qty_pct` 当数量的 bug）
- 大庄家信号开关：设置页一键忽略 BUY-WHALE
- 网格策略 T+7 锁感知 + 阶梯式分批
- 嵌入式调度器：monitor 与 API 同进程，`Sentinel.bat` 一键启动
- AI 复盘页（Phase 1/3/4）：新闻分类 + 每日复盘 + 参数提案
- K 线时间轴改为时间戳定位（不再按索引）+ 鼠标悬停 tooltip
- 增量成交量计算（自动处理跨日重置）
- `POST /api/items/{id}/image` 端点：手动覆盖饰品图
- `POST /api/global/budget`、`POST /api/global/whale_toggle`、
  `POST /api/strategies/active`、`POST /api/grid/toggle`、
  `POST /api/grid/{id}/restart` 等端点

### 修复
- 概览页"监控品种"数字反映真实饰品数（不再硬编码 4）
- `BudgetRequest` NameError（Pydantic 模型定义顺序）
- Steam News 抓取增加 3 次指数退避重试（2s/4s/6s），错误透传到 UI

### 升级须知
- 第一次启动会**自动迁移** `m4a4_buzz_kill_state.json`（v3 → v4）。
  建议升级前手动备份一份。
- 已存在的 `image_url` 字段不会被自动覆盖；可在设置页"换图"手动覆盖。
- 已开通 PushPlus / LLM 的密钥设置无需变更。

---

## [1.2.1] — 2026-04-27

### 修复
- 在使用 `BudgetRequest` 之前先定义所有 Pydantic 请求模型（严格 Python
  环境下出现的 NameError）

---

## [1.2.0] — 2026-04-27

### 新增
- 总预算驱动的仓位计算
- K 线时间精确化（时间戳定位）
- 网络抗性：Steam News 三重重试、错误透传

### 修复
- `qty_pieces` 字段加入仓位 schema，修正成本计算
- Steam News 抓取超时改 30s

---

## [1.0.5] — 2026-04-27

### 新增
- `setup.bat` 优先使用系统 Chrome（避免在国内下载 150MB Chromium）
- npmmirror.com 镜像作为 Chromium 下载备选

### 修复
- `setup.bat` 重写为纯 ASCII，规避 Windows 中文 codepage 乱码
- 加 `chcp 65001` 防止中文编码乱码

---

## [1.0.0] — 2026-04-26

- 首次公开发布
- 4 饰品监控、5 BUY × 4 SELL 信号、PushPlus 推送
- K 线截图归档、影子仓位回测、bias 调节器
- 可选 LLM 接入（Anthropic / OpenAI / DeepSeek）

[2.1.0]: https://github.com/frozenjjzhc/sentinel-cs2/releases/tag/v2.1.0
[2.0.0]: https://github.com/frozenjjzhc/sentinel-cs2/releases/tag/v2.0.0
[1.2.1]: https://github.com/frozenjjzhc/sentinel-cs2/releases/tag/v1.2.1
[1.2.0]: https://github.com/frozenjjzhc/sentinel-cs2/releases/tag/v1.2.0
[1.0.5]: https://github.com/frozenjjzhc/sentinel-cs2/releases/tag/v1.0.5
[1.0.0]: https://github.com/frozenjjzhc/sentinel-cs2/releases/tag/v1.0.0
