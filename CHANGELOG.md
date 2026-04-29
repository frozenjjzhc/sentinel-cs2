# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 格式，
版本号采用 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

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
