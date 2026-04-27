# Sentinel · CS2 饰品智能监控系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)]()

> 100% 本地化的 CS2 饰品价格监控、信号推送、仓位管理、回测分析平台。
> 规则引擎 + 可选 LLM 语义层。配套苹果式极简多页 SPA。

> ⚠️ **免责声明**：本工具仅用于个人学习与价格监控，不构成任何投资建议。CS2 饰品交易具有风险，使用者自担一切责任。本项目与 Valve、Steam、SteamDT 等任何第三方公司**无关联**。

---

## 一、项目能做什么

**自动监控 4+ 个 CS2 饰品**（可任意扩展），**每 10 分钟**采集一次价格 / 量能 / 大盘 / 持仓数据，按内置策略评估**买卖信号**（5 种 BUY 类 + 4 种 SELL 类 + TP 止盈 + 6 种庄家阶段识别），**触发即推送**到 PushPlus 微信（最多 3 个接收人），并保存完整的：

- ✅ 实时价格历史（90 天滚动）
- ✅ 信号触发日志（每次扫描必写，带 bias 应用记录）
- ✅ 推送记录（用于复盘）
- ✅ 影子仓位回测（每个 BUY 信号自动跟踪 7 日收益）
- ✅ 总仓位风险面板（成本/市值/集中度/警告）
- ✅ 庄家阶段切换记录
- ✅ 跨品种相对强度（RS）+ 板块联动分析
- ✅ 每日 23:00 自动复盘报告（推微信 + 写 state）
- ✅ K 线截图归档（30 天滚动）
- ✅ Steam News 自动监控（关键词 + LLM 语义双轨）
- ✅ 应急熔断机制（大盘崩盘时自动停推 BUY）
- ✅ **bias 调节器**：基本面偏置 → 自动调整 BUY 优先级 + 止损/止盈阈值
- ✅ **可选 LLM 接入**：Anthropic / OpenAI / DeepSeek / 任意 OpenAI 兼容协议

**配套前端**（Sentinel UI）：苹果式极简多页 SPA，5 个功能页，**直接连接后端做增删改**：
- **概览**：实时价格 / hero 卡片 / 视差视觉
- **走势图**：折线 / K 线切换 + 24H/3D/7D 范围 + 成交量柱状图
- **仓位管理**：每个品种内嵌操作栏（加仓 / 卖出 / 设套牢仓 / 清空），直接写后端
- **AI 复盘**：Shadow 模拟收益统计 + AI 每日评论 + 参数调整提案审批
- **设置**：PushPlus token 增删 / 监控品种增删（含板块下拉）/ LLM 配置 / 监控心跳

---

## 二、系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                          数据源                                   │
│   • SteamDT 商品页（playwright 爬取）                              │
│   • Steam News API（fundamentals 自动更新）                        │
│   • LLM API（可选：新闻语义 / 复盘 / 参数提案）                     │
│   • 用户主对话 / Web 仪表板（增删品种/仓位/token/录入庄家）         │
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
│   │  (bias调优先级)│  │ (bias调阈值)   │  │ + AI 评论(可选)│     │
│   └────────────────┘  └────────────────┘  └────────────────┘     │
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
│                          数据持久层                               │
│   D:\claude\xuanxiao\                                            │
│   ├── m4a4_buzz_kill_state.json   实时状态 + LLM配置 + AI评论    │
│   ├── shadow_signals.json         影子回测                       │
│   ├── screenshots/YYYY-MM-DD/     K 线归档                       │
│   ├── logs/                       运行日志                       │
│   └── m4a4_errors.log             错误累积                       │
└─────────────────────────────┬────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │ PushPlus │    │ FastAPI  │    │ Claude   │
       │ 三人微信  │    │  :8000   │    │ ad-hoc   │
       └──────────┘    └────┬─────┘    └──────────┘
                            │
                            ▼
                    ┌──────────────────────┐
                    │  Sentinel UI (SPA)   │
                    │  概览 / 走势图 /     │
                    │  仓位管理 / AI复盘 / │
                    │  设置                 │
                    └──────────────────────┘
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
- Cowork / Claude Desktop（用于 ad-hoc 提问、加新品种、解读庄家消息）
- **LLM API key** 任意一种（启用 Phase 1/3/4 智能模块）：
  - Anthropic（claude-sonnet-4-6 等）
  - OpenAI（gpt-4o-mini 等）
  - DeepSeek（deepseek-chat，性价比最高）
  - 其他 OpenAI 兼容协议（Qwen / Moonshot / 自托管 vLLM）

