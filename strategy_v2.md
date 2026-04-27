# CS2 饰品智能监控系统 - 策略 v2.0 软件规格文档

**版本**：2.0
**创建日期**：2026-04-26
**适用对象**：本地 Python 监控 + Claude 智能辅助 的混合架构
**适用市场**：SteamDT (CS2 饰品交易平台)

---

## 一、总体目标与设计哲学

### 1.1 解决的核心问题

为 CS2 饰品交易者提供一套**自动化的多品种价格监控 + 信号判定 + 微信推送**系统，要求：
- 充分利用 CS2 市场的特殊性（T+7 锁定期、庄家市、高波动）
- 信号质量优先于数量，避免噪音
- 风险管理为先，最大可承受亏损明确
- 系统持续学习与迭代（影子回测）
- 长期运行成本极低（本地优先 + Claude 按需调用）

### 1.2 CS2 市场的核心特征（设计假设）

| 特征 | 含义 | 对策 |
|---|---|---|
| **T+7 锁定** | 买入后 7 天才能卖 | 买入信号高频、卖出信号延迟 |
| **波动率高** | 单日 ±5% 是常态 | 止损/止盈宽度比股票大 ~2× |
| **庄家市** | 大户能瞬间反转情绪 | 阶段识别 + 庄家信号显式建模 |
| **流动性差异** | 热门品 vs 冷门品 100× 量级差 | 阈值按品种独立配置 |
| **事件驱动** | V 社更新/赛事强烈影响价格 | 基本面 bias + 事件日历 |

### 1.3 设计哲学

