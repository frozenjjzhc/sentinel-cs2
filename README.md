# Sentinel · CS2 饰品智能监控系统

[![Release](https://img.shields.io/github/v/release/frozenjjzhc/sentinel-cs2)](https://github.com/frozenjjzhc/sentinel-cs2/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)]()

> ## 别的工具帮你找便宜货，Sentinel 帮你做决定
>
> **不是清单生成器，是深度跟踪器**。市面上的 CS2 工具大多解决"今天哪些饰品在异动"的**发现问题**；Sentinel 专攻另一边——**当你已经选定 4–20 件想长期跟踪的饰品，每个时点该不该加仓 / 该不该止盈 / 庄家阶段对不对**。
>
> 在自选池里做到的深度，是清单工具放不进去的：
>
> 🎯 **4 策略并跑 + shadow 横评** — 趋势同步 / RSI 反转 / 均值回归 / 半网格，active 推送，其他跟跑做实时胜率对比
> 🌊 **6 庄家阶段识别** — 吸筹 / 洗盘 / 蓄力 / 拉升 / 派发 / 下跌，决定哪些信号生效
> 🧠 **LLM bias 调节器** — Steam News 语义分类 → 实时调 BUY 优先级 + 止损/止盈乘数（每条推送带 `[bias=negative ×0.7]` 标签，复盘可追溯）
> ⏳ **T+7 锁感知 + 套牢仓 LEGACY_ALERT** — CS2 原生时间语义，不是从股票工具硬搬
> 🧾 **AI 参数提案需人工审批 + 自动备份原值** — LLM 不直接改阈值，写提案给你点 ✓/✗，应用前自动 backup 可回滚
>
> 100% 本地 · 规则引擎 + 可选 LLM 语义层 · 苹果式 6 页 SPA。

## 给会自己调参的交易者

Sentinel 不做「人人同款」的推荐。它是一台 **开放的可调决策仪**——所有阈值、策略权重、bias 调节器、止损/止盈乘数都摊在 dashboard 上让你直接改；4 套策略并跑、shadow 模式给你真实的胜率与回报反馈；LLM 提议的参数变动先经过你审批才会落地。

一个事实：每位优秀交易员都有自己的边界、节奏与风险偏好——平均化的推荐器永远拟合不了。Sentinel 把你的判断与习惯沉淀进系统：监控哪些品种、接受还是拒绝哪条 AI 调参、信任还是屏蔽哪类庄家信号，每一次选择都会让它更贴近你。**一年之后，你的 Sentinel 一定和别人的不一样**。

如果你只想被告知「现在该抄哪个」，市面上有更轻的工具；如果你愿意把策略迭代成自己的——规则引擎、shadow 数据、4 路并跑对比、LLM 提案审批墙，全部为你打开。

> ⚠️ **免责声明**：本工具仅用于个人学习与价格监控，不构成任何投资建议。CS2 饰品交易具有风险，使用者自担一切责任。本项目与 Valve、Steam、SteamDT 等任何第三方公司**无关联**。

---

## ✨ 最新版本重点

### v3.0.0（2026-04 发布）— React UI · 桌面应用 · 局域网访问 · per-strategy AI
| 维度 | 变化 |
|---|---|
| ⚛️ **React 重写** | 单文件 dashboard → **React + Vite + TypeScript SPA**，6 页路由化、移动端响应式 |
| 🪟 **桌面应用** | `Sentinel-Desktop.bat` 启动 **pywebview 原生窗口 + 系统托盘**，关窗口最小化、监控持续运行 |
| 📱 **局域网访问** | 设置页一键开启 LAN 模式 + token 鉴权 + 「内网信任」开关，**手机直接输 URL 即可 CRUD** |
| 🤖 **AI 自动化** | 每天 23:00 daily_review 自动跑 LLM **复盘 + 参数提案**；新闻分类频率改为**每天** |
| 🎯 **per-strategy AI** | RSI / MR / Grid 三策略的 PARAMS 搬到 state，AI 提案 `scope=strategy` 可针对**单策略**优化 |
| 📈 **板块联动** | 主板块跟涨从「单独推送」改为「分阶共振多因子加成」（priority +0.5 + advice 标签） |
| 🆕 **新板块** | 「刀」「贴纸」加入板块下拉 |

### v2.1.0（2026-04 发布）— 跨版本数据持久化
| 维度 | 变化 |
|---|---|
| 📁 **数据目录搬家** | 用户数据默认搬到 **`%APPDATA%\Sentinel\`**（`C:\Users\<你>\AppData\Roaming\Sentinel\`），跨版本升级 **0 迁移成本** |
| 🔄 **首次启动自动迁移** | v1.x / v2.0.x 老用户首次跑 v2.1+ 时自动复制老数据，旧文件保留作备份 |
| 🛠️ **环境变量支持** | `SENTINEL_DATA_DIR` 自定义路径，支持多实例隔离 / 测试隔离 |
| 🪟 **设置页可视化** | 「📁 数据目录」卡片：显示路径 + 来源，一键「📂 打开」/「📋 复制」 |

> **从此朋友升级新版本只要覆盖代码，数据永远在那一个固定位置。再也不用手动复制 state.json 了。**

### v2.0.0（2026-04 发布）— 多策略 + 视觉品牌重塑
| 维度 | 变化 |
|---|---|
| 🧠 **多策略架构** | 单策略 → **4 套并行**（趋势同步 / RSI 反转 / 均值回归 / 半网格），active 推送，其他 shadow 跟跑做实时对比 |
| 🎨 **视觉品牌重塑** | 苹果式 Liquid Glass · 战术 UI 网格 · 3D AK-47 SVG · WebGL Doppler 着色器 |
| 🖼️ **真实饰品图** | 自动从 SteamDT 抓取 Steam CDN 主图，概览卡 + 设置页都显示，可手动换图 |
| 💰 **总预算驱动** | `planned_total_cny` → 仓位百分比、可用余额、集中度警告 |
| 🔢 **数量精确** | 新 `qty_pieces` 字段，修复了把仓位百分比当数量的成本计算 bug |
| 🕸️ **半网格策略** | T+7 锁感知 + 阶梯式分批 + 紧急 z-score 退出 |
| 🐋 **Whale 开关** | 设置页一键忽略 BUY-WHALE 信号 |

完整变更日志见 [CHANGELOG.md](CHANGELOG.md)。

---

## 一、项目能做什么

**自动监控 4+ 个 CS2 饰品**（可任意扩展），**每 10 分钟**采集一次价格 / 量能 / 大盘 / 持仓数据，**4 套策略并行评估买卖信号**（趋势同步 / RSI 反转 / 均值回归 / 半网格），**触发即推送**到 PushPlus 微信（最多 3 个接收人），并保存完整的：

- ✅ 实时价格历史（90 天滚动）
- ✅ **多策略并行**：active 策略实际推送，其他 shadow 跟跑做实时对比回测
- ✅ 信号触发日志（每次扫描必写，带 bias 应用记录）
- ✅ 推送记录（用于复盘）
- ✅ 影子仓位回测（每个 BUY 信号自动跟踪 7 日收益，按策略分组）
- ✅ 总仓位风险面板（**总预算驱动**，成本/市值/集中度/警告 + `qty_pieces` 精确数量）
- ✅ 庄家阶段切换记录
- ✅ 跨品种相对强度（RS）+ 板块联动分析
- ✅ 每日 23:00 自动复盘报告（推微信 + 写 state）
- ✅ K 线截图归档（30 天滚动）
- ✅ Steam News 自动监控（关键词 + LLM 语义双轨）
- ✅ 应急熔断机制（大盘崩盘时自动停推 BUY）
- ✅ **bias 调节器**：基本面偏置 → 自动调整 BUY 优先级 + 止损/止盈阈值
- ✅ **可选 LLM 接入**：Anthropic / OpenAI / DeepSeek / 任意 OpenAI 兼容协议

**配套前端**（Sentinel UI）：苹果式极简多页 SPA，**6 个功能页**，**直接连接后端做增删改**：
- **概览**：Liquid Glass 卡片 / 3D AK-47 SVG / WebGL Doppler 着色器 / 战术 UI 网格 / 真实 Steam 饰品图
- **走势图**：折线 / K 线切换 + 24H/3D/7D 范围 + 时间戳定位 + 鼠标悬停 tooltip + 增量成交量
- **仓位管理**：每个品种内嵌操作栏（加仓 / 卖出 / 设套牢仓 / 清空），按总预算计算占比，直接写后端
- **策略管控**：tab 切换 4 套策略 + 单策略详情面板 + 实时 shadow 对比 + 网格独立控制
- **AI 复盘**：Shadow 模拟收益统计（按策略分组）+ AI 每日评论 + 参数调整提案审批
- **设置**：PushPlus token 增删 / 监控品种增删（含板块下拉 + 换图）/ 总预算 / Whale 开关 / LLM 配置 / 监控心跳

---

## 二、系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                          数据源                                   │
│   • SteamDT 商品页（playwright 爬取）                              │
│   • Steam News API（fundamentals 自动更新）                        │
│   • LLM API（可选：新闻语义 / 复盘 / 参数提案）                     │
│   • Web 仪表板（增删品种/仓位/token、录入庄家信号）                 │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              Layer 1 ─ 热路径：规则引擎（每 10min/1H）             │
│                                                                  │
│   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐     │
│   │ monitor_fast.py│  │ monitor_slow.py│  │daily_review.py │     │
│   │   每 10 min    │  │  每 1 小时      │  │  每天 23:00    │     │
│   │   BUY 信号     │  │ SELL + TP止盈  │  │ 汇总 + 截图   │     │
│   │ (4 策略并跑)   │  │ (bias调阈值)   │  │ + AI 评论(可选)│     │
│   └────────────────┘  └────────────────┘  └────────────────┘     │
│                                                                  │
│   ★ lib/strategies/ ─ v2.0.0 多策略注册表                         │
│     phase-sync-v1 / rsi-reversion-v1 / mean-reversion-v1 /       │
│     grid-half-v1   ← active 推送，其他 shadow 跟跑                │
│                                                                  │
│   lib/ 模块：scraper · indicators · stages · signals · pusher     │
│            state · circuit_breaker · shadow · correlation        │
│            portfolio · screenshots · news_monitor · telegram     │
│            ★ llm_provider · llm_analyst                          │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              Layer 2 ─ 暖路径：LLM 语义层（可选）                  │
│                                                                  │
│   Phase 1 ✅ 新闻语义分类（替代关键词）→ fundamentals.bias        │
│   Phase 2 □ 庄家公告解析（粘贴中文 → 结构化）（待开放）           │
│   Phase 3 ✅ 每日复盘评论 → ai_review[]                          │
│   Phase 4 ✅ 参数调整提案 → parameter_proposals[] (需审批)        │
│                                                                  │
│   provider 可切换：Anthropic / OpenAI / DeepSeek / 自托管         │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              数据持久层（v2.1+：%APPDATA%\Sentinel\）              │
│   ├── m4a4_buzz_kill_state.json   实时状态 + LLM配置 + AI评论    │
│   ├── shadow_signals.json         影子回测                       │
│   ├── screenshots/YYYY-MM-DD/     K 线归档                       │
│   ├── logs/                       运行日志                       │
│   └── m4a4_errors.log             错误累积                       │
└─────────────────────────────┬────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
       ┌──────────┐                    ┌──────────┐
       │ PushPlus │                    │ FastAPI  │
       │  微信推送 │                    │  :8000   │
       └──────────┘                    └────┬─────┘
                                            │
                          ┌─────────────────┴─────────────────┐
                          ▼                                   ▼
                  ┌──────────────────┐              ┌──────────────────┐
                  │  Sentinel-Desktop │              │  浏览器/手机 LAN  │
                  │ pywebview 原生窗  │              │ http://<IP>:8000 │
                  │ + 系统托盘 (v3+)  │              │  (内网信任 / QR)  │
                  └────────┬─────────┘              └────────┬─────────┘
                           └────────────┬────────────────────┘
                                        ▼
                          ┌──────────────────────────┐
                          │  Sentinel UI (React,6 页)│
                          │  概览 / 走势图 /         │
                          │  仓位管理 / 策略管控 /   │
                          │  AI 复盘 / 设置          │
                          └──────────────────────────┘
```

### 决策闭环（bias 调节器）

```
LLM 分类 Steam News  ──→  fundamentals.bias
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
       BUY 信号 priority                SELL 阈值缩放
       (A 调节器 +1/-1/屏蔽)            (B 调节器 ×0.5~×1.3)
              │                               │
              └─────────────┬─────────────────┘
                            ▼
                    pusher 选最高 priority
                            ▼
                    微信 / dashboard
```

---

## 三、环境要求

| 项 | 要求 |
|---|---|
| 操作系统 | Windows 10 / 11 |
| Python | 3.9+（已加入 PATH）|
| 浏览器 | Chrome / Edge（用于 playwright headless 抓取 + 看 dashboard）|
| 磁盘 | ≥ 200 MB（chromium 占大头）|
| 网络 | 能访问 steamdt.com、pushplus.plus、api.steampowered.com |

可选：
- **Node 18+** + **npm 9+**（构建 React 前端，git 用户必须；下载发布版 zip 已带 dist 可跳过）
- **Microsoft Edge WebView2 Runtime**（用 `Sentinel-Desktop.bat` 桌面模式时需要；Win10/11 通常预装）
- **LLM API key** 任意一种（启用 Phase 1/3/4 智能模块）：
  - DeepSeek（`deepseek-chat`，性价比最高，国内可直连）
  - OpenAI（`gpt-4o-mini` 等）
  - Anthropic（`claude-sonnet-4-6` 等）
  - 其他 OpenAI 兼容协议（Qwen / Moonshot / 自托管 vLLM）

---

## 四、首次部署（一次性，约 5 分钟）

### 4.1 安装依赖

```powershell
cd <你解压 / 克隆的 sentinel-cs2 目录>
.\setup.bat
```

`setup.bat` 会自动：
1. 检查 Python 3.9+
2. `pip install -r requirements.txt`（含 playwright / fastapi / uvicorn / pywebview / pystray / Pillow）
3. `playwright install chrome`（首次约 5 分钟，优先复用系统 Chrome 避免下载 Chromium）

**v3.0+ 新增前端构建**（git 拉取 / 源码安装时必须）：
```powershell
cd frontend
npm install
npm run build
cd ..
```
（如果你下载的是 GitHub Release 的 zip，作者已附带构建产物，可跳过此步）

### 4.2 启动（**任选一种**）

**🥇 推荐：双击 `Sentinel-Desktop.bat`** — v3 桌面应用模式
- 弹出原生窗口（pywebview + WebView2，无 cmd 黑窗）
- 系统托盘紫色盾牌图标，**关闭窗口最小化到托盘，监控持续运行**
- 右键托盘 → 「退出 Sentinel」才真正终止

**🥈 替代：双击 `Sentinel.bat`** — 浏览器模式（v2 起一直支持）
- API 服务在 8000 端口启动 + 嵌入式调度器开跑
- 4 秒后浏览器自动打开 `http://localhost:8000`
- 关闭那个 cmd 窗口 = 全部停止

无论哪种模式，**嵌入式调度器**都会自动跑：每 10min fast / 每 1H slow / 每天 23:00 review。

### 4.3 配置 PushPlus（可选，没填也能用）

进 dashboard → 设置页 → PushPlus 卡片 → 「➕ 新增 token」表单：填名字 + 32 位 token → 添加。

token 从 https://www.pushplus.plus 微信扫码登录后获取。

### 4.4 监控调度器有两种模式

进 dashboard → 设置页 → 「⚙️ 监控调度器」卡片，可切换：

**🥇 嵌入式（默认推荐，零配置）**
- 监控随 API 一起跑，开 API 即工作
- 关 API 即停监控
- 适合：日常使用 / 想推广给非技术朋友 / 不想常驻后台进程

**🥈 Windows 任务计划器（独立后台）**
- 监控由系统级任务调度，关 API 也持续跑
- 需要先在 PowerShell 里建任务（见 4.5）
- 适合：想 7×24 不间断运行的高级用户

### 4.5 进阶：用 Windows 任务计划器（可选）

如果你切到 **Windows 任务计划器** 模式，需要 **管理员 PowerShell** 一次性建任务（注意把 `<INSTALL_DIR>` 替换为你的实际路径）：

```powershell
$base = "C:\path\to\sentinel-cs2"   # ← 改成你的安装目录
schtasks /Create /TN "CS2 Monitor Fast" /TR "$base\run_monitor_fast.bat" /SC MINUTE /MO 10 /RL HIGHEST /F
schtasks /Create /TN "CS2 Monitor Slow" /TR "$base\run_monitor_slow.bat" /SC HOURLY /MO 1 /ST 00:05 /RL HIGHEST /F
schtasks /Create /TN "CS2 Daily Review" /TR "$base\run_daily_review.bat" /SC DAILY /ST 23:00 /RL HIGHEST /F
```

暂停/恢复：
```powershell
# 暂停所有
"CS2 Monitor Fast","CS2 Monitor Slow","CS2 Daily Review" | ForEach-Object {
    schtasks /Change /TN $_ /DISABLE
}
# 恢复所有
"CS2 Monitor Fast","CS2 Monitor Slow","CS2 Daily Review" | ForEach-Object {
    schtasks /Change /TN $_ /ENABLE
}
```

### 4.6 升级到新版本（v2.1+ 起 0 迁移成本）

从 **v2.1.0** 开始，用户数据搬到了 `%APPDATA%\Sentinel\`，跟代码完全分离 — **每次升级新版本只要覆盖代码，数据原封不动**。

**v2.1+ → v3.x**（含 React 前端 + 桌面壳，需要重装依赖）：
```powershell
# 解压新 zip / git pull 之后
cd <安装目录>
pip install -r requirements.txt        # 装 pywebview / pystray / Pillow
cd frontend && npm install && npm run build && cd ..
.\Sentinel-Desktop.bat                 # 或 .\Sentinel.bat
```

**v3.x 之间互升**（v3.0 → v3.1 / v4 / …）：
```powershell
# 解压新 zip 到任意位置 → 装新依赖（如有）→ 重新 npm run build → 启动
```

**从 v1.x / v2.0.x 升到 v3.0+**（有数据要迁移）：
```powershell
cd <你的旧 sentinel 目录>
# 解压新 zip 到临时目录
Expand-Archive Sentinel-v3.0.0.zip -DestinationPath $env:TEMP\sentinel-v3 -Force
$src = "$env:TEMP\sentinel-v3\sentinel-cs2"
# 只覆盖代码（数据原封不动，首次启动会自动迁移到 %APPDATA%\Sentinel\）
Copy-Item "$src\*.py","$src\*.bat","$src\*.md","$src\requirements.txt","$src\state.example.json" . -Force
Copy-Item "$src\lib","$src\frontend" . -Recurse -Force
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
.\Sentinel-Desktop.bat
```

**git 用户**：
```bash
git pull origin main
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
.\Sentinel-Desktop.bat
```

---

## 五、日常使用

### 5.1 启动并访问 Dashboard

**🥇 推荐：双击 `Sentinel-Desktop.bat`** — 桌面应用模式
- 弹出原生窗口（pywebview）+ 系统托盘紫色盾牌图标
- 关闭窗口最小化到托盘，监控持续运行；右键托盘 → 「退出 Sentinel」才真正退出

**🥈 替代：双击 `Sentinel.bat`** — 浏览器模式
- 启动 API + 嵌入式调度器，4 秒后浏览器自动打开 `http://localhost:8000`
- 关 cmd 窗口 = 全部停止

**dashboard 内容**：
- 顶部 nav 状态 pill 显示心跳：`🟢 监控运行中 · X 分钟前更新`
- **6 个功能页**：概览 / 走势图 / 仓位管理 / 策略管控 / AI 复盘 / 设置
- 数据每 30 秒自动刷新

### 5.1+ 手机访问（v3.0+）

进 **设置页 → 「📱 局域网访问」** 卡片：
1. 勾选「① 允许局域网访问」 → 重启 backend（关桌面应用窗口或托盘退出再开）
2. 可选勾选「② 内网设备免 token」 → 同 WiFi 下手机 Chrome **直接输 LAN URL** 即可使用所有 CRUD（无需扫码）
3. 不勾② 时手机扫卡片里的 **QR 码**，token 自动入库 localStorage
4. Windows 防火墙首次会询问，选「专用网络」

> **想 7×24 后台跑**？切到「Windows 任务计划器」模式（设置页 → 监控调度器卡片），监控独立运行，关 dashboard 也持续。详见 4.5。

### 5.2 报告建仓 / 加仓 / 平仓

#### 方式 A：Web 仪表板（推荐）

进 **仓位管理** 页 → 找到对应品种卡片 → 操作行选择 + 输入参数 + 点「执行」：

| 操作 | 价格输入 | 数量输入 |
|---|---|---|
| 加仓 | 单价 | 把数（`qty_pieces`，可小数）|
| 卖出 | 卖出单价 | 卖出把数 |
| 设套牢仓 | 均价 | 数量（把） |
| 移除套牢仓 | — | — |
| 清空新仓 | — | — |

后端会原子写 `position.tiers`，A 类止损自动激活。每次操作还会写一条 `recommendations_log`。占总仓位 % 由系统按总预算自动计算。

#### 方式 B：直接改 state.json
打开 `%APPDATA%\Sentinel\m4a4_buzz_kill_state.json`，编辑 `items[].position.tiers` 数组。**不推荐**，容易写错；用 dashboard 更安全。

### 5.3 加新监控品种

#### 方式 A：Web 仪表板（最快，无需重启）

进 **设置** 页 → 「🎯 监控品种」卡片 → 「➕ 新增监控品种」表单：
- URL（必填，校验是 SteamDT 域名）
- 完整名称 + 短名
- **板块下拉**（v3.0 共 8 项）：一代手套 / 二代手套 / 三代手套 / 武库 / 千百战 / 收藏品 / 刀 / 贴纸
- 关键位（折叠区，建议填以激活信号判定）
- 点「添加品种」→ 下次 fast 任务自动开始抓取

#### 方式 B：命令行向导

```powershell
python add_item.py
```

向导版本字段更全（含阶段标签 / 自定义阈值），推荐复杂品种用这个。

### 5.4 增删 PushPlus token

进 **设置** 页 → 「📱 PushPlus 微信推送」卡片：
- 现有 token 旁边有「删除」按钮
- 下方「➕ 新增 token」表单：填名字 + 32 位 token → 点添加

### 5.5 录入庄家信号

目前需要直接编辑 state.json（位于 `%APPDATA%\Sentinel\m4a4_buzz_kill_state.json`）的 `global.fundamentals.whale_signals[]` 数组：

```json
{
  "id": "uniqueid_yyyymmdd",
  "type": "buy_in_commitment",
  "issued_at": "2026-04-29T15:40:00+08:00",
  "expires_at": "2026-05-29T15:40:00+08:00",
  "applicable_items": ["m4a4-buzz-kill-fn"],
  "buy_in_price": 4250,
  "stop_price": 4150,
  "rationale": "庄家公告原文摘要..."
}
```

> **Phase 2 LLM 庄家公告自动解析正在路上** — 届时可以直接在网页粘贴公告原文，由 LLM 抽出 buy_in_price / stop_price / 适用品种结构化字段。

### 5.6 看复盘 / Shadow 收益 / AI 评论

进 **AI 复盘** 页一站式查看：

**📈 Shadow 影子信号回测**
- 顶部四数：已评估笔数 / 待评估（< 7 天）/ 综合平均收益 / 信号种类
- 表格：每类信号的胜率 / 平均收益 / 最大 / 最小
- 最近 10 笔已评估明细（入价/出价/收益）

**📝 AI 每日复盘评论**
- 折叠列表，最新一份默认展开
- 「立即生成一份」按钮可手动触发（需 LLM 配置 + 启用）
- 每晚 23:00 自动跑（需勾选「每日复盘评论」模块）

**⚙️ 参数调整提案**
- AI 看 shadow 30 天数据 → 输出待审批提案
- 每条卡片：字段 / 原值→新值 / 方向 / 置信度 / 理由
- 你点 ✓ 应用 / ✗ 拒绝。应用前自动备份 `original_value`，可回滚

### 5.7 配置 LLM 接入（可选）

进 **设置** 页 → 「🤖 大模型接入」卡片：

| 字段 | 例 |
|---|---|
| Provider | Anthropic / OpenAI / 自定义（DeepSeek / Qwen / Moonshot 等 OpenAI 兼容） |
| Model | `deepseek-chat` / `gpt-4o-mini` / `claude-sonnet-4-6` |
| API Key | `sk-...`（明文存 state.json，仅本地，不会上传任何云端）|
| Base URL | 留空用默认；DeepSeek 填 `https://api.deepseek.com` |

启用模块（独立开关）：
- ☑ 新闻语义分类（替代关键词）
- ☐ 庄家公告解析（Phase 2 待开放）
- ☑ 每日复盘评论（写入 ai_review）
- ☑ 参数调整提案（需 shadow ≥5 条样本）

工作流：填好 → **保存配置** → **测试连通**（应回 `✓ 连通 XXms · "OK"`）→ 勾选模块 → 再次保存 → 立即触发或等定时任务。

> ⚠️ API key 明文存于 `m4a4_buzz_kill_state.json`，不要把该文件上传到代码仓库。

---

## 六、多策略架构

v2.0.0 把单策略升级为 **4 套策略并行**：active 策略实际推送，其他 shadow 跟跑做实时对比回测。每个策略 ID 独立、参数独立、shadow 数据按策略分组，方便横向比胜率。

### 6.0 策略一览

| 策略 ID | 类型 | 触发逻辑 | 适用场景 |
|---|---|---|---|
| `phase-sync-v1` | 趋势同步（默认 active）| 6 阶段识别 + bias 调节器 + 5 BUY × 4 SELL × TP | 主流默认，覆盖面最广 |
| `rsi-reversion-v1` | 反转抄底 | RSI(14) ≤ 30 + 距均值 ≥ 3% + 阶段 / 仓位 / 历史 6 道闸 | 急跌后博弈反弹 |
| `mean-reversion-v1` | 均值回归 | 20 日 z-score ≤ -2σ + 距均值 ≥ 5% + 历史 ≥ 40 天 | 长周期偏离 |
| `grid-half-v1` | 半网格 | 网格步长 5%、最多 3 档、单档 ≤ 10%、紧急 z-score -2.5σ + T+7 锁感知 | 横盘震荡 |

**切换方式**：策略管控页顶部 tab 一键切；后端把 `active_strategy` 写到 state，所有推送会立刻走新策略。

### 6.1 趋势同步（phase-sync-v1）核心信号

| 信号类 | 优先级 | 触发频率 | 说明 |
|---|---|---|---|
| **A 类止损**（持仓时）| 最高，必推 | 1H | 固定 -15% / 移动 -12% / 跌破强支撑 / 1H 急跌 |
| **B 类警示** | 第二 | 1H | 跌破主支撑 / 大盘走弱 / 量价背离假突破 |
| **C 类强买入** | 第三 | 1H | 突破前期高 + 大盘配合 + 量价确认 |
| **D4 突破回踩** | 第四 | 10 min | C 信号后回踩缩量再启动（最高质量入场）|
| **D 类买入** | 第五 | 10 min | 底部反弹 / 5-10 均线金叉 / 深跌 V 反 |
| **TP 止盈** | 软信号 | 1H | 浮盈 +20% / +40% / +70% 触发，按 bias 缩放 |
| **LEGACY_ALERT** | 独立通道 | 任何时候 | 套牢仓接近 ¥5K/5.5K/6K/6.5K 时单独提醒 |

**关键设计**：
- T+7 不对称：买入高频（10min），卖出低频（1H）+ 解锁后才能执行
- 阶段感知：6 阶段（吸筹/洗盘/蓄力/拉升/派发/下跌）决定哪些信号生效
- 庄家信号：whale_floor_price 替代普通止损（庄家承诺底守不住才离场）
- CS2 适配：止损 -15%、止盈 +20/40/70%（远比股票宽，匹配 CS2 真实波动）

详见 `strategy_v2.md`。

### 6.2 Shadow 影子跟跑

每次 fast cycle 会**对所有 4 套策略**运行一遍 BUY 评估：
- active 策略：信号实际推送 + 写 shadow（带策略标签）
- 其他 3 套：仅写 shadow，不推送，4 小时去重防重复

AI 复盘页的 shadow 表会按策略 ID 分组，能直接看到"过去 30 天 RSI-反转 vs 趋势同步"的胜率对比。

### 6.3 Bias 调节器（A + B 增强）

LLM 分类 / 关键词分类得到的 `fundamentals.bias` 会**实时**调节规则引擎参数：

| bias 值 | BUY 优先级 | 止损乘数 | 止盈乘数 | 实际效果（基准 -15% 止损 / +20%/40%/70% 止盈）|
|---|---|---|---|---|
| `positive_with_whale_buy` | +1 | ×1.1 | ×1.3 | 止损放到 -16.5%，第三档止盈拉到 +91% |
| `positive` | +1 | ×1.0 | ×1.1 | 止损不变，止盈略放 |
| `neutral_positive` | +0.5 | ×1.0 | ×1.05 | 略偏多 |
| `neutral` | 0 | ×1.0 | ×1.0 | 全不变 |
| `negative` | -1 | ×0.7 | ×0.8 | 止损 -10.5%，止盈 +16/32/56% |
| `emergency` | **屏蔽** | ×0.5 | ×0.6 | BUY 全屏蔽，止损 -7.5%，止盈 +12/24/42% |

每条推送的 SELL 信号 advice 末尾会带 `[bias=negative ×0.7]` 等标记，每条 `recommendations_log` 同时记录 `bias_applied / bias_stop_mult / bias_tp_mult`，便于事后复盘"LLM 判断对不对、对决策影响多大"。

**设置页 → 基本面卡片**会显示当前 bias 实际生效的三个数值，所见即所得。

---

## 七、文件结构（一图全览）

```
<安装目录>/                          ← 代码（每次升级覆盖）
│
├── 📜 文档
│   ├── README.md                    本文件
│   ├── CHANGELOG.md                 版本变更日志
│   ├── RELEASE_NOTES_v3.0.0.md      v3 发布说明
│   └── strategy_v2.md               完整策略说明
│
├── 🐍 监控引擎入口
│   ├── monitor_fast.py              10min - BUY 信号
│   ├── monitor_slow.py              1H - SELL + 阶段 + 跨品种
│   ├── daily_review.py              23:00 - 复盘 + 截图 + News
│   ├── add_item.py                  向导式加新品种
│   └── backend_api.py               FastAPI 桥接（前端用）
│
├── 🔧 调度入口
│   ├── setup.bat                    一键安装依赖
│   ├── ⭐ Sentinel.bat               一键启动整套（API + 嵌入式监控 + 浏览器）
│   ├── ⭐ Sentinel-Desktop.bat       v3+ 原生桌面应用（pywebview + 系统托盘）
│   ├── desktop_app.py               桌面壳入口（uvicorn + pywebview + pystray）
│   ├── stop_api.bat                 强制停 API（监控随之停止）
│   ├── setup_autostart.bat          可选：装登录自启
│   ├── uninstall_autostart.bat      卸载登录自启
│   ├── start_api_silent.vbs         静默启动包装（自启用）
│   ├── run_backend_api.bat          仅启动 API（不开浏览器，看日志用）
│   ├── run_monitor_fast.bat         单跑 fast（外部 Task Scheduler 模式用）
│   ├── run_monitor_slow.bat         单跑 slow
│   └── run_daily_review.bat         单跑 daily review
│
├── 📦 lib/ — 核心模块
│   ├── config.py                    全局常量
│   ├── utils.py                     时间/JSON/日志
│   ├── state.py                     状态读写 + 历史维护
│   ├── pusher.py                    PushPlus 推送 + Telegram fallback
│   ├── scraper.py                   Playwright SteamDT 抓取（含 Steam CDN 图）
│   ├── indicators.py                MA + RSI + z-score + 动能 + 量价
│   ├── stages.py                    6 阶段识别
│   ├── signals.py                   phase-sync 共享信号库 + bias 调节器
│   ├── ★ strategies/                ⭐ v2.0.0 多策略注册表
│   │   ├── __init__.py              REGISTRY + 分发器 + shadow 跟跑
│   │   ├── phase_sync_v1.py         趋势同步（默认 active）
│   │   ├── rsi_reversion_v1.py      RSI 反转
│   │   ├── mean_reversion_v1.py     均值回归
│   │   └── grid_half_v1.py          半网格 + T+7 锁
│   ├── circuit_breaker.py           应急熔断
│   ├── shadow.py                    影子回测（按策略分组）
│   ├── correlation.py               跨品种 RS + 板块分析
│   ├── portfolio.py                 总仓位风险面板（总预算驱动）
│   ├── screenshots.py               K 线截图归档
│   ├── news_monitor.py              Steam News（关键词 + LLM 双轨）
│   ├── telegram.py                  Telegram bot 接口（预留）
│   ├── ★ llm_provider.py            通用 LLM 客户端（多 provider）
│   └── ★ llm_analyst.py             业务模块：新闻/复盘/参数提案
│
└── 💾 数据 = %APPDATA%\Sentinel\        ← 数据（跨版本永驻，独立于代码）
    ├── m4a4_buzz_kill_state.json     实时状态（核心 + LLM 配置 + AI 评论 + LAN token）
    ├── shadow_signals.json           影子回测记录（按策略分组）
    ├── m4a4_errors.log               错误日志
    ├── logs/                         运行日志（按月份）
    ├── screenshots/                  K 线截图（按日期）
    └── .playwright_profile/          Playwright cookies 持久化
│
├── 🎨 frontend/ — Sentinel UI（v3.0 起 React + Vite + TS）
│   ├── package.json / vite.config.ts / tsconfig.json
│   ├── tailwind.config.js / postcss.config.js
│   ├── index.html                   Vite 入口
│   ├── src/
│   │   ├── main.tsx / App.tsx       路由 + QueryClient 装配
│   │   ├── index.css                设计令牌 + Liquid Glass + 战术网格
│   │   ├── components/              Nav · DopplerCanvas · AKSilhouette · MagneticButton
│   │   ├── pages/                   Home · Charts · Positions · Strategy · AIReview · Settings
│   │   ├── lib/                     api.ts (30+ 端点) · format · toast
│   │   └── hooks/                   useReveal
│   └── dist/                        npm run build 产物（gitignored，运行时由 backend 服务）
│
└── requirements.txt                 Python 依赖
```

---

## 八、常见操作 Cheatsheet

### 8.1 Dashboard 操作（推荐，零命令行）
| 想做的事 | 路径 |
|---|---|
| 桌面应用启动 | 双击 `Sentinel-Desktop.bat`（v3+，原生窗口 + 托盘）|
| 浏览器启动 | 双击 `Sentinel.bat` → http://localhost:8000 |
| 加仓 / 卖出 / 套牢仓 | 仓位管理页 → 卡片操作行（带 `qty_pieces`）|
| **切换 active 策略** | **策略管控页 → 顶部 tab 一键切**（4 选 1）|
| **看 4 策略胜率对比** | 策略管控页 → 单策略详情面板 / AI 复盘页 → Shadow 区 |
| **网格策略独立控制** | 策略管控页 → 网格 tab（开关 + 重启 + 查看 grid_state）|
| 加 / 删 PushPlus token | 设置页 → PushPlus 卡片 |
| 加 / 删监控品种 | 设置页 → 监控品种卡片（板块下拉 8 选 1）|
| **设置总预算** | **设置页 → 总预算卡片**（决定仓位百分比）|
| **改饰品图** | 设置页 → 监控品种 → 「换图」按钮粘贴 URL |
| **Whale 信号开关** | 设置页 → 全局开关 → 忽略 BUY-WHALE |
| **打开局域网访问（v3+）** | 设置页 → 「📱 局域网访问」→ 勾选 ① → 重启 backend |
| **手机扫 QR / 输 URL（v3+）** | 设置页 LAN 卡片显示 IP + QR；可选「②内网信任」免 token |
| 配置 LLM | 设置页 → 大模型接入卡片（DeepSeek / OpenAI / 自定义）|
| 看 Shadow 模拟收益 | AI 复盘页 → Shadow 区（按策略分组）|
| 看 AI 每日复盘 | AI 复盘页 → 评论区 |
| 审批参数提案 | AI 复盘页 → 参数提案区（✓ 应用 / ✗ 拒绝；含 `scope=strategy` per-策略提案）|
| 看监控心跳 | 顶部 nav 状态 pill / 设置页底部 |

### 8.2 命令行 / API
| 想做的事 | 命令 / 步骤 |
|---|---|
| **桌面应用模式启动（v3+）** | **双击 `Sentinel-Desktop.bat`** |
| 浏览器模式启动 | 双击 `Sentinel.bat` |
| 仅启动 API（看实时日志） | `.\run_backend_api.bat` |
| 强制停 API + 监控 | 双击 `stop_api.bat` 或关窗口；桌面模式从托盘右键退出 |
| 手动跑一次 fast 扫描 | `python monitor_fast.py --test` |
| 加新品种（命令行向导）| `python add_item.py` |
| 看错误 | `Get-Content $env:APPDATA\Sentinel\m4a4_errors.log -Encoding UTF8 -Tail 30` |
| 看运行日志 | `Get-Content $env:APPDATA\Sentinel\logs\monitor_fast.log -Encoding UTF8 -Tail 30` |
| 暂停所有调度 | 见 4.5 |
| 恢复所有调度 | 见 4.5 |
| 立即触发任务 | `schtasks /Run /TN "CS2 Monitor Fast"` |
| 看任务状态 | `schtasks /Query /TN "CS2 Monitor Fast" /V /FO LIST` |
| 看某品种最新数据 | `curl http://localhost:8000/api/items/m4a4-buzz-kill-fn` |
| 看总仓位 | `curl http://localhost:8000/api/portfolio` |
| **看 4 策略列表 + 性能** | `curl http://localhost:8000/api/strategies` |
| **切换 active 策略** | `curl -X POST http://localhost:8000/api/strategies/active -H "Content-Type: application/json" -d "{\"id\":\"rsi-reversion-v1\"}"` |
| **看某品种网格状态** | `curl http://localhost:8000/api/grid/m4a4-buzz-kill-fn` |
| **重启网格** | `curl -X POST http://localhost:8000/api/grid/m4a4-buzz-kill-fn/restart` |
| **设置总预算** | `curl -X POST http://localhost:8000/api/global/budget -d "{\"planned_total_cny\":50000}"` |
| **覆盖饰品图** | `curl -X POST http://localhost:8000/api/items/<id>/image -d "{\"image_url\":\"https://...\"}"` |
| 看影子统计 | `curl http://localhost:8000/api/shadow/stats` |
| 看监控心跳 | `curl http://localhost:8000/api/health/freshness` |
| **看 LAN 配置 + token（v3+）** | `curl http://localhost:8000/api/global/lan` |
| **切 LAN 模式（v3+）** | `curl -X POST http://localhost:8000/api/global/lan -d "{\"enabled\":true,\"trust_private\":true}"` |
| **重置 LAN token（v3+）** | `curl -X POST http://localhost:8000/api/global/lan/reset_token` |
| 测 LLM 连通 | `curl -X POST http://localhost:8000/api/llm/test` |
| 立即跑新闻分类 | `curl -X POST http://localhost:8000/api/llm/classify_news` |
| 立即生成复盘 | `curl -X POST http://localhost:8000/api/llm/daily_review` |
| 立即生成参数提案 | `curl -X POST http://localhost:8000/api/llm/propose_params` |
| 看 LLM 调用日志 | `curl http://localhost:8000/api/llm/audit_log` |

---

## 九、Telegram 接入（按需启用）

详见 `lib/telegram.py` 文档字符串。简版：

1. Telegram 找 @BotFather → /newbot → 拿 bot_token
2. 给 bot 发任意消息后访问 `https://api.telegram.org/bot<TOKEN>/getUpdates` 拿 chat_id
3. 编辑 `state.json` 的 `global.telegram_config`：
```json
"telegram_config": {
  "enabled": true,
  "bot_token": "1234:ABC...",
  "recipients": [{"name": "primary", "chat_id": "123456"}]
}
```
4. 之后所有信号自动**同时**推送到 PushPlus + Telegram。

---

## 十、故障排查

### 10.1 抓取失败 / Cloudflare 拦截

```powershell
# 删除 playwright cookies 重建（v2.1+ 默认在 %APPDATA%\Sentinel\）
Remove-Item -Recurse "$env:APPDATA\Sentinel\.playwright_profile"
# 改 scraper.py 的 SteamDTScraper(headless=False) 用可视模式手动通过验证码
```

### 10.1.5 setup.bat 安装 Chromium 卡住 / 超时

报错 `Request to https://storage.googleapis.com/... timed out`：

国内访问 Google CDN 经常超时。`setup.bat` 已经默认走淘宝镜像，但如果还是失败：

```powershell
# 手动指定镜像后重跑
$env:PLAYWRIGHT_DOWNLOAD_HOST = "https://cdn.npmmirror.com/binaries/playwright"
python -m playwright install chromium
```

或换其他镜像：
```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST = "https://npmmirror.com/mirrors/playwright"
```

最稳的方式是启 VPN 再跑 setup.bat。

### 10.2 PushPlus 推送失败

- 检查 token 是否过期（PushPlus 网页登录看）
- 免费版每天 200 条上限；信号触发频率高时可能用完
- 检查网络是否能访问 pushplus.plus

### 10.3 中文乱码

确保 `.bat` 文件里有：
```
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
```

读取日志时用：
```powershell
Get-Content xxx.log -Encoding UTF8
```

### 10.4 任务不自动跑

```powershell
# 检查是否启用
schtasks /Query /TN "CS2 Monitor Fast" /V /FO LIST | Select-String "计划任务状态"
# 检查上次运行结果
schtasks /Query /TN "CS2 Monitor Fast" /V /FO LIST | Select-String "上次结果"
```

非 0x0 表示失败，看 `logs\monitor_fast.log` 找异常。

### 10.5 前端 API 离线

- 确认 `backend_api.py` 终端窗口未关闭，或桌面应用 / 托盘进程未退出
- 浏览器打开 http://localhost:8000/docs 看 API 是否能访问
- 检查防火墙是否拦了 8000 端口（仅本机模式不会拦；LAN 模式首次会询问，选「专用网络」）

### 10.5.1 桌面应用打不开窗口 / 闪退（v3+）

- 看 `<安装目录>\desktop_app_error.log` 末尾几行，常见原因：
  - **WebView2 Runtime 未安装** — 去 https://developer.microsoft.com/microsoft-edge/webview2/ 下载 Evergreen Standalone Installer 装一次
  - **pywebview / pystray 没装** — `pip install -r requirements.txt`
  - **8000 端口被占** — 关另一个 Sentinel 实例
- 如果只是托盘图标看不见但功能正常，看 Windows「显示隐藏的图标」溢出区

### 10.6 state.json 损坏 / 想重置

每次 add_item 都会备份到 `m4a4_buzz_kill_state.json.bak`。手动恢复：
```powershell
Copy-Item m4a4_buzz_kill_state.json.bak m4a4_buzz_kill_state.json
```

### 10.7 升级到 v2.0.0 后状态字段缺失

老用户首次启动 v2.0.0 会自动迁移 state（v3 → v4），补全 `qty_pieces` / `planned_total_cny` / `active_strategy` / `strategies` / `grid_state` / `image_url` / `ignore_whale_signals` 等字段。如果出错：
```powershell
# 备份后用 example 模板重置（会丢仓位历史）
Copy-Item m4a4_buzz_kill_state.json m4a4_buzz_kill_state.json.bak
Copy-Item state.example.json m4a4_buzz_kill_state.json
```
然后到设置页重填总预算、PushPlus token 即可。

### 10.8 v2.1+ 数据目录在哪？想换怎么换？

**默认位置**：`C:\Users\<你>\AppData\Roaming\Sentinel\`

设置页 →「📁 数据目录」卡片有「📂 打开数据目录」按钮，一键定位。

**想换位置（多实例 / 测试 / 移动）**：
```powershell
# 启动前设置环境变量
$env:SENTINEL_DATA_DIR = "D:\我的备用 sentinel 数据"
.\Sentinel.bat
```

**想退回旧行为（数据放安装目录）**：
```powershell
$env:SENTINEL_DATA_DIR = "D:\sentinel-cs2"   # 安装目录
.\Sentinel.bat
```

**完全干净重来**：直接删掉 `%APPDATA%\Sentinel\` 整个目录，下次启动会从空状态开始。

---

## 十一、维护建议

### 每天（被动）
- 微信会自动收到任何信号 + 23:00 复盘
- 你只需要点开看，不需要打开电脑

### 每周（主动）
- 看一次复盘报告，看影子信号统计判断哪类信号该淘汰/调整
- **看一眼策略管控页 4 套策略 shadow 胜率**，判断要不要切 active
- 用 `python add_item.py` 加 1-2 个想关注的新品种

### 每月（策略迭代）
- **AI 复盘页**审批 LLM 自动生成的参数提案（每日 23:00 跑一次，需配 LLM key + 勾选「参数调整提案」模块）
- 提案应用前自动备份 `original_value`，可回滚；`scope=strategy` 提案针对单个策略调参，不影响其他策略
- **比 4 套策略的累计胜率 / 平均收益**，决定下个月用哪套做 active；切策略不会丢失已 AI 调过的参数

### 每年（清理）
- shadow_signals.json 长大后可以归档：复制成 `shadow_signals_2026.json`，新文件 reset
- screenshots/ 自动清理 30 天前的，不需要手动

---

## 十二、安全说明

- ✅ **默认仅 127.0.0.1 监听**：不开 LAN 模式时局域网/公网都连不上
- ✅ **LAN 模式可选 + Token 鉴权（v3+）**：来自非本机的 POST/DELETE 必须带 `X-Sentinel-Token` header；token 自动 uuid4 生成、可在设置页一键重置
- ✅ **「内网信任」分级开关（v3+）**：私网/CGNAT/链路本地段可选免 token（适合自家 WiFi）；公网 IP **永远** 要 token
- ✅ **CORS**：仅本机模式只允许 localhost 来源；LAN 模式打开后扩展为 `*`（结合 token 鉴权保护）
- ✅ **状态文件本地存储**：不上传到任何云服务
- ✅ **PushPlus 单向推送**：你的 token 只用于发消息，不暴露读权限
- ✅ **LLM 参数提案双重防护**：永不直接应用，必须用户审批；应用前自动备份原值
- ⚠️ **PushPlus token / LLM API key / LAN token 都是敏感信息**：state.json 不要分享给别人，**不要上传到任何代码仓库**（本项目 .gitignore 已默认排除）
- ⚠️ **浏览器 cookies**（.playwright_profile）含 SteamDT 登录态：同样不要分享
- ⚠️ **LLM API key 泄露应对**：立刻去 provider 控制台 revoke，重新生成填回设置页
- ⚠️ **公共 WiFi 不要开「内网信任」**：咖啡店/办公室/校园网下，同网段任何人都能直接 CRUD；只在自家独立路由器开

---

## 十三、已知限制 / 未来计划

### 当前限制
- K 线截图依赖 SteamDT 页面 DOM 结构，对方改版可能失效
- Steam CDN 饰品图依赖 SteamDT 页面 `img.zbt.com` 链接，失效时可在设置页手动换图
- 同一品种不同磨损（FN/MW/FT 等）需要分别加为独立 item
- 没有自动下单功能（Steam 市场不开放 API，只能你手动）
- shadow signal 需要 7+ 天才能开始统计胜率（前期数据稀疏）
- LLM 参数提案需要 ≥5 条 shadow 样本才会生成
- 4 策略 shadow 跟跑会让一次 cycle 评估变多，但不影响推送速度（仅 active 推送）

### 路线图
- [x] ~~苹果式多页 SPA dashboard~~
- [x] ~~Web CRUD（仓位 / token / 品种）~~
- [x] ~~监控心跳检测 + 状态告警~~
- [x] ~~LLM 接入：新闻语义分类（Phase 1）~~
- [x] ~~LLM 接入：每日复盘评论（Phase 3）~~
- [x] ~~LLM 接入：参数调整提案 + 审批（Phase 4）~~
- [x] ~~Bias 调节器（A+B 增强）~~
- [x] ~~多策略架构（v2.0.0：4 套并行 + shadow 跟跑 + 注册表分发）~~
- [x] ~~视觉品牌重塑（v2.0.0：Liquid Glass + 3D AK-47 + WebGL Doppler）~~
- [x] ~~真实 Steam 饰品图（v2.0.0：自动抓 + 手动换图）~~
- [x] ~~总预算驱动的仓位百分比（v2.0.0）~~
- [x] ~~`qty_pieces` 精确数量计算（v2.0.0）~~
- [x] ~~半网格策略 T+7 锁感知（v2.0.0：grid-half-v1）~~
- [x] ~~跨版本数据持久化（v2.1.0：%APPDATA%\Sentinel\）~~
- [x] ~~完整 React + Vite + TS 项目（v3.0.0）~~
- [x] ~~桌面 app 封装（v3.0.0：pywebview + 系统托盘）~~
- [x] ~~局域网 / 手机访问（v3.0.0：X-Sentinel-Token + 内网信任开关）~~
- [x] ~~per-strategy AI 调参（v3.0.0：scope=strategy 提案）~~
- [x] ~~AI 复盘 / 参数提案每日自动跑（v3.0.0）~~
- [x] ~~板块跟涨整合到 phase-sync 多因子加成（v3.0.0：sector_boost）~~
- [ ] LLM 接入：庄家公告自动解析（Phase 2）
- [ ] 走势图加技术指标叠加（MA / 成交量 / 关键位）
- [ ] WebSocket 实时推送（信号触发时前端立刻闪烁）
- [ ] 暗色模式
- [ ] 移动端 PWA（manifest + service worker，可「添加到主屏」）
- [ ] PyInstaller 单 exe 发布（让没有 Python 的朋友也能用）
- [ ] iOS / Android 原生 app（PWA 跑通后再说）

---

## 十四、技术栈致谢

| 层 | 技术 |
|---|---|
| 监控引擎 | Python 3.9+ · Playwright · Requests |
| 策略层 | 注册表分发器 · 4 套独立模块（含 phase-sync / RSI / MR / Grid） · Shadow 跟跑 |
| API 服务 | FastAPI · Uvicorn · Pydantic · X-Sentinel-Token 中间件（v3+）|
| 前端 | **React 18 · Vite · TypeScript · Tailwind CSS · TanStack Query · React Router**（v3+）|
| 桌面壳 | **pywebview（WebView2 内核） · pystray 系统托盘 · 单 Python 进程**（v3+）|
| 视觉 | Liquid Glass · CSS 3D Transforms · WebGL Doppler 着色器 · simplex 噪声 |
| 推送 | PushPlus · Telegram Bot API |
| 调度 | 嵌入式 asyncio scheduler / Windows Task Scheduler |
| 持久化 | JSON（atomic write） · 自愈 schema migration · `%APPDATA%\Sentinel\` 用户数据目录 |
| 数据源 | SteamDT · Steam Web API · Steam CDN（饰品图）|
| LLM 抽象 | Anthropic / OpenAI / DeepSeek / 任意 OpenAI 兼容协议（自托管 vLLM 等）|

---

**项目至此完整闭环**：

```
数据采集 → 指标计算 → 阶段识别 → 4 策略并跑 → 风险控制 → 推送通知
   ↑                                              ↓
   └── 参数迭代 ← 用户审批 ← LLM 提案 ← 影子回测 ← 复盘归档
                                                    ↓
                                           前端可视化 + Web CRUD
```

🟢 **100% 数据本地化** · **规则引擎 + 可选 LLM 双层** · **完全开源可定制**
