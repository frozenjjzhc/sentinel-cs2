# v2.0.0 — 多策略 + 视觉品牌重塑

## 重大变更
- **多策略架构**：从单策略升级为 4 策略并行 — `phase-sync-v1`（趋势同步）/ `rsi-reversion-v1`（RSI 反转）/ `mean-reversion-v1`（均值回归）/ `grid-half-v1`（半网格）。Active 策略实际推送，其他 shadow 跟跑做对比回测。
- **state schema v3 → v4**：自动迁移，老用户首次启动会补全新字段。
- **视觉品牌重塑**：苹果式 Liquid Glass、战术 UI 网格、3D AK-47 SVG、WebGL Doppler 着色器，整套首页视觉重做。

## 新增
- 策略管控页：tab 选择 + 单策略详情面板 + 实时 shadow 对比 + 淡入淡出动画
- 真实 Steam 饰品图：自动从 SteamDT 抓取 `img.zbt.com` 主图，概览卡和设置页饰品列表都显示
- 总预算（`planned_total_cny`）→ 仓位百分比、可用余额计算
- `qty_pieces`：精确成本计算（修复了把 `qty_pct` 当数量的 bug）
- 大庄家信号开关：设置页一键忽略 BUY-WHALE
- 网格策略 T+7 锁感知 + 阶梯式分批
- 嵌入式调度器：monitor 与 API 同进程，`Sentinel.bat` 一键启动
- AI 复盘页（Phase 1/3/4）：新闻分类 + 每日复盘 + 参数提案
- K 线时间轴改为时间戳定位 + 鼠标悬停 tooltip + 增量成交量
- 多个新 API 端点（图片覆盖、预算、whale 开关、策略切换、网格控制）

## 修复
- 概览页"监控品种"数字反映真实饰品数（不再硬编码）
- `BudgetRequest` NameError（Pydantic 模型定义顺序）
- Steam News 抓取增加 3 次指数退避重试，错误透传到 UI

## 升级须知
- 第一次启动会**自动迁移** `m4a4_buzz_kill_state.json`（v3 → v4）。建议升级前手动备份。
- 已存在的 `image_url` 字段不会被覆盖；可在设置页"换图"手动覆盖。
- PushPlus / LLM 的密钥设置无需变更。

---

完整变更日志：[CHANGELOG.md](https://github.com/frozenjjzhc/sentinel-cs2/blob/main/CHANGELOG.md)
