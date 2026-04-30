import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, GridState, ItemSummary, ShadowStat, StrategyMeta } from "@/lib/api";
import { fmtPrice, shortName } from "@/lib/format";
import { showToast } from "@/lib/toast";

// 通用卡片
function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div
      className="rounded-[28px] p-8 backdrop-blur-2xl"
      style={{
        background: "rgba(255,255,255,0.65)",
        border: "1px solid rgba(255,255,255,0.35)",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function PhaseSyncDetails() {
  return (
    <>
      <Card>
        <h4 className="text-lg font-medium mb-4">🔄 决策数据流（7 层）</h4>
        <pre className="text-xs leading-relaxed font-mono p-4 rounded-xl bg-black/[0.03] overflow-x-auto">{`每 10 分钟扫描:

  Layer 1  抓数据      → history.append({price, volume, market_index, ...})
  Layer 2  算指标      → MA, momentum, volume_quality, volatility
  Layer 3  识别阶段    → ACCUMULATION / SHAKEOUT / MARKUP / ...
  Layer 4  评估 BUY    → 5 种信号按优先级竞争
  Layer 5  bias 调节   → emergency 屏蔽 / 改 priority + 缩放止损止盈
  Layer 6  去重        → 4 小时窗口内同信号不重推
  Layer 7  仓位上限    → 满仓 / 超预算 → 阻断

  → 推送 PushPlus + 写 signals_log + shadow.record (7 日跟踪)`}</pre>
      </Card>

      <Card>
        <h4 className="text-lg font-medium mb-4">📈 BUY 信号详情</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-[var(--text-tertiary)] uppercase">
              <tr className="border-b border-black/5">
                <th className="text-left py-2 pr-4">信号</th>
                <th className="text-center py-2 px-2">优先级</th>
                <th className="text-left py-2 pl-2">触发条件</th>
              </tr>
            </thead>
            <tbody className="text-[13px]">
              <tr className="border-b border-black/5"><td className="py-2 pr-4 font-medium">BUY-WASHOUT</td><td className="text-center font-mono">10</td><td className="pl-2 text-[var(--text-secondary)]">stage = SHAKEOUT（庄家洗盘急跌但未破前低）</td></tr>
              <tr className="border-b border-black/5"><td className="py-2 pr-4 font-medium">BUY-WHALE</td><td className="text-center font-mono">9</td><td className="pl-2 text-[var(--text-secondary)]">价格距庄家承诺底 ≤ 2% + 庄家信号未过期</td></tr>
              <tr className="border-b border-black/5"><td className="py-2 pr-4 font-medium">BUY-LAUNCH</td><td className="text-center font-mono">8</td><td className="pl-2 text-[var(--text-secondary)]">stage = MARKUP + 突破 R1 × 1.015 + 大盘配合 + 量价共振</td></tr>
              <tr className="border-b border-black/5"><td className="py-2 pr-4 font-medium">BUY-PULLBACK</td><td className="text-center font-mono">7</td><td className="pl-2 text-[var(--text-secondary)]">24h 内 BUY-LAUNCH 后回踩 ±3% + 反弹拐头 + 动能恢复</td></tr>
              <tr><td className="py-2 pr-4 font-medium">BUY-ACCUMULATE</td><td className="text-center font-mono">5</td><td className="pl-2 text-[var(--text-secondary)]">stage = ACCUMULATION + 当前仓位 &lt; 30%（试探仓）</td></tr>
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <h4 className="text-lg font-medium mb-4">🎭 6 阶段庄家识别</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div className="p-3 rounded-xl bg-emerald-50/40"><strong className="text-emerald-700">① ACCUMULATION 吸筹</strong><br/><span className="text-xs text-[var(--text-secondary)]">价格 &lt; 周线 5%+ + 量能持续低迷</span></div>
          <div className="p-3 rounded-xl bg-emerald-50/40"><strong className="text-emerald-700">② SHAKEOUT 洗盘</strong><br/><span className="text-xs text-[var(--text-secondary)]">1H 急跌 -5% 但未破前低（庄家洗散户）</span></div>
          <div className="p-3 rounded-xl bg-amber-50/40"><strong className="text-amber-700">③ COILING 蓄力</strong><br/><span className="text-xs text-[var(--text-secondary)]">波动压缩 + 价格围绕 ma_week ±3%</span></div>
          <div className="p-3 rounded-xl bg-indigo-50/40"><strong className="text-indigo-700">④ MARKUP 拉升</strong><br/><span className="text-xs text-[var(--text-secondary)]">突破 24h 高 0.5%+ + 量价共振</span></div>
          <div className="p-3 rounded-xl bg-rose-50/40"><strong className="text-rose-700">⑤ DISTRIBUTION 派发</strong><br/><span className="text-xs text-[var(--text-secondary)]">价格 &gt; 月线 5% + 多次假突破</span></div>
          <div className="p-3 rounded-xl bg-rose-50/40"><strong className="text-rose-700">⑥ MARKDOWN 杀跌</strong><br/><span className="text-xs text-[var(--text-secondary)]">价格 &lt; 周 &lt; 月线 + 24h 跌 -3%+</span></div>
        </div>
      </Card>

      <Card>
        <h4 className="text-lg font-medium mb-3">🎚️ Bias 调节器（A + B 增强）</h4>
        <p className="text-sm text-[var(--text-secondary)] mb-3">
          LLM 看新闻判定 bias → 实时影响 BUY 优先级 + 止损止盈阈值。
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-[var(--text-tertiary)] uppercase">
              <tr className="border-b border-black/5">
                <th className="text-left py-2 pr-4">Bias</th>
                <th className="text-center py-2 px-2">BUY 优先级</th>
                <th className="text-center py-2 px-2">止损乘数</th>
                <th className="text-center py-2 px-2">止盈乘数</th>
                <th className="text-left py-2 pl-2">效果</th>
              </tr>
            </thead>
            <tbody className="text-[13px] font-mono">
              <tr className="border-b border-black/5"><td className="py-2 pr-4">positive_with_whale_buy</td><td className="text-center text-emerald-600">+1</td><td className="text-center">×1.10</td><td className="text-center text-emerald-600">×1.30</td><td className="pl-2 text-xs">让利润奔跑</td></tr>
              <tr className="border-b border-black/5"><td className="py-2 pr-4">positive</td><td className="text-center text-emerald-600">+1</td><td className="text-center">×1.00</td><td className="text-center text-emerald-600">×1.10</td><td className="pl-2 text-xs">略偏多</td></tr>
              <tr className="border-b border-black/5"><td className="py-2 pr-4">neutral</td><td className="text-center">0</td><td className="text-center">×1.00</td><td className="text-center">×1.00</td><td className="pl-2 text-xs">默认</td></tr>
              <tr className="border-b border-black/5"><td className="py-2 pr-4">negative</td><td className="text-center text-rose-600">-1</td><td className="text-center text-rose-600">×0.70</td><td className="text-center text-rose-600">×0.80</td><td className="pl-2 text-xs">收紧防守</td></tr>
              <tr><td className="py-2 pr-4">emergency</td><td className="text-center text-rose-600 font-bold">屏蔽</td><td className="text-center text-rose-600">×0.50</td><td className="text-center text-rose-600">×0.60</td><td className="pl-2 text-xs">紧急清仓</td></tr>
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

function RsiDetails() {
  return (
    <>
      <Card>
        <h4 className="text-lg font-medium mb-4">📊 RSI 公式</h4>
        <pre className="text-xs leading-relaxed font-mono p-4 rounded-xl bg-black/[0.03] overflow-x-auto">{`RSI = 100 − 100 / (1 + RS)
RS  = 平均涨幅(N 天) / 平均跌幅(N 天)

RSI < 30  → 超卖（动能耗尽）→ 触发 BUY
RSI > 70  → 超买（动能枯竭）→ 通常出场
我们用 N=14（业界标准），日线降采样后计算`}</pre>
      </Card>
      <Card>
        <h4 className="text-lg font-medium mb-4">🚦 6 道闸门（任一不过 → 不触发）</h4>
        <ol className="text-sm space-y-2 list-decimal pl-5">
          <li>不在满仓（total_qty_pct &lt; 1.0）</li>
          <li>不在禁止阶段（MARKUP / DISTRIBUTION / MARKDOWN）</li>
          <li>历史足够（≥ 30 天数据）</li>
          <li>庄家不活跃（无活跃庄家信号）</li>
          <li><strong>RSI(14) &lt; 30</strong>（核心触发）</li>
          <li>距月线均价 ≥ 3%（覆盖 1% 卖出手续费 + 留 2% 利润）</li>
        </ol>
      </Card>
      <Card>
        <h4 className="text-lg font-medium mb-4">⚙️ 关键参数</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm font-mono">
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">rsi_period:</span> 14</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">rsi_oversold:</span> 30</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">min_history_days:</span> 30</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">min_distance_to_mean:</span> 0.03 (3%)</div>
        </div>
      </Card>
    </>
  );
}

function MrDetails() {
  return (
    <>
      <Card>
        <h4 className="text-lg font-medium mb-4">📊 z-score 公式</h4>
        <pre className="text-xs leading-relaxed font-mono p-4 rounded-xl bg-black/[0.03] overflow-x-auto">{`z = (P − μ) / σ

  μ = 20 日均价
  σ = 20 日标准差
  P = 当前价

z = -2  →  当前价比 20 日均价低 2 个标准差
            （统计上罕见，约 5% 概率事件）
z < -2  →  触发 MR-OVERSOLD`}</pre>
      </Card>
      <Card>
        <h4 className="text-lg font-medium mb-4">🚦 6 道闸门</h4>
        <ol className="text-sm space-y-2 list-decimal pl-5">
          <li>不在满仓</li>
          <li>不在禁止阶段（MARKUP / DISTRIBUTION / MARKDOWN）</li>
          <li>历史足够（≥ 40 天，因为 σ 计算需更多样本）</li>
          <li>庄家不活跃</li>
          <li><strong>z-score ≤ -2.0</strong>（核心触发）</li>
          <li>距均线绝对距离 ≥ 5%（避免低波动品种触发过敏）</li>
        </ol>
      </Card>
      <Card>
        <h4 className="text-lg font-medium mb-4">⚙️ 关键参数</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm font-mono">
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">lookback_days:</span> 20</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">z_score_threshold:</span> -2.0</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">min_history_days:</span> 40</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">min_distance_to_mean:</span> 0.05 (5%)</div>
        </div>
      </Card>
      <Card style={{ background: "rgba(99,102,241,0.04)", border: "1px solid rgba(99,102,241,0.18)" }}>
        <h4 className="text-lg font-medium mb-3">💡 与 RSI 战法的差异</h4>
        <ul className="text-sm space-y-2 list-disc pl-5 text-[var(--text-secondary)]">
          <li><strong>RSI</strong> 看动能（涨跌幅平滑）→ 反应慢半拍但更稳</li>
          <li><strong>z-score</strong> 看价格分布 → 反应快但对低波动品种不灵</li>
          <li>缓慢阴跌：z-score 优（等到统计极端才入，避免接刀）</li>
          <li>剧烈暴跌：z-score 优（RSI 平滑滞后）</li>
          <li>温和震荡：两者基本相当</li>
        </ul>
      </Card>
    </>
  );
}

function GridDetails({ items }: { items: ItemSummary[] }) {
  return (
    <>
      <Card>
        <h4 className="text-lg font-medium mb-4">📐 网格机制</h4>
        <pre className="text-xs leading-relaxed font-mono p-4 rounded-xl bg-black/[0.03] overflow-x-auto">{`中心 = MA30（自动锚定，漂移 ≥10% 滑动更新）

   +3 档 (+15%)  ← 卖出区
   +2 档 (+10%)
   +1 档 (+ 5%)
[ 中心 C ]
   -1 档 (- 5%)  ← 买入区
   -2 档 (-10%)
   -3 档 (-15%)

操作：
  价格触 -N 档 + 该档无货 → 买 1 把
  价格回到买入价 +5% + T+7 已解锁 → 卖

资金分配：
  半仓 (50%) 平均分到 3 个买入档（每档 ~16%）
  另一半留作应急储备（z < -2.5σ 时一次性加仓）

突破退出：
  价格距中心 > ±20% → 自动退出，需手动重启`}</pre>
      </Card>
      <Card>
        <h4 className="text-lg font-medium mb-4">⚙️ 关键参数</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm font-mono">
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">grid_step_pct:</span> 0.05 (5%)</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">grid_levels:</span> 3 上下各</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">max_pos_per_level:</span> 0.10</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">breakout_exit_pct:</span> 0.20 (±20%)</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">emergency_zscore:</span> -2.5</div>
          <div className="p-2 rounded bg-black/[0.03]"><span className="text-[var(--text-tertiary)]">tplus7_days:</span> 7</div>
        </div>
      </Card>
      <GridPanel items={items} />
    </>
  );
}

function GridPanel({ items }: { items: ItemSummary[] }) {
  const [states, setStates] = useState<Record<string, GridState | null>>({});
  const [busy, setBusy] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let alive = true;
    (async () => {
      const entries = await Promise.all(
        items.map(async (it) => [it.id, (await api.gridState(it.id))?.grid_state || null] as const)
      );
      if (!alive) return;
      const out: Record<string, GridState | null> = {};
      entries.forEach(([id, gs]) => { out[id] = gs; });
      setStates(out);
    })();
    return () => { alive = false; };
  }, [items, refreshTick]);

  async function toggle(id: string, active: boolean) {
    setBusy(true);
    const r = await api.toggleGrid(id, active);
    setBusy(false);
    if (r.ok) {
      showToast(active ? "✓ 网格已启用" : "✓ 网格已关闭");
      setRefreshTick((x) => x + 1);
    } else {
      showToast("失败：" + r.error, "error");
    }
  }
  async function restart(id: string) {
    if (!confirm("重启网格会重新锚定中心价（用当前 ma_30）。原有持仓档信息会被清除。继续？")) return;
    setBusy(true);
    const r = await api.restartGrid(id);
    setBusy(false);
    if (r.ok) {
      showToast("✓ 网格已重启");
      setRefreshTick((x) => x + 1);
    } else {
      showToast("失败：" + r.error, "error");
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-medium">🎯 按品种启用</h4>
        <span className="text-xs text-[var(--text-tertiary)]">
          启用后 shadow 跟跑；切为 active 则真实推送
        </span>
      </div>
      <p className="text-xs text-[var(--text-secondary)] mb-4">
        网格策略需要逐个品种启用。启用时自动用当前 30 日均价作为网格中心。突破 ±20% 自动退出，需手动重启。
      </p>
      <div className="space-y-3">
        {items.length === 0 && (
          <div className="text-sm text-[var(--text-tertiary)]">尚无监控品种</div>
        )}
        {items.map((it) => {
          const gs = states[it.id];
          const enabled = gs && gs.active;
          const exited = gs && gs.exited;
          let badge: React.ReactNode;
          if (!gs) badge = <span className="pill" style={{ fontSize: 11 }}>未启用</span>;
          else if (exited) badge = <span className="pill amber" style={{ fontSize: 11 }}>已退出（突破）</span>;
          else if (enabled) badge = <span className="pill green" style={{ fontSize: 11 }}>启用中</span>;
          else badge = <span className="pill" style={{ fontSize: 11 }}>已停用</span>;

          return (
            <div key={it.id} className="p-4 rounded-2xl border border-black/5 bg-white/60">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <span className="font-medium">{it.short_name || it.name}</span>{" "}
                  {badge}
                </div>
                <div className="flex items-center gap-2">
                  {enabled ? (
                    <button
                      disabled={busy}
                      onClick={() => toggle(it.id, false)}
                      className="text-xs px-3 py-1.5 rounded-lg bg-rose-50 text-rose-700 hover:bg-rose-100 transition disabled:opacity-50"
                    >
                      关闭网格
                    </button>
                  ) : (
                    <button
                      disabled={busy}
                      onClick={() => toggle(it.id, true)}
                      className="text-xs px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition disabled:opacity-50"
                    >
                      启用网格
                    </button>
                  )}
                  {exited && (
                    <button
                      disabled={busy}
                      onClick={() => restart(it.id)}
                      className="text-xs px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition disabled:opacity-50"
                    >
                      重启
                    </button>
                  )}
                </div>
              </div>
              {gs?.center_price && (
                <div className="text-xs text-[var(--text-tertiary)] mt-1">
                  中心 ¥{gs.center_price.toFixed(0)} · 档距 {(gs.step_pct * 100).toFixed(0)}% · {gs.levels} 档/边 ·
                  应急储备 {gs.reserve_used ? "已动用" : "未动用"}
                </div>
              )}
              {gs?.positions?.length ? (
                <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                  {gs.positions.map((pos) => {
                    const target = gs.center_price * (1 + pos.level * gs.step_pct);
                    const held = pos.qty_pieces > 0;
                    const unlocked = pos.unlock_time && new Date(pos.unlock_time) <= new Date();
                    const cellBg = held
                      ? unlocked
                        ? "bg-emerald-50 border-emerald-200"
                        : "bg-amber-50 border-amber-200"
                      : "bg-black/[0.02] border-black/5";
                    return (
                      <div key={pos.level} className={`p-2 rounded-lg border ${cellBg}`}>
                        <div className="font-medium">L{pos.level}</div>
                        <div className="text-[var(--text-tertiary)]">目标 ¥{target.toFixed(0)}</div>
                        {held ? (
                          <div className="mt-1">
                            <div>持仓 {pos.qty_pieces} 把 @{fmtPrice(pos.entry_price)}</div>
                            <div className={unlocked ? "text-emerald-700" : "text-amber-700"}>
                              {unlocked ? "✓ 已解锁" : "⏳ T+7 锁定中"}
                            </div>
                          </div>
                        ) : (
                          <div className="text-[var(--text-tertiary)]">未持仓</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function StrategyDetail({
  s,
  active,
  stats,
  items,
  onSwitch,
}: {
  s: StrategyMeta;
  active: string;
  stats: ShadowStat | undefined;
  items: ItemSummary[];
  onSwitch: () => void;
}) {
  const isActive = s.id === active;
  return (
    <>
      <Card
        style={{
          background: "linear-gradient(135deg, rgba(99,102,241,0.08), rgba(236,72,153,0.04))",
          border: "1px solid rgba(99,102,241,0.18)",
        }}
      >
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h3 className="text-2xl font-semibold tracking-tight text-gradient">{s.name}</h3>
              {isActive && <span className="pill green" style={{ fontSize: 11 }}>✓ 当前启用</span>}
              <span className={`pill ${s.status === "stable" ? "green" : "amber"}`} style={{ fontSize: 11 }}>
                {s.status || "—"}
              </span>
              <span className="pill" style={{ fontSize: 11 }}>v{s.version || "—"}</span>
            </div>
            <div className="text-sm text-[var(--text-secondary)]">{s.tagline || ""}</div>
          </div>
          <div>
            {isActive ? (
              <button disabled className="px-5 py-2.5 rounded-full bg-emerald-100 text-emerald-700 text-sm font-medium cursor-default">
                已是当前策略
              </button>
            ) : (
              <button
                onClick={onSwitch}
                className="px-5 py-2.5 rounded-full bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition"
              >
                切换为当前策略
              </button>
            )}
          </div>
        </div>
        <p className="text-sm leading-relaxed text-[var(--text-secondary)] mt-4">{s.description || ""}</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4 text-xs">
          <div className="p-3 rounded-xl bg-emerald-50/60">
            <span className="text-emerald-700 font-medium">✓ 适用场景</span><br />
            <span className="text-[var(--text-secondary)]">{s.best_for || "—"}</span>
          </div>
          <div className="p-3 rounded-xl bg-amber-50/60">
            <span className="text-amber-700 font-medium">⚠ 弱势场景</span><br />
            <span className="text-[var(--text-secondary)]">{s.weak_for || "—"}</span>
          </div>
        </div>
      </Card>

      {stats ? (
        <Card>
          <h4 className="text-lg font-medium mb-4">📊 Shadow 表现（已评估的真实数据）</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-[var(--text-tertiary)]">已评估</div>
              <div className="text-2xl font-semibold mt-1">{stats.count}</div>
              <div className="text-xs text-[var(--text-tertiary)]">笔</div>
            </div>
            <div>
              <div className="text-xs text-[var(--text-tertiary)]">胜率</div>
              <div className={`text-2xl font-semibold mt-1 ${stats.win_rate >= 0.5 ? "text-emerald-600" : "text-rose-600"}`}>
                {(stats.win_rate * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-[var(--text-tertiary)]">平均收益</div>
              <div className={`text-2xl font-semibold mt-1 ${stats.avg_return >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                {(stats.avg_return * 100).toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-[var(--text-tertiary)]">最大单笔</div>
              <div className="text-2xl font-semibold mt-1 text-emerald-600">
                {(stats.max_return * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </Card>
      ) : (
        <Card>
          <h4 className="text-lg font-medium mb-2">📊 Shadow 表现</h4>
          <div className="text-sm text-[var(--text-tertiary)]">
            尚无已评估的 shadow 数据。每条 BUY 信号触发后会记一笔，7 天后自动评估收益。
          </div>
        </Card>
      )}

      {!!s.signals?.length && (
        <Card>
          <h4 className="text-lg font-medium mb-3">🎯 信号类型</h4>
          <div className="flex flex-wrap gap-2">
            {s.signals.map((sig) => (
              <code key={sig} className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 text-sm font-mono">
                {sig}
              </code>
            ))}
          </div>
        </Card>
      )}

      {s.id === "phase-sync-v1" && <PhaseSyncDetails />}
      {s.id === "rsi-reversion-v1" && <RsiDetails />}
      {s.id === "mean-reversion-v1" && <MrDetails />}
      {s.id === "grid-half-v1" && <GridDetails items={items} />}
    </>
  );
}

export default function Strategy() {
  const qc = useQueryClient();
  const strategies = useQuery({ queryKey: ["strategies"], queryFn: () => api.strategies() });
  const items = useQuery({ queryKey: ["items"], queryFn: () => api.items() });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // 默认选当前 active
  useEffect(() => {
    if (!selectedId && strategies.data?.active) setSelectedId(strategies.data.active);
  }, [strategies.data, selectedId]);

  // tab 切换时触发 fade-in 动画
  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    panel.classList.remove("fading-in");
    void panel.offsetWidth;
    panel.classList.add("fading-in");
    const t = setTimeout(() => panel.classList.remove("fading-in"), 800);
    return () => clearTimeout(t);
  }, [selectedId]);

  async function setActive(id: string) {
    if (!confirm(`确认切换为「${id}」？\n\n切换后真实推送会用这个策略，原策略仍会跟跑 shadow 用于对比。`)) return;
    const r = await api.setActiveStrategy(id);
    if (r.ok) {
      showToast("✓ 已切换 active 策略");
      qc.invalidateQueries({ queryKey: ["strategies"] });
    } else {
      showToast("切换失败：" + r.error, "error");
    }
  }

  if (!strategies.data) {
    return (
      <div style={{ paddingTop: 100 }}>
        <section className="py-12 px-6 max-w-6xl mx-auto">
          <h2 className="text-4xl font-semibold tracking-tight mb-3">策略管控</h2>
          <div className="text-center py-12 text-[var(--text-tertiary)]">加载中...</div>
        </section>
      </div>
    );
  }

  const data = strategies.data;
  const sel = data.strategies.find((x) => x.id === selectedId);
  const stats = selectedId ? data.performance?.[selectedId] : undefined;

  return (
    <div style={{ paddingTop: 100 }}>
      <section className="py-12 px-6 max-w-6xl mx-auto">
        <h2 className="text-4xl font-semibold tracking-tight mb-3">策略管控</h2>
        <p className="text-[var(--text-secondary)] mb-8">
          点击 Tab 切换查看不同策略的详细信息。绿点 ●&nbsp;= 当前 active 策略（实际推送用此），其他策略在 shadow 模式跟跑。
        </p>

        <div className="mb-8 overflow-x-auto">
          <div className="inline-flex p-1.5 rounded-full bg-black/[0.04] gap-1">
            {data.strategies.map((s) => (
              <button
                key={s.id}
                className={`strategy-tab ${selectedId === s.id ? "selected" : ""}`}
                onClick={() => setSelectedId(s.id)}
              >
                {shortName(s.name)}
                {s.id === data.active && (
                  <span className="active-dot" title="当前推送策略" />
                )}
              </button>
            ))}
          </div>
        </div>

        <div ref={panelRef} className="strategy-detail-panel space-y-6">
          {sel && (
            <StrategyDetail
              s={sel}
              active={data.active}
              stats={stats}
              items={items.data?.items ?? []}
              onSwitch={() => setActive(sel.id)}
            />
          )}
        </div>
      </section>
    </div>
  );
}
