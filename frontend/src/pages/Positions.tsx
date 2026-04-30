import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ItemSummary, PortfolioBreakdown } from "@/lib/api";
import { fmtPrice, fmtPct, pctClass } from "@/lib/format";
import { showToast } from "@/lib/toast";

type Action = "buy" | "sell" | "legacy" | "legacy_remove" | "clear";

function PositionCard({ it, breakdown, budgetVal, refetch }: {
  it: ItemSummary;
  breakdown: PortfolioBreakdown | undefined;
  budgetVal: number;
  refetch: () => void;
}) {
  const [action, setAction] = useState<Action>("buy");
  const [price, setPrice] = useState("");
  const [pieces, setPieces] = useState("");
  const [busy, setBusy] = useState(false);

  const pos = it.position;
  const legacy = it.legacy;
  const pctOfBudget = breakdown?.pct_of_budget;
  const pctText =
    budgetVal > 0 && pctOfBudget != null
      ? ` （占总仓 ${(pctOfBudget * 100).toFixed(1)}%）`
      : "";

  async function submit() {
    const p = parseFloat(price);
    const q = parseFloat(pieces);
    setBusy(true);
    let res;
    if (action === "buy") {
      if (!p || !q) { showToast("价格和把数都必填", "error"); setBusy(false); return; }
      res = await api.positionBuy(it.id, p, q);
    } else if (action === "sell") {
      if (!p || !q) { showToast("价格和把数都必填", "error"); setBusy(false); return; }
      res = await api.positionSell(it.id, p, q);
    } else if (action === "legacy") {
      if (!p || !q) { showToast("均价和把数都必填", "error"); setBusy(false); return; }
      res = await api.setLegacy(it.id, { quantity: q, avg_entry_price: p, action: "set" });
    } else if (action === "legacy_remove") {
      res = await api.setLegacy(it.id, { action: "remove" });
    } else {
      if (!confirm("确定清空新仓所有档？此操作不可逆。")) { setBusy(false); return; }
      res = await api.positionClear(it.id);
    }
    setBusy(false);
    if (res.ok) {
      showToast(action === "buy" ? "加仓成功" : action === "sell" ? "卖出成功" : "操作成功");
      setPrice(""); setPieces("");
      refetch();
    } else {
      showToast("失败：" + res.error, "error");
    }
  }

  return (
    <div className="rounded-2xl p-5 bg-white border border-black/5">
      <div className="font-medium mb-3">
        {it.short_name || it.name}
        <span className="text-xs text-[var(--text-tertiary)]">{pctText}</span>
      </div>
      {pos ? (
        <div className="text-sm space-y-1 mb-3">
          <div>
            新仓：<strong>{pos.total_pieces || 0} 把</strong> @均价 {fmtPrice(pos.avg_entry_price)} · 成本 {fmtPrice(breakdown?.active_cost)}
          </div>
          {pos.pnl_pct != null && (
            <div className={pctClass(pos.pnl_pct * 100)}>浮盈 {fmtPct(pos.pnl_pct * 100)}</div>
          )}
          <div className="text-xs text-[var(--text-tertiary)]">
            最高 {fmtPrice(pos.highest_since_first_entry)} · 止盈已执行 {(pos.tp_executed || []).join(", ") || "无"}
          </div>
        </div>
      ) : (
        <div className="text-sm text-[var(--text-tertiary)] mb-3">新仓：无</div>
      )}
      {legacy && (
        <div className="mt-3 pt-3 border-t border-black/5 text-sm">
          <div>
            套牢仓：<strong>{legacy.quantity} 把</strong> @均价 {fmtPrice(legacy.avg_entry_price)}
          </div>
          {legacy.pnl_pct != null && (
            <div className={pctClass(legacy.pnl_pct * 100)}>浮亏 {fmtPct(legacy.pnl_pct * 100)}</div>
          )}
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-black/5">
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <select
            className="text-xs px-2 py-1.5 rounded-lg border border-black/10 bg-white"
            value={action}
            onChange={(e) => setAction(e.target.value as Action)}
          >
            <option value="buy">加仓</option>
            <option value="sell">卖出</option>
            <option value="legacy">设套牢仓</option>
            <option value="legacy_remove">移除套牢仓</option>
            <option value="clear">清空新仓</option>
          </select>
          <input
            type="number"
            step="0.01"
            min="0"
            placeholder="价格 ¥"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="text-xs px-2 py-1.5 rounded-lg border border-black/10 w-24"
          />
          <input
            type="number"
            step="0.01"
            min="0"
            placeholder="把数"
            value={pieces}
            onChange={(e) => setPieces(e.target.value)}
            className="text-xs px-2 py-1.5 rounded-lg border border-black/10 w-20"
          />
          <button
            disabled={busy}
            onClick={submit}
            className="text-xs px-3 py-1.5 rounded-lg bg-indigo-600 text-white font-medium hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {busy ? "..." : "执行"}
          </button>
        </div>
        <div className="text-[11px] text-[var(--text-tertiary)] leading-relaxed">
          加仓/卖出/设套牢仓：填<strong>价格 + 把数</strong>。占总仓 % 由系统自动计算（基于上方总仓位预算）。<br />
          移除套牢仓 / 清空新仓不需要填任何字段。
        </div>
      </div>
    </div>
  );
}

export default function Positions() {
  const qc = useQueryClient();
  const [budgetVal, setBudgetVal] = useState("");
  const [budgetStatus, setBudgetStatus] = useState<{ text: string; color: string }>({
    text: "",
    color: "",
  });

  const portfolio = useQuery({ queryKey: ["portfolio"], queryFn: () => api.portfolio() });
  const items = useQuery({ queryKey: ["items"], queryFn: () => api.items() });
  const budget = useQuery({ queryKey: ["budget"], queryFn: () => api.budget() });

  useEffect(() => {
    if (budget.data && !budgetVal) setBudgetVal(String(budget.data.planned_total_cny || ""));
  }, [budget.data]);  // eslint-disable-line

  const breakdownMap: Record<string, PortfolioBreakdown> = {};
  (portfolio.data?.breakdown || []).forEach((b) => { breakdownMap[b.id] = b; });

  const pln = budget.data?.planned_total_cny || 0;
  const used = portfolio.data?.total_cost || 0;
  const usedPct = pln > 0 ? (used / pln) * 100 : 0;
  const remain = pln - used;
  const usedColor = usedPct > 100 ? "text-rose-600" : usedPct > 80 ? "text-amber-600" : "text-emerald-600";
  const barColor = usedPct > 100 ? "#EF4444" : usedPct > 80 ? "#F59E0B" : "#10B981";

  async function saveBudget() {
    const v = parseFloat(budgetVal);
    if (isNaN(v) || v < 0) { showToast("请输入正数", "error"); return; }
    setBudgetStatus({ text: "保存中...", color: "" });
    const res = await api.setBudget(v);
    if (res.ok) {
      setBudgetStatus({ text: "✓ 已保存", color: "#10B981" });
      qc.invalidateQueries({ queryKey: ["budget"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    } else {
      setBudgetStatus({ text: "✗ " + res.error, color: "#EF4444" });
    }
  }

  function refetch() {
    qc.invalidateQueries({ queryKey: ["portfolio"] });
    qc.invalidateQueries({ queryKey: ["items"] });
    qc.invalidateQueries({ queryKey: ["budget"] });
  }

  return (
    <div style={{ paddingTop: 100 }}>
      <section className="py-12 px-6 max-w-6xl mx-auto">
        <h2 className="text-4xl font-semibold tracking-tight mb-3">仓位管理</h2>
        <p className="text-[var(--text-secondary)] mb-10">
          查看新建仓 / 套牢仓 / 总风险面板。所有百分比基于你设的总仓位预算自动计算。
        </p>

        {/* 总仓位预算 */}
        <div
          className="mb-6 rounded-[28px] p-8 backdrop-blur-2xl"
          style={{ background: "rgba(255,255,255,0.65)", border: "1px solid rgba(255,255,255,0.35)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium">💼 总仓位预算</h3>
            <span className="text-xs text-[var(--text-tertiary)]">
              所有"占总仓 %"基于此值计算
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-3xl font-semibold tracking-tight">¥</div>
            <input
              type="number"
              step="100"
              min="0"
              placeholder="如 50000"
              value={budgetVal}
              onChange={(e) => setBudgetVal(e.target.value)}
              className="text-3xl font-semibold tracking-tight px-3 py-1 rounded-xl border border-black/10 bg-white w-44"
            />
            <button
              onClick={saveBudget}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition"
            >
              保存
            </button>
            <span className="text-xs" style={{ color: budgetStatus.color }}>
              {budgetStatus.text}
            </span>
          </div>
          <div className="mt-4 text-sm text-[var(--text-secondary)]">
            {pln <= 0 ? (
              <span className="text-amber-700">⚠️ 未设预算 — 设置后系统才能算"占总仓 %"。</span>
            ) : portfolio.data && !portfolio.data.empty ? (
              <>
                <div className="flex items-baseline justify-between mb-2">
                  <span>
                    已用{" "}
                    <strong className={usedColor}>
                      {fmtPrice(used)} ({usedPct.toFixed(1)}%)
                    </strong>
                  </span>
                  <span>
                    剩余 <strong>{fmtPrice(remain)}</strong>
                  </span>
                </div>
                <div className="h-2 rounded-full bg-black/[0.06] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${Math.min(100, usedPct)}%`, background: barColor }}
                  />
                </div>
              </>
            ) : (
              <>预算 {fmtPrice(pln)} · 当前还没有持仓</>
            )}
          </div>
        </div>

        {/* 总仓位汇总 */}
        <div
          className="mb-10 rounded-[28px] p-8 backdrop-blur-2xl"
          style={{ background: "rgba(255,255,255,0.65)", border: "1px solid rgba(255,255,255,0.35)" }}
        >
          <h3 className="text-lg font-medium mb-4">总仓位</h3>
          {portfolio.data && !portfolio.data.empty ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <div className="text-xs text-[var(--text-tertiary)]">总成本</div>
                  <div className="text-2xl font-semibold">{fmtPrice(portfolio.data.total_cost)}</div>
                </div>
                <div>
                  <div className="text-xs text-[var(--text-tertiary)]">总市值</div>
                  <div className="text-2xl font-semibold">{fmtPrice(portfolio.data.total_value)}</div>
                </div>
                <div>
                  <div className="text-xs text-[var(--text-tertiary)]">浮盈</div>
                  <div
                    className={`text-2xl font-semibold ${
                      portfolio.data.total_pnl >= 0 ? "text-emerald-600" : "text-rose-600"
                    }`}
                  >
                    {fmtPrice(portfolio.data.total_pnl)} ({fmtPct(portfolio.data.total_pnl_pct * 100)})
                  </div>
                </div>
              </div>
              {!!portfolio.data.warnings?.length && (
                <div className="mt-4 p-3 rounded-xl bg-amber-50 text-sm text-amber-800">
                  {portfolio.data.warnings.map((w, i) => (
                    <div key={i}>{w}</div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="text-sm text-[var(--text-tertiary)]">加载中或暂无持仓</div>
          )}
        </div>

        <h3 className="text-2xl font-semibold tracking-tight mb-4">分品种</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(items.data?.items ?? []).map((it) => (
            <PositionCard
              key={it.id}
              it={it}
              breakdown={breakdownMap[it.id]}
              budgetVal={pln}
              refetch={refetch}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
