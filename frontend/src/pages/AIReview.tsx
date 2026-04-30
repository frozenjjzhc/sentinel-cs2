import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { fmtPrice } from "@/lib/format";
import { showToast } from "@/lib/toast";

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-[28px] p-8 backdrop-blur-2xl"
      style={{
        background: "rgba(255,255,255,0.65)",
        border: "1px solid rgba(255,255,255,0.35)",
      }}
    >
      {children}
    </div>
  );
}

export default function AIReview() {
  const qc = useQueryClient();
  const stats = useQuery({ queryKey: ["shadow-stats"], queryFn: () => api.shadowStats() });
  const recent = useQuery({ queryKey: ["shadow-recent"], queryFn: () => api.shadowRecent(10) });
  const reviews = useQuery({ queryKey: ["llm-reviews"], queryFn: () => api.llmReviews(10) });
  const proposals = useQuery({ queryKey: ["proposals"], queryFn: () => api.proposals() });

  const labels = Object.keys(stats.data?.stats ?? {});
  const totalCount = labels.reduce((s, k) => s + (stats.data!.stats[k].count || 0), 0);
  const allReturns = labels.flatMap((k) =>
    Array(stats.data!.stats[k].count).fill(stats.data!.stats[k].avg_return)
  );
  const totalAvg = allReturns.length ? allReturns.reduce((a, b) => a + b, 0) / allReturns.length : 0;

  async function generateReview() {
    const r = await api.generateDailyReview();
    if (r.ok) {
      showToast("✓ 复盘已生成");
      qc.invalidateQueries({ queryKey: ["llm-reviews"] });
    } else showToast("生成失败：" + r.error, "error");
  }

  async function generateProposals() {
    const r = await api.generateProposals();
    if (r.ok) {
      const n = (r.data.proposals || []).length;
      showToast(n ? `✓ 生成 ${n} 条新提案` : "✓ AI 认为暂无需调整");
      qc.invalidateQueries({ queryKey: ["proposals"] });
    } else showToast("生成失败：" + r.error, "error");
  }

  async function applyProp(id: string) {
    if (!confirm("确认应用这条提案？原值会自动备份。")) return;
    const r = await api.applyProposal(id);
    if (r.ok) {
      showToast("✓ 已应用");
      qc.invalidateQueries({ queryKey: ["proposals"] });
    } else showToast("失败：" + r.error, "error");
  }
  async function rejectProp(id: string) {
    const r = await api.rejectProposal(id);
    if (r.ok) {
      showToast("已拒绝");
      qc.invalidateQueries({ queryKey: ["proposals"] });
    } else showToast("失败：" + r.error, "error");
  }

  return (
    <div style={{ paddingTop: 100 }}>
      <section className="py-12 px-6 max-w-6xl mx-auto">
        <h2 className="text-4xl font-semibold tracking-tight mb-3">AI 复盘 / 策略迭代</h2>
        <p className="text-[var(--text-secondary)] mb-10">
          影子信号回测、AI 每日评论、参数调整提案 — 所有数据驱动的迭代都在这里。
        </p>

        <div className="space-y-10">
          {/* Shadow */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">📈 Shadow 影子信号回测</h3>
              <span className="text-xs text-[var(--text-tertiary)]">
                每条 BUY 推送 → 7 天后自动评估实际收益
              </span>
            </div>
            <div className="text-sm mb-4">
              {stats.data ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-[var(--text-tertiary)]">已评估笔数</div>
                    <div className="text-2xl font-semibold">{totalCount}</div>
                  </div>
                  <div>
                    <div className="text-xs text-[var(--text-tertiary)]">待评估（&lt; 7 天）</div>
                    <div className="text-2xl font-semibold">{stats.data.pending || 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-[var(--text-tertiary)]">综合平均收益</div>
                    <div
                      className={`text-2xl font-semibold ${
                        totalAvg >= 0 ? "text-emerald-600" : "text-rose-600"
                      }`}
                    >
                      {totalCount ? (totalAvg * 100).toFixed(2) + "%" : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-[var(--text-tertiary)]">信号种类</div>
                    <div className="text-2xl font-semibold">{labels.length}</div>
                  </div>
                </div>
              ) : (
                <span className="text-rose-600">无法读取 shadow 数据</span>
              )}
            </div>
            <div className="text-sm font-medium mb-2">分类型胜率</div>
            <div className="overflow-x-auto">
              {labels.length === 0 ? (
                <div className="text-sm text-[var(--text-tertiary)]">
                  还没积累足够数据。每条 BUY 推送会自动建一个影子仓位，7 天后自动评估。
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-xs text-[var(--text-tertiary)] uppercase">
                    <tr className="border-b border-black/5">
                      <th className="text-left py-2 pr-4">信号类型</th>
                      <th className="text-right py-2 px-2">笔数</th>
                      <th className="text-right py-2 px-2">胜率</th>
                      <th className="text-right py-2 px-2">平均收益</th>
                      <th className="text-right py-2 px-2">最大</th>
                      <th className="text-right py-2 pl-2">最小</th>
                    </tr>
                  </thead>
                  <tbody>
                    {labels.map((label) => {
                      const s = stats.data!.stats[label];
                      const winColor =
                        s.win_rate >= 0.6
                          ? "text-emerald-600"
                          : s.win_rate < 0.4
                          ? "text-rose-600"
                          : "text-slate-700";
                      const avgColor = s.avg_return >= 0 ? "text-emerald-600" : "text-rose-600";
                      return (
                        <tr key={label} className="border-b border-black/5 hover:bg-black/[0.02]">
                          <td className="py-2 pr-4 font-medium">{label}</td>
                          <td className="text-right py-2 px-2">{s.count}</td>
                          <td className={`text-right py-2 px-2 font-medium ${winColor}`}>
                            {(s.win_rate * 100).toFixed(0)}%
                          </td>
                          <td className={`text-right py-2 px-2 font-medium ${avgColor}`}>
                            {(s.avg_return * 100).toFixed(2)}%
                          </td>
                          <td className="text-right py-2 px-2 text-emerald-600">
                            {(s.max_return * 100).toFixed(1)}%
                          </td>
                          <td className="text-right py-2 pl-2 text-rose-600">
                            {(s.min_return * 100).toFixed(1)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            <div className="text-sm font-medium mt-6 mb-2">最近 10 笔已评估</div>
            <div className="space-y-2 text-sm">
              {(recent.data?.shadows ?? []).length === 0 ? (
                <div className="text-[var(--text-tertiary)]">暂无已评估记录</div>
              ) : (
                recent.data!.shadows.map((s) => {
                  const r = s.return_7d_pct || 0;
                  const color = r >= 0 ? "text-emerald-600" : "text-rose-600";
                  const date = (s.exit_time || "").slice(0, 10);
                  return (
                    <div
                      key={s.id}
                      className="flex items-center justify-between p-3 rounded-xl bg-black/[0.02]"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="font-medium">
                          {s.label} · {s.item_id}
                        </div>
                        <div className="text-xs text-[var(--text-tertiary)]">
                          入 {fmtPrice(s.entry_price)} → 出 {fmtPrice(s.exit_price)} · {date}
                        </div>
                      </div>
                      <div className={`font-mono font-semibold ${color}`}>
                        {(r * 100).toFixed(2)}%
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </Card>

          {/* AI 复盘 */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">📝 AI 每日复盘评论</h3>
              <button
                onClick={generateReview}
                className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-medium hover:bg-indigo-100 transition"
              >
                立即生成一份
              </button>
            </div>
            <div className="space-y-3">
              {(reviews.data?.reviews ?? []).length === 0 ? (
                <div className="text-sm text-[var(--text-tertiary)]">
                  还没有任何 AI 复盘。在设置页勾选「每日复盘评论」+ 配 LLM key，或者点上方「立即生成一份」。
                </div>
              ) : (
                reviews.data!.reviews.map((r, i) => (
                  <details
                    key={i}
                    open={i === 0}
                    className="rounded-2xl border border-black/5 bg-white/60"
                  >
                    <summary className="cursor-pointer p-4 flex items-center justify-between">
                      <div className="font-medium">{r.date || (r.ts || "").slice(0, 10)} 复盘</div>
                      <span className="text-xs text-[var(--text-tertiary)]">{r.model}</span>
                    </summary>
                    <div className="px-4 pb-4 text-sm leading-relaxed text-[var(--text-secondary)] whitespace-pre-wrap">
                      {r.text || ""}
                    </div>
                  </details>
                ))
              )}
            </div>
            <div className="text-xs text-[var(--text-tertiary)] mt-3">
              默认每晚 23:00 由 daily_review.py 自动生成（需在设置里勾选「每日复盘评论」）。
            </div>
          </Card>

          {/* 提案 */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">⚙️ 参数调整提案</h3>
              <button
                onClick={generateProposals}
                className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-medium hover:bg-indigo-100 transition"
              >
                立即生成一批
              </button>
            </div>
            <div className="text-xs text-[var(--text-tertiary)] mb-4">
              AI 看 shadow 30 天数据 → 提议调整 thresholds（止损/止盈/D1 距离/最小成交量等）。
              <strong>需要至少 5 条 shadow 评估样本</strong>才会有提案。每条都需你手动点 ✅ 应用 / ❌ 拒绝。
            </div>
            <div className="space-y-3">
              {(proposals.data?.proposals ?? []).length === 0 ? (
                <div className="text-sm text-[var(--text-tertiary)]">
                  尚无提案。点上方「立即生成一批」试一下（需要 shadow 已评估 ≥5 笔）。
                </div>
              ) : (
                proposals.data!.proposals.map((p) => {
                  const dir = +p.proposed_value > +p.current_value ? "↑ 放宽" : "↓ 收紧";
                  const dirColor =
                    +p.proposed_value > +p.current_value ? "text-emerald-600" : "text-amber-600";
                  // 作用域显示：global / 策略名 / 品种
                  const scopeLabel =
                    p.scope === "strategy"
                      ? `🎯 策略 · ${p.strategy_id || "?"}`
                      : p.scope === "item"
                      ? `📦 品种 · ${p.item_id || "?"}`
                      : "🌐 全局";
                  // 高亮策略提案：紫底
                  const cardCls =
                    p.scope === "strategy"
                      ? "rounded-2xl p-4 border border-indigo-200 bg-indigo-50/40"
                      : "rounded-2xl p-4 border border-black/5 bg-white/60";
                  return (
                    <div key={p.id} className={cardCls}>
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="font-medium">{p.field}</span>
                            <span className="text-xs text-[var(--text-tertiary)]">
                              {scopeLabel}
                            </span>
                            {p.status === "pending" && (
                              <span className="pill amber" style={{ fontSize: 11 }}>
                                待审批
                              </span>
                            )}
                            {p.status === "applied" && (
                              <span className="pill green" style={{ fontSize: 11 }}>
                                已应用
                              </span>
                            )}
                            {p.status === "rejected" && (
                              <span
                                className="pill"
                                style={{ fontSize: 11, background: "rgba(0,0,0,0.06)", color: "#6E6E73" }}
                              >
                                已拒绝
                              </span>
                            )}
                          </div>
                          <div className="font-mono text-sm">
                            <span className="text-[var(--text-tertiary)]">{p.current_value}</span>
                            <span className={`${dirColor} mx-2`}>→ {dir} →</span>
                            <span className="font-semibold">{p.proposed_value}</span>
                          </div>
                        </div>
                        <div className="text-xs text-[var(--text-tertiary)] whitespace-nowrap">
                          置信 {(p.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div className="text-sm text-[var(--text-secondary)] mb-3">💡 {p.rationale}</div>
                      {p.status === "pending" ? (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => applyProp(p.id)}
                            className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-700 transition"
                          >
                            ✓ 应用
                          </button>
                          <button
                            onClick={() => rejectProp(p.id)}
                            className="px-3 py-1.5 rounded-lg bg-rose-50 text-rose-700 text-xs font-medium hover:bg-rose-100 transition"
                          >
                            ✗ 拒绝
                          </button>
                        </div>
                      ) : p.status === "applied" ? (
                        <div className="text-xs text-[var(--text-tertiary)]">
                          应用于 {(p.applied_at || "").slice(0, 16)} · 原值 {p.original_value}
                        </div>
                      ) : null}
                    </div>
                  );
                })
              )}
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