---

## 四、首次部署（一次性，约 5 分钟）

### 4.1 安装依赖

```powershell
cd D:\claude\xuanxiao
.\setup.bat
```

`setup.bat` 会自动：
1. 检查 Python 3.9+
2. `pip install playwright playwright-stealth requests fastapi uvicorn`
3. `playwright install chromium`（首次约 5 分钟）

### 4.2 启动（**就这一步**）

双击 `Sentinel.bat`：

会发生：
- API 服务在 8000 端口启动
- **嵌入式调度器自动开始跑**：每 10min fast / 每 1H slow / 每天 23:00 review
- 4 秒后浏览器自动打开 `http://localhost:8000`

**整套系统就在这一个窗口里**。关掉这个窗口 = 全部停止。

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

如果你切到 **Windows 任务计划器** 模式，需要 **管理员 PowerShell** 一次性建任务：

```powershell
schtasks /Create /TN "CS2 Monitor Fast" /TR "D:\claude\xuanxiao\run_monitor_fast.bat" /SC MINUTE /MO 10 /RL HIGHEST /F
schtasks /Create /TN "CS2 Monitor Slow" /TR "D:\claude\xuanxiao\run_monitor_slow.bat" /SC HOURLY /MO 1 /ST 00:05 /RL HIGHEST /F
schtasks /Create /TN "CS2 Daily Review" /TR "D:\claude\xuanxiao\run_daily_review.bat" /SC DAILY /ST 23:00 /RL HIGHEST /F
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

---

## 五、日常使用

### 5.1 启动并访问 Dashboard

**双击 `Sentinel.bat`** — 这一步等于：
- 启动 API 服务
- 嵌入式调度器自动开跑监控
- 浏览器自动打开 `http://localhost:8000`

**dashboard 内容**：
- 顶部 nav 状态 pill 显示心跳：`🟢 监控运行中 · X 分钟前更新`
- 5 个功能页：概览 / 走势图 / 仓位管理 / AI 复盘 / 设置
- 数据每 30 秒自动刷新

**停止整套**：关闭 Sentinel.bat 那个窗口（点 X 或 Ctrl+C）。

---

> **想 7×24 后台跑**？切到「Windows 任务计划器」模式（设置页 → 监控调度器卡片），监控独立运行，关 dashboard 也持续。详见 4.5。

### 5.2 报告建仓 / 加仓 / 平仓（**3 种方式**）

#### 方式 A：Web 仪表板（最方便）

进 **仓位管理** 页 → 找到对应品种卡片 → 操作行选择 + 输入参数 + 点「执行」：

| 操作 | 价格输入 | % 输入 |
|---|---|---|
| 加仓 | 单价 | 仓位百分比（30 = 30%） |
| 卖出 | 卖出单价 | 卖出比例（按总仓位百分比） |
| 设套牢仓 | 均价 | 数量（把） |
| 移除套牢仓 | — | — |
| 清空新仓 | — | — |

后端会原子写 `position.tiers`，A 类止损自动激活。每次操作还会写一条 `recommendations_log`。

#### 方式 B：找 Claude 主对话

直接说：
> "M4A4 喧嚣 我以 ¥4,250 建第 1 档 30%"

Claude 帮你改 state.json。

#### 方式 C：手动改 state.json
（不推荐，容易写错格式。）

### 5.3 加新监控品种（**3 种方式**）

#### 方式 A：Web 仪表板（最快，无需重启）

进 **设置** 页 → 「🎯 监控品种」卡片 → 「➕ 新增监控品种」表单：
- URL（必填，校验是 SteamDT 域名）
- 完整名称 + 短名
- **板块下拉**：一代手套 / 二代手套 / 三代手套 / 武库 / 千百战 / 收藏品
- 关键位（折叠区，建议填以激活信号）
- 点「添加品种」→ 下次 fast 任务自动开始抓取

#### 方式 B：命令行向导

```powershell
python add_item.py
```

