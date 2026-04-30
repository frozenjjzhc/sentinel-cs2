import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ItemSummary } from "@/lib/api";
import { fmtPrice, fmtPct, pctClass, shortName } from "@/lib/format";
import { useRevealObserver } from "@/hooks/useReveal";
import DopplerCanvas from "@/components/DopplerCanvas";
import AKSilhouette from "@/components/AKSilhouette";
import MagneticButton from "@/components/MagneticButton";

const PALETTE = [
  { grad: "skin-recoil",  bg: "rgba(248,113,113,0.06)" },
  { grad: "skin-doppler", bg: "rgba(99,102,241,0.06)"  },
  { grad: "skin-ember",   bg: "rgba(245,158,11,0.06)"  },
  { grad: "skin-marble",  bg: "rgba(168,85,247,0.06)"  },
] as const;

const STRATEGY_PALETTE: Record<string, { gradClass: string; icon: string }> = {
  "phase-sync-v1":     { gradClass: "cs2-violet",   icon: "🌈" },
  "rsi-reversion-v1":  { gradClass: "cs2-tempered", icon: "〰️" },
  "mean-reversion-v1": { gradClass: "cs2-emerald",  icon: "📐" },
  "grid-half-v1":      { gradClass: "cs2-doppler",  icon: "⚡" },
};

function SkinCard({ item, idx }: { item: ItemSummary; idx: number }) {
  const c = PALETTE[idx % 4];
  const fullName = item.short_name || item.name || "—";
  const prefix = (fullName.split(/\s+/)[0] || "").slice(0, 5);
  const wearMatch = (item.name || "").match(/\(([^)]+)\)/);
  const wear = wearMatch ? wearMatch[1] : "";
  const phase = item.phase && item.phase !== "unknown" ? item.phase : "";
  const desc = [wear, phase].filter(Boolean).join(" · ") || "监控中";

  const badge = item.position ? (
    <span className="pill green">持仓</span>
  ) : (
    <span className="pill">监控中</span>
  );

  return (
    <div className={`liquid-glass reveal delay-${(idx % 4) + 1} rounded-[28px] p-7 transition-transform hover:-translate-y-1`}>
      <div className="flex items-center justify-between mb-4 relative z-10">
        {item.image_url ? (
          <div
            className="w-16 h-16 rounded-2xl overflow-hidden flex items-center justify-center"
            style={{
              background: `linear-gradient(135deg, var(--${c.grad}) 0%, transparent 80%)`,
              boxShadow: "0 8px 24px -8px rgba(99,102,241,0.4)",
            }}
          >
            <img
              src={item.image_url}
              alt={fullName}
              loading="lazy"
              referrerPolicy="no-referrer"
              style={{
                width: "100%",
                height: "100%",
                objectFit: "contain",
                filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.15))",
              }}
              onError={(e) => {
                const el = e.currentTarget;
                const span = document.createElement("span");
                span.className = "text-white font-medium text-sm";
                span.textContent = prefix;
                el.replaceWith(span);
              }}
            />
          </div>
        ) : (
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center"
            style={{
              background: `var(--${c.grad})`,
              boxShadow: "0 8px 24px -8px rgba(99,102,241,0.4)",
            }}
          >
            <span className="text-white font-medium text-sm">{prefix}</span>
          </div>
        )}
        {badge}
      </div>
      <h3 className="font-medium text-lg mb-1 relative z-10">{fullName}</h3>
      <p className="text-xs text-[var(--text-tertiary)] mb-4 relative z-10">{desc}</p>
      <div className="text-3xl font-semibold tracking-tight relative z-10">{fmtPrice(item.price ?? null)}</div>
      <div className="flex items-center gap-2 mt-2 relative z-10">
        <span className={`text-sm font-medium ${pctClass(item.today_pct ?? null)}`}>
          {fmtPct(item.today_pct ?? null)}
        </span>
        <span className="text-xs text-[var(--text-tertiary)]">今日</span>
      </div>
    </div>
  );
}