1. **本地优先**：所有可机械化的逻辑放在本地 Python，不消耗 Claude token
2. **Claude 仅做"需思考"的事**：基本面分析、形态判断、策略迭代、ad-hoc 提问
3. **数据为王**：所有决策基于持续累积的历史数据，可回测可验证
4. **失败安全**：宁可漏报不可误报；任何字段缺失即跳过该判定
5. **人控制最终决策**：系统只发信号，绝不替用户下单

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户操作界面                                 │
│   ① 微信（接收 PushPlus 推送）                                   │
│   ② Claude 主对话（策略调整、问题分析、建仓汇报、ad-hoc 操作）    │
│   ③ 文件系统（直接查看/编辑 state.json）                         │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                      数据持久层                                   │
│   D:\claude\xuanxiao\                                            │
│   ├── state.json                  ← 实时状态（10min 更新）        │
│   ├── daily_kline_<id>.json       ← 长期日线归档（按品种）        │
│   ├── shadow_signals.json         ← 信号回测记录                  │
│   ├── monthly_archive/*.gz        ← 月度数据压缩归档              │
│   ├── errors.log                  ← 错误日志（按月轮换）          │
│   └── screenshots/                ← K 线截图（每日复盘用）        │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────┴───────┐   ┌─────────┴─────────┐   ┌──────┴──────┐
│  本地 Python  │   │   本地 Python      │   │  Claude     │
│  10 分钟扫描   │   │   1 小时扫描       │   │  按需/每周   │
│               │   │                   │   │             │
│ - 抓数据       │   │ - 完整指标计算      │   │ - V社更新     │
│ - 阶段识别     │   │ - SELL 信号评估     │   │ - 形态判断    │
│ - BUY 信号     │   │ - 阶段切换检测      │   │ - 策略迭代    │
│ - 急买点       │   │ - 复盘            │   │ - 庄家信号录入│
│ - 熔断检测     │   │ - 推送 SELL 提醒   │   │ - 复盘报告    │
│ - 推送 BUY     │   │                   │   │ - ad-hoc 提问 │
└───────────────┘   └───────────────────┘   └─────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
              ┌──────────────────────────────┐
              │       SteamDT (网页爬取)      │
              │   PushPlus (微信推送 webhook) │
              │   WebSearch (V社更新查询)     │
              │   Steam News (CS2 事件)      │
              └──────────────────────────────┘
```

### 2.1 三层调度

| 层 | 频率 | 执行者 | 主要任务 |
|---|---|---|---|
| **Fast** | 10 分钟 | 本地 Python | 价格采集 + BUY 信号 + 急跌买点 + 熔断 + legacy_alert |
| **Slow** | 1 小时（整点） | 本地 Python | 完整指标 + SELL 信号 + 阶段切换 + 跨品种联动 |
| **Daily** | 每天 23:00 | 本地 Python | 复盘汇总 + shadow_signals 统计 + 推送报告 |
| **Weekly+ad-hoc** | 每周/按需 | Claude | V社更新 + 庄家信号录入 + 策略迭代 + 形态分析 |

---

## 三、本地 Python 部分（详细职责）

### 3.1 文件组织

```
D:\claude\xuanxiao\
├── monitor_fast.py          # 10min 调度入口
├── monitor_slow.py          # 1h 调度入口
├── daily_review.py          # 每日 23:00 复盘
├── lib/
│   ├── __init__.py
│   ├── config.py            # 全局配置 + 阈值定义
│   ├── scraper.py           # SteamDT 抓取（playwright）
│   ├── indicators.py        # MA/动能/量价计算
│   ├── stages.py            # 庄家阶段识别
│   ├── signals.py           # BUY/SELL 信号判定
│   ├── pusher.py            # PushPlus 三推送
│   ├── state.py             # state.json 读写 + 历史归档
│   ├── circuit_breaker.py   # 熔断检测
│   ├── correlation.py       # 跨品种联动 + RS 强度
│   ├── shadow.py            # 影子仓位回测
│   └── utils.py             # 时间/格式工具
├── setup.bat                # 一键安装依赖
├── run_monitor_fast.bat     # 任务计划程序入口（10min）
├── run_monitor_slow.bat     # 任务计划程序入口（1h）
├── run_daily_review.bat     # 任务计划程序入口（23:00）
├── requirements.txt         # Python 依赖
├── .playwright_profile/     # playwright 持久化 cookies
├── state.json               # 实时状态
├── daily_kline_*.json       # 长期日线归档（每品种一个）
├── shadow_signals.json      # 信号回测
├── strategy_v2.md           # 本文档
└── errors_YYYY-MM.log       # 月度错误日志
```

### 3.2 monitor_fast.py（每 10 分钟）

**目的**：高频抓取价格 + 抓住瞬间买入机会 + 风险熔断

**完整流程**：
1. 加载 `state.json` 和 `lib.config`
2. 启动 playwright（持久化 context）
3. **大盘抓取**：访问 SteamDT 主页，提取 `market_index`
4. **熔断检测**：调用 `circuit_breaker.check()`，若激活则跳过 BUY 流程
5. **遍历每个 item**：
   1. 访问 item.url，提取 price/today_pct/week_pct/today_volume/stock
   2. 追加 history（含 timestamp、市场快照）
   3. 计算 micro 指标（ma_micro 1H、momentum_score、delta_volume）
   4. **阶段快速识别**（基于近 1-2 天数据）：
      - SHAKEOUT（急跌但未破前低）→ BUY-WASHOUT
      - 庄家防守底附近 → BUY-WHALE
   5. **BUY 信号评估**（仅当 total_qty < 1.0）：
      - BUY-WASHOUT、BUY-LAUNCH、BUY-PULLBACK、BUY-ACCUMULATE、BUY-WHALE
   6. **HOLD-WATCH**（持仓中但 T+7 锁定）：仅记录急跌，不报"立即止损"
   7. **legacy_alert 检查**：跨阈值则推送
   8. 记录 `signals_log`、`recommendations_log`
6. 保存 `state.json`
7. 推送 BUY 类信号到 PushPlus
8. 关闭 playwright

**关键模块调用**：
- `scraper.fetch_market(page)` → 大盘
- `scraper.fetch_item(page, item)` → 个品数据
- `circuit_breaker.check(state)` → 熔断状态
- `indicators.compute_micro(history)` → 短期指标
- `stages.detect_fast(history, indicators)` → 快速阶段判定
- `signals.evaluate_buy(item, indicators, stage, market, fundamentals)` → BUY 信号
- `signals.check_legacy_alerts(item)` → 套牢仓提醒
- `pusher.send_to_all(state['global']['pushplus_tokens'], title, body)` → 推送
- `state.save(state, path)` → 持久化

### 3.3 monitor_slow.py（每整点 1 小时）

**目的**：完整指标计算、SELL 信号评估、跨品种联动、阶段切换

**完整流程**：
1. 加载 state（与 fast 共享同一文件）
2. **跨品种相对强度（RS）计算**：
   - 计算每品种 1H 涨幅 vs 大盘 1H 涨幅
   - 给每品种打 RS 分（>2 强势 / <0.5 弱势）
3. **完整指标**：
   - ma_micro / ma_intraday(12H) / ma_week(7D) / ma_month(30D)
   - 量价共振、momentum_score
   - 波动率（standard deviation）
4. **完整阶段识别**（基于多时间框架）：
   - ACCUMULATION / SHAKEOUT / COILING / MARKUP / DISTRIBUTION / MARKDOWN
   - 检测阶段切换 → 重要事件，推送
5. **SELL 信号评估**（仅当 is_holding）：
   - SELL-DIST、SELL-BREAK、SELL-TP（达到止盈档）、SELL-EMERGENCY
   - 附加 T+7 时机标注（"距可卖时间 X 天"）
6. **基本面过期检查**：whale_signals 是否过期、bias 是否需要降级
7. 复盘所有 BUY 信号（fast 已发出的）→ 写入 shadow_positions 跟踪
8. 保存 state，推送 SELL 类提醒

### 3.4 daily_review.py（每天 23:00）

**目的**：当日复盘 + 影子仓位统计 + 推送

**完整流程**：
1. 加载 state
2. 对每个 item 汇总今日：
   - 开 / 收 / 高 / 低 / 振幅 / 总成交
   - 信号统计（BUY 各类 / SELL 各类 / 推送数）
   - 阶段切换记录
   - 持仓盈亏（仅 position.tiers，legacy 单独）
3. **影子仓位结算**：
   - 7 天前的 BUY 信号 → 与今天价格对比，计算 7 日收益
   - 累计每类信号的胜率、平均收益
4. **总仓位风险面板**：
   - 总成本 / 总市值 / 总浮盈
   - 单品种集中度
   - 已实现盈亏（本月、本年）
5. **明日要点**：每品种关键支撑/阻力、待观察事件
6. **可选**：playwright 截图每个品种 K 线 → 存档至 `screenshots/`
7. 写入 `daily_review_log[]`，砍超过 90 天的旧记录
8. 推送复盘报告到三 token

### 3.5 lib/scraper.py 关键设计

```python
from playwright.sync_api import sync_playwright

class SteamDTScraper:
    def __init__(self, profile_dir):
        self.profile_dir = profile_dir
        self.pw = None
        self.context = None
    
    def __enter__(self):
        self.pw = sync_playwright().start()
        self.context = self.pw.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=True,
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."
        )
        # stealth 注入
        from playwright_stealth import stealth_sync
        page = self.context.pages[0] if self.context.pages else self.context.new_page()
        stealth_sync(page)
        self.page = page
        return self
    
    def __exit__(self, *args):
        self.context.close()
        self.pw.stop()
    
    def fetch_market(self):
        self.page.goto("https://www.steamdt.com")
        self.page.wait_for_timeout(4000)
        text = self.page.inner_text("body")
        # 正则提取 大盘指数 / 涨跌幅
        ...
    
    def fetch_item(self, item):
        self.page.goto(item['url'])
        self.page.wait_for_timeout(6000)
        text = self.page.inner_text("body")
        # 提取 price / today_pct / week_pct / today_volume / stock
        ...
    
    def screenshot_kline(self, item, save_path):
        # 截 K 线 canvas 区域
        kline = self.page.locator("[class*='klinecharts'], [class*='chart-container']").first
        kline.screenshot(path=save_path)
```

### 3.6 lib/signals.py 关键决策树

```python
def evaluate_buy(item, ind, stage, market, fundamentals):
    """
    返回 list of signals (可多个)
    """
    signals = []
    pos = item['position']
    K = item['key_levels']
    T = item['thresholds']
    P = item['history'][-1]['price']
    
    # 仓位已满，不评估 BUY
    if pos['total_qty_pct'] >= 1.0:
        return signals
    
    # === 高优先级：洗盘 ===
    if stage == 'SHAKEOUT':
        if P > min(prices_last_24h) and ind['delta_volume_10m'] > vol_avg * 1.5:
            signals.append({
                'label': 'BUY-WASHOUT',
                'priority': 10,
                'advice': f'庄家洗盘买点，建议加仓 {next_tier_qty}%'
            })
    
    # === 庄家底防守 ===
    whale = next((w for w in fundamentals['whale_signals'] 
                  if not w.get('expired') and item['id'] in w.get('applicable_items', [])), None)
    if whale and abs(P - whale['promised_buy_prices'].get(item['id'], 0)) / P < 0.02:
        signals.append({
            'label': 'BUY-WHALE',
            'priority': 9,
            'advice': f'价格触庄家承诺底 ¥{whale["promised_buy_price"]}，可跟买'
        })
    
    # === 拉升启动 ===
    if stage == 'MARKUP':
        if P > K['resistance_1'] * 1.015 and market['index'] > 1014:
            signals.append({
                'label': 'BUY-LAUNCH',
                'priority': 8,
                'advice': f'拉升突破 R1，建第 {next_tier} 档（{next_tier_qty}%）'
            })
    
    # === 突破回踩（D4）===
    last_c = find_recent_c_signal(item['recommendations_log'], hours=24)
    if last_c and is_pullback_pattern(item['history'], last_c):
        signals.append({
            'label': 'BUY-PULLBACK',
            'priority': 7,
            'advice': f'突破回踩高质量入场，建第 {next_tier} 档'
        })
    
    # === 吸筹试探 ===
    if stage == 'ACCUMULATION':
        if P < ind['ma_week'] * 0.95 and ind['vol_ratio'] < 0.6:
            signals.append({
                'label': 'BUY-ACCUMULATE',
                'priority': 5,
                'advice': '吸筹阶段，可小仓位试探（10-15%）'
            })
    
    return signals


def evaluate_sell(item, ind, stage, ...):
    # 仅当持仓时评估
    # SELL-EMERGENCY > SELL-BREAK > SELL-DIST > SELL-TP
    # 推送时附加：'T+7 时机：距可卖 X 天'
    ...


def check_circuit_breaker(state):
    # 大盘单日 -5% / 3 日 -8% / 个品 -15%
    # 返回 (active: bool, reason: str)
    ...
```

### 3.7 lib/stages.py 阶段识别核心

```python
STAGES = ['ACCUMULATION', 'SHAKEOUT', 'COILING', 'MARKUP', 'DISTRIBUTION', 'MARKDOWN']

def detect_stage(history, indicators):
    """
    基于近 N 天数据识别庄家阶段
    返回 stage label
    """
    prices = [h['price'] for h in history[-144:]]  # 近 1 天
    volumes = [h.get('today_volume', 0) for h in history[-144:]]
    P = prices[-1]
    
    ma_week = indicators['ma_week']
    ma_month = indicators['ma_month']
    
    recent_volatility = std(prices[-72:]) / mean(prices[-72:])
    long_volatility = std(prices[-720:]) / mean(prices[-720:]) if len(prices) >= 720 else recent_volatility
    
    avg_vol = mean(volumes[-72:])
    max_recent_vol = max(volumes[-12:])
    
    # 急跌检测
    if len(prices) > 6:
        recent_drop = (prices[-6] - P) / prices[-6]
        if recent_drop > 0.05 and P > min(prices[-144:-6]):
            return 'SHAKEOUT'
    
    # 蓄力检测（波动率收敛 + 在 ma_week 附近震荡）
    if recent_volatility < long_volatility * 0.5 and abs(P - ma_week) / ma_week < 0.03:
        return 'COILING'
    
    # 拉升检测（突破 + 量放大）
    if P > max(prices[-144:-1]) * 1.01 and max_recent_vol > avg_vol * 2.5:
        return 'MARKUP'
    
    # 吸筹检测（低位 + 低量）
    if P < ma_week * 0.95 and recent_volatility < 0.02 and avg_vol < (mean(volumes[-720:]) if len(volumes) >= 720 else avg_vol) * 0.6:
        return 'ACCUMULATION'
    
    # 派发检测（高位 + 假突破）
    if P > ma_month * 1.05 and detect_false_breakouts(prices, count_window=144) >= 2:
        return 'DISTRIBUTION'
    
    # 下跌检测
    if P < ma_week and ma_week < ma_month and detect_volume_on_drops(prices, volumes):
        return 'MARKDOWN'
    
    return 'UNKNOWN'
```

### 3.8 lib/indicators.py 多时间框架 MA

```python
def compute_indicators(history, frequency_minutes=10):
    prices = [h['price'] for h in history]
    volumes = [h.get('today_volume', 0) for h in history if h.get('today_volume') is not None]
    
    # 各周期对应的 entry 数
    n_micro = max(1, 60 // frequency_minutes)        # 1H
    n_intraday = max(1, 12 * 60 // frequency_minutes) # 12H
    n_week = max(1, 7 * 24 * 60 // frequency_minutes) # 7D
    n_month = max(1, 30 * 24 * 60 // frequency_minutes) # 30D
    
    return {
        'ma_micro':    mean(prices[-n_micro:]) if len(prices) >= n_micro else None,
        'ma_intraday': mean(prices[-n_intraday:]) if len(prices) >= n_intraday else None,
        'ma_week':     mean(prices[-n_week:]) if len(prices) >= n_week else None,
        'ma_month':    mean(prices[-n_month:]) if len(prices) >= n_month else None,
        'momentum_score': compute_momentum(prices),
        'delta_volume_10m': volumes[-1] - volumes[-2] if len(volumes) >= 2 else 0,
        'vol_avg_short': mean(volumes[-6:]) if len(volumes) >= 6 else None,
        'volatility': std(prices[-72:]) / mean(prices[-72:]) if len(prices) >= 72 else None,
    }
```

### 3.9 lib/correlation.py 跨品种联动

```python
def compute_relative_strength(state):
    """每品种 vs 大盘的相对强度"""
    market_change_1h = compute_market_change(state, '1H')
    rs_scores = {}
    for item in state['items']:
        item_change_1h = compute_item_change(item, '1H')
        if abs(market_change_1h) < 0.001:
            rs_scores[item['id']] = 1.0
        else:
            rs_scores[item['id']] = item_change_1h / market_change_1h
    return rs_scores

def detect_sector_movements(state):
    """同系品种领涨跟涨链"""
    # 例如 M4A4 系列：喧嚣、红色 DDPAT、机械工业 等
    sectors = state['global'].get('sector_groups', {})
    for sector_name, item_ids in sectors.items():
        # 找领涨品（RS 最高 + 阶段在 MARKUP）
        leaders = find_leaders(state, item_ids)
        if leaders:
            # 标记同 sector 其他品种为"待跟涨"，下一轮强化扫描
            for follower_id in item_ids:
                if follower_id not in [l['id'] for l in leaders]:
                    mark_follower_watch(state, follower_id)
```

### 3.10 lib/circuit_breaker.py 熔断检测

```python
def check(state):
    market = get_recent_market_changes(state)
    
    # 1. 大盘单日 -5%
    if market['1d_change'] <= -0.05:
        return True, 'MARKET_CRASH_1D'
    
    # 2. 大盘 3 日累计 -8%
    if market['3d_change'] <= -0.08:
        return True, 'MARKET_DECLINE_3D'
    
    # 3. 任一监控品种单日 -15%
    for item in state['items']:
        if get_item_1d_change(item) <= -0.15:
            return True, f'ITEM_CRASH_{item["id"]}'
    
    # 4. 关键词预警（依赖每周 Claude V社更新写入）
    fundamentals = state['global']['fundamentals']
    if fundamentals.get('emergency_keywords_detected'):
        return True, 'EMERGENCY_NEWS'
    
    return False, None

def activate(state, reason):
    state['global']['circuit_breaker'] = {
        'active': True,
        'activated_at': now_iso(),
        'reason': reason,
        'scheduled_review_at': iso_after(hours=4)
    }
    push_emergency_alert(state, reason)

def auto_review(state):
    """每 4 小时检查是否解除"""
    cb = state['global'].get('circuit_breaker')
    if not cb or not cb['active']:
        return
    if now() < parse_iso(cb['scheduled_review_at']):
        return
    # 检查是否大盘恢复（连续 12h 无新跌幅）
    if market_recovered_12h(state):
        deactivate(state)
        push_recovery_alert(state)
```

### 3.11 lib/shadow.py 影子仓位回测

```python
def record_shadow_buy(state, signal, price, time):
    """每次发出 BUY 信号时同步建一个影子仓位"""
    shadow = load_shadow_signals()
    shadow.append({
        'id': uuid(),
        'item_id': signal['item_id'],
        'label': signal['label'],
        'entry_price': price,
        'entry_time': time,
        'realized': False
    })
    save_shadow_signals(shadow)

def evaluate_shadow_positions(state):
    """每天 23:00 评估 7 天前的信号"""
    shadow = load_shadow_signals()
    seven_days_ago = now() - timedelta(days=7)
    for sp in shadow:
        if sp['realized']:
            continue
        if parse_iso(sp['entry_time']) < seven_days_ago:
            current_price = get_current_price(state, sp['item_id'])
            sp['exit_price'] = current_price
            sp['return_pct'] = (current_price - sp['entry_price']) / sp['entry_price']
            sp['realized'] = True
    save_shadow_signals(shadow)

def get_signal_stats():
    """返回每类信号的胜率与平均收益"""
    shadow = load_shadow_signals()
    realized = [s for s in shadow if s['realized']]
    stats = {}
    for label in set(s['label'] for s in realized):
        slabel = [s for s in realized if s['label'] == label]
        stats[label] = {
            'count': len(slabel),
            'avg_return': mean([s['return_pct'] for s in slabel]),
            'win_rate': sum(1 for s in slabel if s['return_pct'] > 0) / len(slabel)
        }
    return stats
```

---

## 四、Claude 部分（详细职责）

### 4.1 Claude 不做的事

❌ 不参与 10min 数据采集
❌ 不参与每小时指标计算
❌ 不参与 BUY/SELL 信号常规判定
❌ 不参与 PushPlus 推送
❌ 不参与日常状态文件读写

**结论**：常规运营 0 token 消耗。

### 4.2 Claude 做的事

#### 4.2.1 每周一次：V 社更新检查（约 5K token）

**触发**：本地脚本检测 `fundamentals.next_check_due` 已过期，自动调用 Claude（通过定时任务）

**Claude 职责**：
1. WebSearch `CS2 update <YYYY-MM> Valve patch notes case skin` 等查询
2. 解读结果，分类影响（new case rotation / Major / 反作弊改进 / 普通修复）
3. 更新 state.global.fundamentals.recent_updates 和 bias
4. 设置 `emergency_keywords_detected` 标记（如发现"ban""policy change"等）

**输出**：写回 state，下次本地脚本运行时自动应用新 bias。

#### 4.2.2 每天 23:30：智能复盘报告（可选；约 3K token）

**触发**：`daily_review.py` 完成数据统计后，可选调用 Claude

**Claude 职责**：
1. 读取本地生成的 daily_review_log 最新一条
2. 用自然语言写出"今日故事"（哪些信号触发、阶段切换、明日要点）
3. 附加：影子仓位胜率、策略漂移分析（最近哪类信号失败率上升）

**输出**：Markdown 复盘报告 + 推送到三 token

如果不想花这个 token，本地脚本也能写"模板化复盘"，只是不如 Claude 写的自然。

#### 4.2.3 ad-hoc：用户主对话提问

**触发场景**：
- 用户报告建仓 / 加仓 / 平仓 → Claude 更新 state.position
- 用户截图微信群庄家消息 → Claude 解读 + 更新 whale_signals
- 用户发 K 线截图问"这是什么形态" → Claude 视觉分析
- 用户问"AK 现在该不该止盈" → Claude 综合 state + 当前价 + 阶段给建议
- 用户想新增监控品种 → Claude 协助提取 K 线 + 设关键位 + 加入 state.items

**Claude 职责**：
1. 读取 state.json 上下文
2. 理解用户问题
3. 给出建议或更新 state
4. 不替用户做交易决策

#### 4.2.4 月度策略迭代（按需；约 10K token）

**触发**：用户主动请求或 shadow_signals 显示某类信号胜率持续下降

**Claude 职责**：
1. 分析过去 30 天 shadow_signals 数据
2. 识别哪类信号不准（如 D1 胜率仅 30%）
3. 提出参数调整建议（提高 D1 阈值 / 增加确认条件）
4. 更新 lib/config.py 中的阈值（用户审核后）

#### 4.2.5 紧急事件分析

**触发**：熔断激活时，本地脚本通知 Claude

**Claude 职责**：
1. WebSearch 当前热点新闻
2. 判断熔断原因（市场情绪 / V 社事件 / 黑天鹅）
3. 推荐应对策略（继续熔断 / 提前解除 / 调整止损线）

### 4.3 Claude 调用频率与成本估算

| 调用场景 | 频率 | 单次 token | 月度 token |
|---|---|---|---|
| 每周 V 社更新 | 4 次/月 | 5K | 20K |
| 每日复盘（可选） | 30 次/月 | 3K | 90K |
| ad-hoc 用户提问 | 视使用 | 5K-20K | 100K-500K |
| 月度策略迭代 | 1 次/月 | 10K | 10K |
| 紧急事件分析 | 罕见 | 10K | 0-10K |
| **合计** | | | **~150K-650K/月** |

对比当前架构（~7-15M/月），节省 **96-99%**。

---

## 五、数据结构（state.json）

### 5.1 顶层结构

```json
{
  "version": 4,
  "global": {
    "pushplus_tokens": [...],
    "frequency_fast_minutes": 10,
    "frequency_slow_minutes": 60,
    "homepage_url": "https://www.steamdt.com",
    "trading_style": "swing_t7_aware",
    "fixed_stop_pct": 0.15,
    "trailing_stop_pct": 0.12,
    "fundamentals": {...},
    "tier_plan": {...},
    "circuit_breaker": {"active": false, ...},
    "portfolio_summary": {...},
    "sector_groups": {
      "M4A4_Series": ["m4a4-buzz-kill-fn", "m4a4-red-ddpat-fn"],
      "AK47_Asiimov_Series": ["ak47-leet-museo-ft"],
      "Gloves": ["driver-gloves-lunar-weave-mw"]
    },
    "cs2_calendar": [...],
    "daily_review_log": [...]
  },
  "items": [
    {
      "id": "...",
      "name": "...",
      "url": "...",
      "tier": "core" | "watchlist" | "deep_pool",
      "phase": "...",
      "current_stage": "ACCUMULATION" | "SHAKEOUT" | ...,
      "key_levels": {...},
      "thresholds": {...},
      "history": [...],         // 最多 13,000 条 (10min × 90 天)
      "highest_observed": ...,
      "lowest_observed": ...,
      "position": {...},        // 新建仓
      "legacy_holding": {...},  // 套牢仓
      "signals_log": [...],     // 最多 720 条
      "recommendations_log": [...],  // 最多 200 条
      "last_signal_pushed": ...,
      "last_signal_time": ...,
      "rs_score_1h": ...,       // 相对强度
      "rs_score_24h": ...
    }
  ]
}
```

### 5.2 history 单条结构（10min 频率下，每条约 200 bytes）

```json
{
  "t": "2026-04-26T01:00:00-07:00",
  "price": 4348.5,
  "today_pct": 1.19,
  "week_pct": -1.14,
  "today_volume": 13,
  "delta_volume_10m": 3,
  "stock": 26605,
  "market_index": 1016.77,
  "market_pct": 0.36
}
```

### 5.3 stage_changes 记录

```json
"stage_changes": [
  {"t": "2026-04-26T01:00:00", "from": "COILING", "to": "MARKUP", "trigger_price": 4400, "_note": "突破 R1 确认"},
  {"t": "2026-04-25T15:00:00", "from": "ACCUMULATION", "to": "COILING", ...}
]
```

### 5.4 daily_kline_<id>.json 长期归档（每日聚合）

```json
{
  "item_id": "m4a4-buzz-kill-fn",
  "daily_bars": [
    {"date": "2026-04-25", "open": 4263, "high": 4348.5, "low": 4249, "close": 4280, "volume": 13, "stage": "COILING"},
    {"date": "2026-04-24", "open": ..., ...}
  ]
}
```

---

## 六、策略核心（信号一览表）

### 6.1 BUY 信号（10min 高频）

| 标签 | 触发阶段 | 关键条件 | 优先级 | 推送时机 |
|---|---|---|---|---|
| **BUY-WASHOUT** | SHAKEOUT | 急跌 ≥5% + 价 > 前 24h 低 + 量放大 | 10 | 立即 |
| **BUY-WHALE** | 任何 | 价格触庄家承诺底 ±2% | 9 | 立即 |
| **BUY-LAUNCH** | MARKUP | P > R1×1.015 + 量价确认 + 大盘 > 1014 | 8 | 立即 |
| **BUY-PULLBACK** | MARKUP | C 信号后回踩 + 缩量 + 反弹 | 7 | 立即 |
| **BUY-ACCUMULATE** | ACCUMULATION | P < ma_week×0.95 + 低量 | 5 | 立即 |

### 6.2 SELL 信号（1H 频率，T+7 时机标注）

| 标签 | 触发阶段 | 关键条件 | 时机说明 |
|---|---|---|---|
| **SELL-EMERGENCY** | 任何 | P < strong_support | T+7 解锁后无条件清仓 |
| **SELL-BREAK** | MARKDOWN | 跌破 ma_week + 放量 | 解锁后立即 |
| **SELL-DIST** | DISTRIBUTION | 高位假突破连续 | 解锁后第一批 |
| **SELL-TP** | MARKUP/DIST | 浮盈 +20/+40/+70 | 解锁后建议分批 |

### 6.3 HOLD-WATCH（提醒不行动）

- 持仓中急跌但 T+7 锁定 → "观察 24h 是否破前低；若未破可继续持有"
- 持仓中阶段切换至 DISTRIBUTION → "顶部信号出现，请关注解锁后处理时机"

### 6.4 LEGACY_ALERT（独立通道）

- 套牢仓价格触 ¥5,000 / ¥5,500 / ¥6,000 / ¥6,500 → 各触发一次

### 6.5 CIRCUIT_BREAKER（熔断）

- 激活时立刻推送，并暂停所有 BUY 信号
- 4h 后自动评估解除条件

---

## 七、风险管理

### 7.1 多层止损

| 层 | 触发 | 当前 M4A4 喧嚣（庄家期内）| 当前 AK 抽象派1337 |
|---|---|---|---|
| 价位止损（庄家底） | P < whale_floor | ¥4,200 | (无庄家) |
| 固定止损 -15% | P < entry × 0.85 | 备用 | ¥1,062.5 |
| 移动止损 -12% | P < peak × 0.88 | 备用 | 持续更新 |
| 强支撑止损 | P < strong_support | ¥3,789 | ¥1,080 |

### 7.2 止盈分档

| 档 | 浮盈率 | 卖出比例 |
|---|---|---|
| TP1 | +20% | 30% |
| TP2 | +40% | 30% |
| TP3 | +70% | 0%（移动止损接管） |

### 7.3 总仓位控制

- 单品种最大仓位：100%（计划仓位）
- 总资金跨品种最大暴露：建议 60%（留 40% 现金应对机会）
- 单笔最大可承受亏损：15% × 该笔仓位
- 集中度警告：单品种占总仓位 > 70% 时推送提醒

---

## 八、5 个增强功能详解

（已在第三章 lib/ 各模块中说明，此处不重复）

1. **跨品种联动 + RS 强度**：lib/correlation.py
2. **总仓位风险面板**：每日复盘自动汇总
3. **关键事件日历**：state.global.cs2_calendar，Claude 每周更新
4. **应急熔断**：lib/circuit_breaker.py
5. **影子仓位回测**：lib/shadow.py

---

## 九、监控容量与历史保留

### 9.1 监控容量推荐

| 频率档 | 推荐上限 | 说明 |
|---|---|---|
| 全部 10 min | 30 品种 | 单一频率监控 |
| 全部 1 hour | 100 品种 | 单一频率监控 |
| **混合三层** | **核心 10 + 观察 30 + 大池 100 = 140** | **推荐方案** |

### 9.2 历史数据保留

| 数据类型 | 频率 | 保留时长 | 单品种大小 |
|---|---|---|---|
| 实时 history | 10 min | 90 天 (13K 条) | ~2 MB |
| 日 K 归档 | 每日 | 永久 | ~40 KB/年 |
| signals_log | 每次扫描 | 720 条（约 5 天）| ~150 KB |
| recommendations_log | 仅信号触发 | 200 条 | ~80 KB |
| daily_review_log | 每天 | 90 天 | ~50 KB |
| shadow_signals | 累积 | 永久 | ~100 KB/年 |

**30 品种总大小**：~60 MB（state.json）+ ~2 MB（每年日 K 归档累计）

---

## 十、部署指南

### 10.1 环境要求

- Windows 10/11
- Python 3.9+ 已安装
- ~100 MB 磁盘空间
- 互联网连接（访问 SteamDT + PushPlus + WebSearch）

### 10.2 一次性部署步骤

1. 克隆/复制项目到 `D:\claude\xuanxiao\`
2. 双击 `setup.bat`（自动 pip install + playwright install chromium）
3. 编辑 `state.json` 配置 PushPlus tokens 和监控品种
4. 首次运行 `python monitor_fast.py`（~5min 慢启动，建立 cookies + 拉历史 K 线）
5. 在 Windows 任务计划程序添加：
   - `run_monitor_fast.bat` 每 10 分钟
   - `run_monitor_slow.bat` 每整点
   - `run_daily_review.bat` 每天 23:00

### 10.3 暂停现有 Claude 定时任务

迁移完成后，到 Cowork 侧边栏 Scheduled 区域：
- 暂停 `m4a4-buzz-kill-monitor`
- 暂停 `cs2-skin-daily-review`
- 保留为备用，可随时恢复

### 10.4 验证清单

- [ ] PushPlus 三 token 都收到测试推送
- [ ] state.json 自动生成 history 条目
- [ ] 阶段识别有输出（不全是 UNKNOWN）
- [ ] 任务计划程序日志无错
- [ ] 第 8 天能看到 ma_week 计算结果
- [ ] 第 31 天能看到 ma_month 计算结果

---

## 十一、维护与升级

### 11.1 何时调用 Claude

| 场景 | Claude 介入方式 |
|---|---|
| 看到陌生 K 线形态 | 截图发主对话 |
| 收到庄家群消息 | 截图发主对话，让 Claude 录入 whale_signals |
| 想增加监控品种 | 主对话说 "新增监控 X" |
| 建仓 / 加仓 / 平仓 | 主对话报告 |
| 调整策略参数 | 主对话讨论 |
| 复盘异常 | 主对话提问 |

### 11.2 何时由本地脚本自动处理

- 每 10min 数据采集 + BUY 信号
- 每整点指标计算 + SELL 信号
- 每天 23:00 复盘
- 熔断检测与解除
- legacy_alert 触发
- 状态文件维护

### 11.3 升级路径

- v2.1：增加 SteamDT API 直接拉历史 K（绕过 DOM 慢爬）
- v2.2：增加 OCR 识别 K 线截图（捕获 canvas 上的 MA 数值）
- v2.3：增加机器学习预测（基于 90 天数据训练简单模型）
- v3.0：多用户支持（多个交易者共享一套监控）

---

## 十二、附录：关键决策汇总

1. **架构**：本地 Python 主导（10min + 1h + daily），Claude 仅按需介入
2. **监控品种**：4 把（M4A4 喧嚣 / AK 抽象派1337 / M4A4 红色 DDPAT / 驾驶手套月色）
3. **频率**：10min 买入扫描 + 1h 卖出评估 + daily 复盘
4. **MA 体系**：micro(1H) / intraday(12H) / week(7D) / month(30D)
5. **6 阶段识别**：ACCUMULATION / SHAKEOUT / COILING / MARKUP / DISTRIBUTION / MARKDOWN
6. **信号体系**：BUY 5 类（10min 推送）+ SELL 4 类（1h 推送）+ 特殊（LEGACY/CIRCUIT/HOLD-WATCH）
7. **止损止盈**：CS2 适配（-15%/-12% 止损 + +20/+40/+70 止盈）
8. **风险控制**：熔断机制 + 总仓位面板 + 集中度警告
9. **学习机制**：影子仓位回测 + 月度策略迭代
10. **历史保留**：90 天 10min + 永久日线归档 + 月度压缩

---

**END OF DOCUMENT**