向导版本字段更全（含阶段标签 / 自定义阈值），推荐复杂品种用这个。

#### 方式 C：找 Claude

> "新增监控 [品种] URL 是 https://..."

### 5.4 增删 PushPlus token

进 **设置** 页 → 「📱 PushPlus 微信推送」卡片：
- 现有 token 旁边有「删除」按钮
- 下方「➕ 新增 token」表单：填名字 + 32 位 token → 点添加

### 5.5 录入庄家信号

目前仍走 Claude 主对话：
> "刚收到庄家消息 [截图 / 文字]，请录入"

> Phase 2 LLM 庄家公告自动解析正在路上 — 届时可以直接在网页粘贴文本。

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
| Provider | Anthropic / OpenAI / 自定义 |
| Model | `claude-sonnet-4-6` / `gpt-4o-mini` / `deepseek-chat` |
| API Key | `sk-...`（明文存 state.json，仅本地）|
| Base URL | 留空用默认；自定义如 `https://api.deepseek.com` |

启用模块（独立开关）：
- ☑ 新闻语义分类（替代关键词）
- ☐ 庄家公告解析（Phase 2 待开放）
- ☑ 每日复盘评论（写入 ai_review）
- ☑ 参数调整提案（需 shadow ≥5 条样本）

工作流：填好 → **保存配置** → **测试连通**（应回 `✓ 连通 XXms · "OK"`）→ 勾选模块 → 再次保存 → 立即触发或等定时任务。

> ⚠️ API key 明文存于 `m4a4_buzz_kill_state.json`，不要把该文件上传到代码仓库。

---

## 六、策略简介

详见 `strategy_v2.md`。核心：

| 信号类 | 优先级 | 触发频率 | 说明 |
|---|---|---|---|
| **A 类止损**（持仓时）| 最高，必推 | 1H | 固定 -15% / 移动 -12% / 跌破强支撑 / 1H 急跌 |
| **B 类警示** | 第二 | 1 H | 跌破主支撑 / 大盘走弱 / 量价背离假突破 |
| **C 类强买入** | 第三 | 1 H | 突破前期高 + 大盘配合 + 量价确认 |
| **D4 突破回踩** | 第四 | 10 min | C 信号后回踩缩量再启动（最高质量入场）|
| **D 类买入** | 第五 | 10 min | 底部反弹 / 5-10 均线金叉 / 深跌 V 反 |
| **TP 止盈** | 软信号 | 1H | 浮盈 +20% / +40% / +70% 触发，按 bias 缩放 |
| **LEGACY_ALERT** | 独立通道 | 任何时候 | 套牢仓接近 ¥5K/5.5K/6K/6.5K 时单独提醒 |

**关键设计**：
- T+7 不对称：买入高频（10min），卖出低频（1H）+ 解锁后才能执行
- 阶段感知：6 阶段（吸筹/洗盘/蓄力/拉升/派发/下跌）决定哪些信号生效
- 庄家信号：whale_floor_price 替代普通止损（庄家承诺底守不住才离场）
- CS2 适配：止损 -15%、止盈 +20/40/70%（远比股票宽，匹配 CS2 真实波动）