const CHAPTERS = [
  {
    letter: "A",
    title: 'A 类<br/><span class="text-gradient">即时止损</span>',
    desc: "固定止损、移动止损、强支撑止损、急跌检测。<br/>A 类信号无视去重，触发即推送，<br/>因为风险控制不能等。",
    bg: "var(--skin-doppler)",
  },
  {
    letter: "C",
    title: 'C 类<br/><span class="text-gradient">突破买入</span>',
    desc: "突破前期高 + 大盘配合 + 放量确认。<br/>多重过滤后的高质量买入信号，<br/>给你最清晰的进场时机。",
    bg: "var(--skin-marble)",
  },
  {
    letter: "D",
    title: 'D 类<br/><span class="text-gradient">回踩入场</span>',
    desc: "突破回踩缩量 + 反弹拐头 + 动能确认。<br/>这是技术分析里最经典的入场点，<br/>让你买在便宜价、止损更紧。",
    bg: "var(--skin-tempered)",
  },
];

function StickyParallax() {
  const [chapIdx, setChapIdx] = useState(0);

  useEffect(() => {
    function onScroll() {
      const stage = document.querySelector(".sticky-stage") as HTMLElement | null;
      if (!stage) return;
      const r = stage.getBoundingClientRect();
      const total = stage.offsetHeight - window.innerHeight;
      if (total <= 0) return;
      const progress = Math.max(0, Math.min(1, -r.top / total));
      const idx = Math.min(CHAPTERS.length - 1, Math.floor(progress * CHAPTERS.length));
      setChapIdx(idx);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const chap = CHAPTERS[chapIdx];

  return (
    <section className="sticky-stage" style={{ background: "var(--bg-secondary)" }}>
      <div className="sticky-pin px-12">
        <div className="relative h-[600px] flex items-center justify-center">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="glow-orb orb-2" style={{ position: "absolute", opacity: 0.3 }} />
          </div>
          <div
            className="relative z-10 w-[400px] h-[400px] rounded-[48px] flex items-center justify-center transition-all duration-700"
            style={{ background: chap.bg }}
          >
            <span className="text-white text-7xl font-semibold transition-all">
              {chap.letter}
            </span>
          </div>
        </div>
        <div className="relative h-full flex flex-col justify-center pl-16 max-w-xl">
          <div>
            <span className="pill mb-6">CHAPTER {chapIdx + 1}</span>
            <h2
              className="text-5xl font-semibold tracking-tight leading-tight mb-6"
              dangerouslySetInnerHTML={{ __html: chap.title }}
            />
            <p
              className="text-lg text-[var(--text-secondary)] leading-relaxed"
              dangerouslySetInnerHTML={{ __html: chap.desc }}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  useRevealObserver();
  const nav = useNavigate();

  const items = useQuery({
    queryKey: ["items"],
    queryFn: () => api.items(),
    refetchInterval: 30_000,
  });

  const market = useQuery({
    queryKey: ["market"],
    queryFn: () => api.market(),
    refetchInterval: 30_000,
  });

  const strategies = useQuery({ queryKey: ["strategies"], queryFn: () => api.strategies() });
  const budget = useQuery({ queryKey: ["budget"], queryFn: () => api.budget() });
  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => api.portfolio(),
    refetchInterval: 60_000,
  });
  const freshness = useQuery({
    queryKey: ["freshness"],
    queryFn: () => api.freshness(),
    refetchInterval: 30_000,
  });
  const shadowStats = useQuery({ queryKey: ["shadow-stats"], queryFn: () => api.shadowStats() });

  const itemList = items.data?.items ?? [];
  const itemCount = items.data?.count ?? 0;

  const activeStrategy = strategies.data?.strategies.find((s) => s.id === strategies.data?.active);
  const planned = budget.data?.planned_total_cny ?? 0;
  const heroBudget = planned > 0 ? `¥${(planned / 1000).toFixed(1)}k` : "未设";

  const used = portfolio.data && !portfolio.data.empty ? portfolio.data.total_cost : 0;
  let heroBudgetUsed = "已用 —";
  let heroBudgetUsedColor = "text-[var(--text-tertiary)]";
  if (planned > 0) {
    const usedPct = (used / planned) * 100;
    heroBudgetUsedColor =
      usedPct > 100 ? "text-rose-600" : usedPct > 80 ? "text-amber-600" : "text-emerald-600";
    heroBudgetUsed = `已用 ¥${(used / 1000).toFixed(1)}k (${usedPct.toFixed(0)}%)`;
  } else if (used > 0) {
    heroBudgetUsed = `已用 ¥${(used / 1000).toFixed(1)}k`;
  }

  const totalShadows = Object.values(shadowStats.data?.stats ?? {}).reduce(
    (s, v) => s + (v.count || 0),
    0
  );

  return (
    <>
      {/* HERO */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-14 tactical-grid">
        <DopplerCanvas />
        <div className="glow-orb orb-1" />
        <div className="glow-orb orb-2" />
        <div className="glow-orb orb-3" />
        <div className="corner-crosshair tl" />
        <div className="corner-crosshair tr" />
        <div className="corner-crosshair bl" />
        <div className="corner-crosshair br" />

        <div className="hidden sm:block">
          <AKSilhouette />
        </div>

        <div className="relative z-10 text-center px-6 max-w-5xl mx-auto">
          <div className="reveal mb-8 flex items-center justify-center gap-3 flex-wrap">
            <span className={`pill ${freshness.data?.status === "ok" ? "green" : freshness.data?.status === "delayed" ? "amber" : freshness.data?.status === "stalled" ? "rose" : ""}`}>
              {freshness.data
                ? freshness.data.status === "ok"
                  ? `🟢 监控运行中 · ${freshness.data.age_minutes} 分钟前更新`
                  : freshness.data.status === "delayed"
                  ? `🟡 监控延迟 · 已 ${freshness.data.age_minutes} 分钟未更新`
                  : freshness.data.status === "stalled"
                  ? `🔴 监控可能已停 · ${((freshness.data.age_minutes ?? 0) / 60).toFixed(1)} 小时无更新`
                  : "🟢 API 在线"
                : "⏳ 正在检测 API..."}
            </span>
            {market.data?.current_index && (
              <span className="pill">
                📈 大盘 {market.data.current_index.toFixed(2)} (
                {(market.data.current_change_pct ?? 0) > 0 ? "+" : ""}
                {(market.data.current_change_pct ?? 0).toFixed(2)}%)
              </span>
            )}
          </div>

          <h1 className="reveal delay-1 text-5xl sm:text-6xl md:text-7xl lg:text-[88px] font-semibold tracking-tight leading-[1.05] mb-6">
            <span className="text-gradient">极简</span> ·{" "}
            <span className="text-gradient">极智</span> ·{" "}
            <span className="text-gradient">极速</span>
          </h1>

          <p className="reveal delay-2 text-base sm:text-xl md:text-2xl text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto leading-relaxed">
            为 CS2 饰品交易者打造的智能信号引擎。<br />
            让每一次买卖，都有数据支撑。
          </p>

          <div className="reveal delay-3 flex items-center justify-center gap-4">
            <MagneticButton
              onClick={() => {
                document.getElementById("skin-cards")?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              查看实时监控
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </MagneticButton>
            <MagneticButton
              onClick={() => nav("/charts")}
              style={{
                background: "transparent",
                color: "var(--text-primary)",
                border: "1px solid rgba(0,0,0,0.12)",
              }}
            >
              查看 K 线
            </MagneticButton>
          </div>

          {/* 4 张液态玻璃统计卡 */}
          <div className="reveal delay-4 mt-20 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto stagger-in">
            <div className="liquid-glass rounded-3xl p-6 text-left">
              <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider">监控品种</div>
              <div className="text-3xl font-semibold tracking-tight mt-2">{itemCount}</div>
              <div className="text-xs text-[var(--text-tertiary)] mt-1">SteamDT 实时抓取</div>
            </div>
            <div className="liquid-glass rounded-3xl p-6 text-left">
              <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider">扫描频率</div>
              <div className="text-3xl font-semibold tracking-tight mt-2">
                10<span className="text-base text-[var(--text-tertiary)] ml-1">分钟</span>
              </div>
              <div className="text-xs text-[var(--text-tertiary)] mt-1">Fast / 1H Slow / 23:00 复盘</div>
            </div>
            <div className="liquid-glass rounded-3xl p-6 text-left">
              <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider">活跃策略</div>
              <div className="text-2xl font-semibold tracking-tight mt-2 truncate">
                {shortName(activeStrategy?.name) || "—"}
              </div>
              <div className="text-xs text-[var(--text-tertiary)] mt-1">
                {strategies.data ? `${strategies.data.strategies.length} 个策略可选` : "— 个策略可选"}
              </div>
            </div>
            <div className="liquid-glass rounded-3xl p-6 text-left">
              <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider">总仓位预算</div>
              <div className="text-3xl font-semibold tracking-tight mt-2">{heroBudget}</div>
              <div className={`text-xs mt-1 ${heroBudgetUsedColor}`}>{heroBudgetUsed}</div>
            </div>
          </div>
        </div>
      </section>

      {/* 系统脉搏 */}
      <section className="relative py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <span className="pill mb-4 reveal">SYSTEM PULSE</span>
            <h2 className="reveal delay-1 text-4xl md:text-5xl font-semibold tracking-tight mb-3">
              永不停歇的<span className="text-gradient">数据脉搏</span>
            </h2>
            <p className="reveal delay-2 text-base text-[var(--text-secondary)] max-w-2xl mx-auto">
              每 10 分钟一次扫描，每条信号都被 shadow 跟跑，每个决策都有数据支撑。
            </p>
          </div>

          <div className="reveal delay-3 liquid-glass rounded-[28px] p-10 mb-6">
            <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="w-3 h-3 rounded-full bg-emerald-500 heartbeat" />
                  <div
                    className="pulse-ring text-emerald-500"
                    style={{ width: 12, height: 12, left: 0, top: 0 }}
                  />
                </div>
                <div>
                  <div className="font-medium">监控引擎运行中</div>
                  <div className="text-xs text-[var(--text-tertiary)]">
                    最近扫描:{" "}
                    {freshness.data?.age_minutes != null
                      ? freshness.data.age_minutes < 60
                        ? `${freshness.data.age_minutes.toFixed(1)} 分钟前`
                        : `${(freshness.data.age_minutes / 60).toFixed(1)} 小时前`
                      : "—"}
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-6 text-right">
                <div>
                  <div className="text-2xl font-semibold">{totalShadows}</div>
                  <div className="text-xs text-[var(--text-tertiary)]">Shadow 累计</div>
                </div>
                <div>
                  <div className="text-2xl font-semibold">{shadowStats.data?.pending ?? 0}</div>
                  <div className="text-xs text-[var(--text-tertiary)]">7 日内待评估</div>
                </div>
                <div>
                  <div className="text-2xl font-semibold">
                    {strategies.data?.strategies.length ?? "—"}
                  </div>
                  <div className="text-xs text-[var(--text-tertiary)]">策略并行</div>
                </div>
              </div>
            </div>

            <svg viewBox="0 0 800 80" preserveAspectRatio="none" className="w-full" style={{ height: 80 }}>
              <defs>
                <linearGradient id="pulseGrad" x1="0" x2="1" y1="0" y2="0">
                  <stop offset="0%" stopColor="#10B981" stopOpacity="0" />
                  <stop offset="50%" stopColor="#10B981" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path
                d="M 0 40 L 100 40 L 110 25 L 120 60 L 130 10 L 140 50 L 150 40 L 250 40 L 260 25 L 270 60 L 280 10 L 290 50 L 300 40 L 400 40 L 410 25 L 420 60 L 430 10 L 440 50 L 450 40 L 550 40 L 560 25 L 570 60 L 580 10 L 590 50 L 600 40 L 700 40 L 710 25 L 720 60 L 730 10 L 740 50 L 750 40 L 800 40"
                stroke="url(#pulseGrad)"
                strokeWidth="2"
                fill="none"
              />
            </svg>
          </div>

          {/* 4 路并行策略小卡 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 stagger-in">
            {strategies.data?.strategies.map((s) => {
              const p = STRATEGY_PALETTE[s.id] || { gradClass: "cs2-marble", icon: "·" };
              const stats = strategies.data!.performance?.[s.id];
              const isActive = s.id === strategies.data!.active;
              return (
                <Link
                  key={s.id}
                  to="/strategy"
                  className="liquid-glass rounded-3xl p-5 cursor-pointer transition-transform hover:-translate-y-1"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg ${p.gradClass}`}
                    >
                      <span style={{ filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.2))" }}>
                        {p.icon}
                      </span>
                    </div>
                    {isActive && (
                      <span className="pill green" style={{ fontSize: 10 }}>
                        active
                      </span>
                    )}
                  </div>
                  <div className="font-semibold text-base mb-1">{shortName(s.name)}</div>
                  <div className="text-xs text-[var(--text-tertiary)] truncate mb-3">
                    {s.tagline || ""}
                  </div>
                  {stats ? (
                    <div className="flex items-baseline gap-2">
                      <span
                        className={`text-xl font-semibold ${
                          stats.win_rate >= 0.5 ? "text-emerald-600" : "text-rose-600"
                        }`}
                      >
                        {(stats.win_rate * 100).toFixed(0)}%
                      </span>
                      <span className="text-xs text-[var(--text-tertiary)]">
                        胜率 · {stats.count} 笔
                      </span>
                    </div>
                  ) : (
                    <div className="text-xs text-[var(--text-tertiary)]">📊 数据积累中</div>
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* 饰品卡 */}
      <section id="skin-cards" className="relative py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <span className="pill mb-6 reveal">SENTINEL ENGINE</span>
            <h2 className="reveal delay-1 text-5xl md:text-6xl font-semibold tracking-tight leading-tight mb-6">
              从未离开的<br />
              <span className="text-gradient">智能哨兵</span>
            </h2>
            <p className="reveal delay-2 text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
              每 10 分钟一次价格扫描，每小时一次趋势研判，每晚一份复盘报告。
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {itemList.length === 0 ? (
              <div className="col-span-full text-center py-20">
                <div className="text-6xl mb-4 opacity-25">🎯</div>
                <div className="text-lg font-medium mb-2 text-[var(--text-secondary)]">暂无监控饰品</div>
                <div className="text-sm text-[var(--text-tertiary)]">
                  去{" "}
                  <Link to="/settings" className="text-indigo-600 hover:underline cursor-pointer font-medium">
                    设置
                  </Link>{" "}
                  添加你想监控的 SteamDT 饰品
                </div>
              </div>
            ) : (
              <>
                {itemList.slice(0, 4).map((it, i) => (
                  <SkinCard key={it.id} item={it} idx={i} />
                ))}
                {itemList.length > 4 && (
                  <div className="col-span-full text-center text-xs text-[var(--text-tertiary)] mt-2">
                    仅显示前 4 个 · 共 {itemList.length} 个监控品种 ·{" "}
                    <Link to="/charts" className="text-indigo-600 hover:underline">
                      走势图
                    </Link>{" "}
                    查看全部
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </section>

      <StickyParallax />

      {/* CTA */}
      <section className="relative py-40 px-6 overflow-hidden">
        <div className="glow-orb orb-1" style={{ top: "20%", left: "20%" }} />
        <div className="glow-orb orb-3" style={{ bottom: "0%", right: "15%" }} />
        <div className="relative z-10 max-w-4xl mx-auto text-center">
          <h2 className="reveal text-6xl md:text-7xl font-semibold tracking-tight leading-tight mb-8">
            由你的<br />
            <span className="text-gradient">本地 Python</span><br />
            驱动。
          </h2>
          <p className="reveal delay-1 text-xl text-[var(--text-secondary)] mb-12 max-w-xl mx-auto">
            0 token 日常运营。100% 数据本地化。完全开源可定制。
          </p>
          <div className="reveal delay-2 flex items-center justify-center gap-4">
            <MagneticButton onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
              回到顶部
            </MagneticButton>
            <MagneticButton
              onClick={() => window.open("/docs", "_blank")}
              style={{
                background: "transparent",
                color: "var(--text-primary)",
                border: "1px solid rgba(0,0,0,0.12)",
              }}
            >
              查看 API 文档
            </MagneticButton>
          </div>
        </div>
      </section>
    </>
  );
}
