import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { api } from "@/lib/api";

const PAGES = [
  { path: "/", label: "概览", end: true },
  { path: "/charts", label: "走势图" },
  { path: "/positions", label: "仓位管理" },
  { path: "/strategy", label: "策略管控" },
  { path: "/ai", label: "AI 复盘" },
  { path: "/settings", label: "设置" },
] as const;

type StatusPill = { html: string; cls: string };

// 顶部导航栏 — 6 个页面 + 实时心跳 pill
export default function Nav() {
  const [status, setStatus] = useState<StatusPill>({ html: "⏳ 检测中", cls: "pill" });

  useEffect(() => {
    let alive = true;
    async function refresh() {
      const h = await api.health();
      if (!alive) return;
      if (!h) {
        setStatus({ html: "🔴 API 离线（使用演示数据）", cls: "pill amber" });
        return;
      }
      const f = await api.freshness();
      if (!alive) return;
      if (!f || f.status === "unknown") {
        setStatus({ html: "🟢 API 在线 · ⚠️ 数据状态未知", cls: "pill amber" });
      } else if (f.status === "ok") {
        setStatus({
          html: `🟢 监控运行中 · ${f.age_minutes} 分钟前更新`,
          cls: "pill green",
        });
      } else if (f.status === "delayed") {
        setStatus({
          html: `🟡 监控延迟 · 已 ${f.age_minutes} 分钟未更新`,
          cls: "pill amber",
        });
      } else {
        const hr = ((f.age_minutes ?? 0) / 60).toFixed(1);
        setStatus({ html: `🔴 监控可能已停 · ${hr} 小时无更新`, cls: "pill rose" });
      }
    }
    refresh();
    const id = setInterval(refresh, 30_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <nav className="fixed top-0 inset-x-0 z-50 backdrop-blur-xl bg-white/75 border-b border-black/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-2">
        <Link to="/" className="flex items-center gap-2.5 cursor-pointer flex-shrink-0 group">
          {/* 哨兵盾牌 logo：渐变填充 + 中心准星，呼应 Hero 的 AK-47 主题 */}
          <svg
            width="28"
            height="28"
            viewBox="0 0 32 32"
            xmlns="http://www.w3.org/2000/svg"
            className="transition-transform group-hover:scale-110 group-hover:rotate-3"
            style={{ filter: "drop-shadow(0 2px 6px rgba(99,102,241,0.35))" }}
          >
            <defs>
              <linearGradient id="logoGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#6366F1" />
                <stop offset="50%" stopColor="#EC4899" />
                <stop offset="100%" stopColor="#F59E0B" />
              </linearGradient>
              <linearGradient id="logoInner" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
                <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.7" />
              </linearGradient>
            </defs>
            {/* 盾牌轮廓 */}
            <path
              d="M16 2 L28 6 L28 17 C28 24 22 29 16 30 C10 29 4 24 4 17 L4 6 Z"
              fill="url(#logoGrad)"
            />
            {/* 内部高光 */}
            <path
              d="M16 5 L25 8 L25 17 C25 22.5 20.5 26.5 16 27.5 C11.5 26.5 7 22.5 7 17 L7 8 Z"
              fill="url(#logoInner)"
              opacity="0.18"
            />
            {/* 中心准星：圆 + 十字 */}
            <circle cx="16" cy="16" r="4" stroke="white" strokeWidth="1.6" fill="none" />
            <line x1="16" y1="9" x2="16" y2="12" stroke="white" strokeWidth="1.6" strokeLinecap="round" />
            <line x1="16" y1="20" x2="16" y2="23" stroke="white" strokeWidth="1.6" strokeLinecap="round" />
            <line x1="9" y1="16" x2="12" y2="16" stroke="white" strokeWidth="1.6" strokeLinecap="round" />
            <line x1="20" y1="16" x2="23" y2="16" stroke="white" strokeWidth="1.6" strokeLinecap="round" />
            <circle cx="16" cy="16" r="1" fill="white" />
          </svg>
          <span className="font-semibold tracking-tight text-[15px] bg-gradient-to-r from-slate-900 via-indigo-700 to-pink-600 bg-clip-text text-transparent">
            Sentinel
          </span>
        </Link>

        {/* 桌面/平板：横排 */}
        <div className="hidden md:flex items-center gap-2 text-sm">
          {PAGES.map((p) => (
            <NavLink
              key={p.path}
              to={p.path}
              end={"end" in p ? p.end : false}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              {p.label}
            </NavLink>
          ))}
        </div>

        <span
          className={`${status.cls} hidden sm:inline-flex truncate max-w-[200px]`}
          style={{ fontSize: 12 }}
          dangerouslySetInnerHTML={{ __html: status.html }}
        />

        {/* 移动端：hamburger，用 <details> 实现免依赖 */}
        <details className="md:hidden relative">
          <summary className="cursor-pointer list-none p-2 rounded-lg hover:bg-black/[0.04]">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </summary>
          <div className="absolute right-0 top-full mt-2 bg-white border border-black/10 rounded-2xl shadow-xl py-2 min-w-[180px]">
            {PAGES.map((p) => (
              <NavLink
                key={p.path}
                to={p.path}
                end={"end" in p ? p.end : false}
                className={({ isActive }) =>
                  `block px-4 py-2 text-sm hover:bg-black/[0.04] ${isActive ? "bg-indigo-50 text-indigo-700 font-medium" : ""}`
                }
                onClick={(e) => {
                  // 关闭 details
                  const det = (e.currentTarget.closest("details") as HTMLDetailsElement | null);
                  if (det) det.open = false;
                }}
              >
                {p.label}
              </NavLink>
            ))}
            <div
              className={`block px-4 pt-2 mt-1 border-t border-black/5 text-xs ${
                status.cls.includes("rose")
                  ? "text-rose-600"
                  : status.cls.includes("amber")
                  ? "text-amber-600"
                  : status.cls.includes("green")
                  ? "text-emerald-600"
                  : ""
              }`}
              dangerouslySetInnerHTML={{ __html: status.html }}
            />
          </div>
        </details>
      </div>
    </nav>
  );
}