### 6.1 Bias 调节器（A + B 增强）

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
D:\claude\xuanxiao\
│
├── 📜 文档
│   ├── README.md                    本文件
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
│   ├── setup.bat                    一键安装
│   ├── run_monitor_fast.bat         任务调度器入口
│   ├── run_monitor_slow.bat         同上
│   ├── run_daily_review.bat         同上
│   └── run_backend_api.bat          启动 API 服务
│
├── 📦 lib/ — 核心模块
│   ├── config.py                    全局常量
│   ├── utils.py                     时间/JSON/日志
│   ├── state.py                     状态读写 + 历史维护
│   ├── pusher.py                    PushPlus 推送 + Telegram fallback
│   ├── scraper.py                   Playwright SteamDT 抓取
│   ├── indicators.py                多时间框架 MA + 动能 + 量价
│   ├── stages.py                    6 阶段识别
│   ├── signals.py                   BUY / SELL / TP + bias 调节器
│   ├── circuit_breaker.py           应急熔断
│   ├── shadow.py                    影子回测
│   ├── correlation.py               跨品种 RS + 板块分析
│   ├── portfolio.py                 总仓位风险面板
│   ├── screenshots.py               K 线截图归档
│   ├── news_monitor.py              Steam News（关键词 + LLM 双轨）
│   ├── telegram.py                  Telegram bot 接口（预留）
│   ├── ★ llm_provider.py            通用 LLM 客户端（多 provider）
│   └── ★ llm_analyst.py             业务模块：新闻/复盘/参数提案
│
├── 💾 数据
│   ├── m4a4_buzz_kill_state.json    实时状态（核心）
│   ├── shadow_signals.json          影子回测记录
│   ├── m4a4_errors.log              错误日志
│   ├── logs/                        运行日志（按月份）
│   ├── screenshots/                 K 线截图（按日期）
│   └── .playwright_profile/         Playwright cookies 持久化
│
├── 🎨 frontend/ — Sentinel UI
│   ├── preview.html                 ⭐ 单文件 dashboard（双击直接看）
│   ├── README.md                    前端设计文档
│   ├── package.json                 React 项目（如需扩展）
│   └── src/components/              React 组件源码
│       ├── MagneticButton.jsx
│       ├── HeroSection.jsx
│       └── PriceAnalysisSection.jsx
│
└── requirements.txt                 Python 依赖
```

---

## 八、常见操作 Cheatsheet

### 8.1 Dashboard 操作（推荐，零命令行）
| 想做的事 | 路径 |
|---|---|
| 看实时数据 | 浏览器打开 `http://localhost:8000` |
| 加仓 / 卖出 / 套牢仓 | 仓位管理页 → 卡片操作行 |
| 加 / 删 PushPlus token | 设置页 → PushPlus 卡片 |
| 加 / 删监控品种 | 设置页 → 监控品种卡片（板块下拉 6 选 1）|
| 配置 LLM | 设置页 → 大模型接入卡片 |
| 看 Shadow 模拟收益 | AI 复盘页 → Shadow 区 |
| 看 AI 每日复盘 | AI 复盘页 → 评论区 |
| 审批参数提案 | AI 复盘页 → 参数提案区（✓ 应用 / ✗ 拒绝）|
| 看监控心跳 | 顶部 nav 状态 pill / 设置页底部 |

### 8.2 命令行 / API
| 想做的事 | 命令 / 步骤 |
|---|---|
| 启动 API | `.\run_backend_api.bat` |
| 手动跑一次 fast 扫描 | `python monitor_fast.py --test` |
| 加新品种（命令行向导）| `python add_item.py` |
| 看错误 | `Get-Content m4a4_errors.log -Encoding UTF8 -Tail 30` |
| 看运行日志 | `Get-Content logs\monitor_fast.log -Encoding UTF8 -Tail 30` |
| 暂停所有调度 | 见 4.5 |
| 恢复所有调度 | 见 4.5 |
| 立即触发任务 | `schtasks /Run /TN "CS2 Monitor Fast"` |
| 看任务状态 | `schtasks /Query /TN "CS2 Monitor Fast" /V /FO LIST` |
| 看某品种最新数据 | `curl http://localhost:8000/api/items/m4a4-buzz-kill-fn` |
| 看总仓位 | `curl http://localhost:8000/api/portfolio` |
| 看影子统计 | `curl http://localhost:8000/api/shadow/stats` |
| 看监控心跳 | `curl http://localhost:8000/api/health/freshness` |
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
# 删除 playwright cookies 重建
Remove-Item -Recurse D:\claude\xuanxiao\.playwright_profile
# 改 scraper.py 的 SteamDTScraper(headless=False) 用可视模式手动通过验证码
```

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

- 确认 `backend_api.py` 终端窗口未关闭
- 浏览器打开 http://localhost:8000/docs 看 API 是否能访问
- 检查防火墙是否拦了 8000 端口（一般不会，因为是 127.0.0.1 内网回环）

### 10.6 state.json 损坏 / 想重置

每次 add_item 都会备份到 `m4a4_buzz_kill_state.json.bak`。手动恢复：
```powershell
Copy-Item m4a4_buzz_kill_state.json.bak m4a4_buzz_kill_state.json
```

---

## 十一、维护建议

### 每天（被动）
- 微信会自动收到任何信号 + 23:00 复盘
- 你只需要点开看，不需要打开电脑

### 每周（主动）
- 看一次复盘报告，看影子信号统计判断哪类信号该淘汰/调整
- 用 `python add_item.py` 加 1-2 个想关注的新品种

### 每月（策略迭代）
- 找 Claude 主对话："最近一个月 D1 信号胜率 30%，要不要把阈值调严？"
- Claude 帮你改 thresholds 后跟踪 7-14 天看效果

### 每年（清理）
- shadow_signals.json 长大后可以归档：复制成 `shadow_signals_2026.json`，新文件 reset
- screenshots/ 自动清理 30 天前的，不需要手动

---

## 十二、安全说明

- ✅ **API 仅 127.0.0.1 监听**：不离开你的电脑，局域网/公网都连不上
- ✅ **CORS 白名单**：只允许 localhost 来源的浏览器调用
- ✅ **状态文件本地存储**：不上传到任何云服务
- ✅ **PushPlus 单向推送**：你的 token 只用于发消息，不暴露读权限
- ✅ **LLM 参数提案双重防护**：永不直接应用，必须用户审批；应用前自动备份原值
- ⚠️ **PushPlus token 是敏感信息**：state.json 不要分享给别人
- ⚠️ **浏览器 cookies**（.playwright_profile）含 SteamDT 登录态：同样不要分享
- ⚠️ **LLM API key 明文存于 state.json**：不要上传到代码仓库；如果泄露立刻去 provider 控制台 revoke
- ⚠️ **写端点无身份校验**：本地 dashboard 可以做任何 CRUD。如果哪天暴露到局域网，需要先加 token 头校验

---

## 十三、已知限制 / 未来计划

### 当前限制
- K 线截图依赖 SteamDT 页面 DOM 结构，对方改版可能失效
- 同一品种不同磨损（FN/MW/FT 等）需要分别加为独立 item
- 没有自动下单功能（Steam 市场不开放 API，只能你手动）
- shadow signal 需要 7+ 天才能开始统计胜率（前期数据稀疏）
- LLM 参数提案需要 ≥5 条 shadow 样本才会生成

### 路线图
- [x] ~~苹果式多页 SPA dashboard~~
- [x] ~~Web CRUD（仓位 / token / 品种）~~
- [x] ~~监控心跳检测 + 状态告警~~
- [x] ~~LLM 接入：新闻语义分类（Phase 1）~~
- [x] ~~LLM 接入：每日复盘评论（Phase 3）~~
- [x] ~~LLM 接入：参数调整提案 + 审批（Phase 4）~~
- [x] ~~Bias 调节器（A+B 增强）~~
- [ ] LLM 接入：庄家公告自动解析（Phase 2）
- [ ] 走势图加技术指标叠加（MA / 成交量 / 关键位）
- [ ] WebSocket 实时推送（信号触发时前端立刻闪烁）
- [ ] 完整 React 项目（preview.html 拆到 src/）
- [ ] 暗色模式
- [ ] 移动端 PWA
- [ ] 桌面 app 封装（Tauri）
- [ ] 局域网 / 远程访问（需要先加身份校验层）

---

## 十四、技术栈致谢

| 层 | 技术 |
|---|---|
| 监控引擎 | Python 3.9+ · Playwright · Requests |
| API 服务 | FastAPI · Uvicorn · Pydantic |
| 前端 | HTML5 · Tailwind CSS · 单文件 SPA |
| 推送 | PushPlus · Telegram Bot API |
| 调度 | Windows Task Scheduler |
| 持久化 | JSON（atomic write）|
| 数据源 | SteamDT · Steam Web API |
| LLM 抽象 | Anthropic API · OpenAI 兼容协议 |
| 智能助手 | Claude（Cowork mode）|

---

**项目至此完整闭环**：

```
数据采集 → 指标计算 → 阶段识别 → 信号判定 → 风险控制 → 推送通知
   ↑                                          ↓
   └── 参数迭代 ← 用户审批 ← LLM 提案 ← 影子回测 ← 复盘归档
                                                ↓
                                       前端可视化 + Web CRUD
```

🟢 **100% 数据本地化** · **规则引擎 + 可选 LLM 双层** · **完全开源可定制**

有问题或想加新功能，找 Claude 主对话即可。
