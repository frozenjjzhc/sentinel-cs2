import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import QRCode from "qrcode";
import { api, Fundamentals, getToken, setToken } from "@/lib/api";
import { showToast } from "@/lib/toast";

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-[28px] p-8 backdrop-blur-2xl ${className}`}
      style={{
        background: "rgba(255,255,255,0.65)",
        border: "1px solid rgba(255,255,255,0.35)",
      }}
    >
      {children}
    </div>
  );
}

const BIAS_IMPACT: Record<string, { buy_pri: string; stop_mult: string; tp_mult: string; desc: string }> = {
  positive: { buy_pri: "+1", stop_mult: "×1.0", tp_mult: "×1.1", desc: "正面：信号优先级+1，止盈略放宽" },
  positive_with_whale_buy: {
    buy_pri: "+1",
    stop_mult: "×1.1",
    tp_mult: "×1.3",
    desc: "正面+庄家：止损放宽 10%，止盈第三档放奔跑 30%",
  },
  neutral_positive: { buy_pri: "+0.5", stop_mult: "×1.0", tp_mult: "×1.05", desc: "偏中性正向：略偏多" },
  neutral: { buy_pri: "0", stop_mult: "×1.0", tp_mult: "×1.0", desc: "中性：所有阈值不变" },
  negative: { buy_pri: "-1", stop_mult: "×0.7", tp_mult: "×0.8", desc: "负面：止损收紧 30%，止盈提早 20%" },
  emergency: { buy_pri: "屏蔽", stop_mult: "×0.5", tp_mult: "×0.6", desc: "紧急：BUY 完全屏蔽，止损减半" },
};

function biasColor(b?: string) {
  if (b === "positive") return "text-emerald-700 bg-emerald-50";
  if (b === "negative") return "text-rose-700 bg-rose-50";
  if (b === "emergency") return "text-red-700 bg-red-100";
  return "text-slate-600 bg-slate-50";
}

function FreshnessCard() {
  const { data: f } = useQuery({
    queryKey: ["freshness"],
    queryFn: () => api.freshness(),
    refetchInterval: 30_000,
  });
  if (!f) return null;
  const min = f.age_minutes ?? 0;
  const hr = (min / 60).toFixed(1);
  let bg: string, border: string, color: string, txt: string, age: string, hint: React.ReactNode;
  if (f.status === "ok") {
    bg = "rgba(34,197,94,0.04)"; border = "rgba(34,197,94,0.2)"; color = "#16A34A";
    txt = "✅ 监控运行正常"; age = `${min} 分钟前`; hint = null;
  } else if (f.status === "delayed") {
    bg = "rgba(245,158,11,0.06)"; border = "rgba(245,158,11,0.3)"; color = "#D97706";
    txt = "⚠️ 监控延迟"; age = `${min} 分钟前`;
    hint = (
      <div className="text-xs mt-2" style={{ color: "#D97706" }}>
        正常 fast 任务每 10 分钟一次。如果只是偶尔延迟可忽略，持续 30 min+ 请手动跑{" "}
        <code className="bg-white px-1 py-0.5 rounded">python monitor_fast.py</code> 看报错。
      </div>
    );
  } else if (f.status === "stalled") {
    bg = "rgba(239,68,68,0.06)"; border = "rgba(239,68,68,0.3)"; color = "#DC2626";
    txt = "🚨 监控可能已停"; age = `${hr} 小时前`;
    hint = (
      <div className="text-xs mt-2" style={{ color: "#DC2626" }}>
        排查：① <code className="bg-white px-1 rounded">schtasks /Query /TN "CS2 Monitor Fast" /V /FO LIST</code> 看任务状态<br />
        ② 看 <code className="bg-white px-1 rounded">logs/monitor_fast.log</code> 末尾报错<br />
        ③ 手动 <code className="bg-white px-1 rounded">python monitor_fast.py</code> 复现
      </div>
    );
  } else {
    bg = "rgba(34,197,94,0.04)"; border = "rgba(34,197,94,0.2)"; color = "#6E6E73";
    txt = "❓ 状态未知（无数据）"; age = "—"; hint = null;
  }
  return (
    <div className="mb-4 p-4 rounded-2xl border" style={{ background: bg, borderColor: border }}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium" style={{ color }}>{txt}</span>
        <span className="text-xs text-[var(--text-tertiary)]">{age}</span>
      </div>
      <div className="text-xs text-[var(--text-tertiary)]">
        最新数据点：{f.latest_data_time || "—"}
        {f.latest_data_item ? " · 来源：" + f.latest_data_item : ""}
      </div>
      {hint}
    </div>
  );
}

function SchedulerSection() {
  const qc = useQueryClient();
  const { data: resp } = useQuery({
    queryKey: ["scheduler"],
    queryFn: () => api.schedulerStatus(),
    refetchInterval: 10_000,
  });
  const [busy, setBusy] = useState<string | null>(null);

  const mode = resp?.mode || "embedded";
  const enabled = resp?.status?.enabled;
  const tasks = resp?.status?.tasks ?? {};
  const taskNames = ["monitor_fast", "monitor_slow", "daily_review"];

  async function setMode(m: "embedded" | "external") {
    const r = await api.schedulerSetMode(m);
    if (r.ok) {
      showToast(`已切换到 ${m === "embedded" ? "嵌入式" : "Windows 任务计划器"} 模式`);
      qc.invalidateQueries({ queryKey: ["scheduler"] });
    } else {
      showToast("切换失败：" + r.error, "error");
    }
  }
  async function toggle(start: boolean) {
    setBusy(start ? "start" : "stop");
    const r = start ? await api.schedulerStart() : await api.schedulerStop();
    setBusy(null);
    if (r.ok) {
      showToast(start ? "✓ 已启动" : "✓ 已停止");
      qc.invalidateQueries({ queryKey: ["scheduler"] });
    } else showToast("失败：" + r.error, "error");
  }
  async function runNow(name: string) {
    setBusy(name);
    showToast(`触发 ${name} 中...（首次扫描可能 30-60s）`);
    const r = await api.schedulerRun(name);
    setBusy(null);
    if (r.ok) {
      showToast(`✓ ${name} 已完成`);
      qc.invalidateQueries({ queryKey: ["scheduler"] });
    } else showToast("失败：" + r.error, "error");
  }

  const badge =
    mode === "embedded" ? (
      <span className={enabled ? "pill green" : "pill amber"} style={{ fontSize: 11 }}>
        {enabled ? "🟢 嵌入式 · 运行中" : "🟡 嵌入式 · 已停"}
      </span>
    ) : (
      <span className="pill" style={{ fontSize: 11 }}>🔵 外部任务计划器</span>
    );

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium">⚙️ 监控调度器</h3>
        {badge}
      </div>
      <div className="mb-4 p-4 rounded-2xl bg-indigo-50/50">
        <div className="text-sm font-medium mb-2">监控运行模式</div>
        <div className="flex flex-wrap gap-2 mb-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer p-2 rounded-lg hover:bg-white/60 flex-1 min-w-[200px]">
            <input
              type="radio"
              name="sched-mode"
              checked={mode === "embedded"}
              onChange={() => setMode("embedded")}
            />
            <div>
              <div className="font-medium">嵌入式（推荐）</div>
              <div className="text-xs text-[var(--text-tertiary)]">监控随 API 一起跑，开 API 即工作</div>
            </div>
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer p-2 rounded-lg hover:bg-white/60 flex-1 min-w-[200px]">
            <input
              type="radio"
              name="sched-mode"
              checked={mode === "external"}
              onChange={() => setMode("external")}
            />
            <div>
              <div className="font-medium">Windows 任务计划器</div>
              <div className="text-xs text-[var(--text-tertiary)]">独立后台进程，关 API 也持续跑</div>
            </div>
          </label>
        </div>
      </div>

      <FreshnessCard />

      <div className="text-sm font-medium mb-2">三个任务的状态</div>
      <div className="space-y-2 mb-4">
        {taskNames.map((name) => {
          const t = tasks[name] || ({} as (typeof tasks)[string]);
          const runDot = t.running ? "🟢 运行中" : enabled ? "⚪ 等待" : "⏸ 已停";
          const lastOk = t.last_ok ? new Date(t.last_ok).toLocaleString("zh-CN") : "—";
          const nextRun = t.next_run ? new Date(t.next_run).toLocaleString("zh-CN") : "—";
          return (
            <div key={name} className="p-3 rounded-xl bg-black/[0.03]">
              <div className="flex items-center justify-between mb-1">
                <div>
                  <span className="font-medium">{t.label || name}</span>
                  <span className="text-xs text-[var(--text-tertiary)] ml-2">{t.schedule || ""}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs">{runDot}</span>
                  {t.last_error && (
                    <span className="pill rose" style={{ fontSize: 10 }} title={t.last_error}>
                      {t.errors} 次错误
                    </span>
                  )}
                  <button
                    disabled={t.running || busy === name}
                    onClick={() => runNow(name)}
                    className="px-2 py-1 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-medium hover:bg-indigo-100 transition disabled:opacity-50"
                  >
                    立即跑
                  </button>
                </div>
              </div>
              <div className="text-xs text-[var(--text-tertiary)]">
                上次成功：{lastOk} · 下次：{nextRun} · 累计 {t.runs || 0} 次
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          disabled={busy === "start"}
          onClick={() => toggle(true)}
          className="px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-medium hover:bg-emerald-100 transition disabled:opacity-50"
        >
          ▶ 启动调度器
        </button>
        <button
          disabled={busy === "stop"}
          onClick={() => toggle(false)}
          className="px-3 py-1.5 rounded-lg bg-rose-50 text-rose-700 text-xs font-medium hover:bg-rose-100 transition disabled:opacity-50"
        >
          ⏸ 停止调度器
        </button>
      </div>
    </Card>
  );
}

function TokensSection() {
  const qc = useQueryClient();
  const { data: state } = useQuery({ queryKey: ["state"], queryFn: () => api.state() });
  const tokens =
    ((state?.global as { pushplus_tokens?: { name: string; token: string }[] } | undefined)
      ?.pushplus_tokens ?? []);
  const [name, setName] = useState("");
  const [token, setToken] = useState("");

  async function add() {
    if (!name.trim() || !token.trim()) {
      showToast("名字和 token 都必填", "error");
      return;
    }
    if (token.length < 20) {
      showToast("token 看起来不正确（< 20 字符）", "error");
      return;
    }
    const r = await api.addToken(name, token);
    if (r.ok) {
      showToast(`✓ token "${name}" 已添加`);
      setName("");
      setToken("");
      qc.invalidateQueries({ queryKey: ["state"] });
    } else showToast("失败：" + r.error, "error");
  }
  async function del(n: string) {
    if (!confirm(`确定删除 token "${n}"？`)) return;
    const r = await api.deleteToken(n);
    if (r.ok) {
      showToast(`✓ "${n}" 已删除`);
      qc.invalidateQueries({ queryKey: ["state"] });
    } else showToast("失败：" + r.error, "error");
  }
  return (
    <Card>
      <h3 className="text-lg font-medium mb-4">📱 PushPlus 微信推送</h3>
      <div className="space-y-2 mb-4">
        {tokens.length === 0 ? (
          <div className="text-sm text-[var(--text-tertiary)]">暂无 token</div>
        ) : (
          tokens.map((t) => (
            <div key={t.name} className="flex items-center justify-between p-3 rounded-xl bg-black/[0.03]">
              <div>
                <div className="font-medium">{t.name}</div>
                <div className="text-xs text-[var(--text-tertiary)] font-mono">
                  {t.token.slice(0, 4)}****{t.token.slice(-4)}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="pill green" style={{ fontSize: 11 }}>已激活</span>
                <button
                  onClick={() => del(t.name)}
                  className="text-xs text-rose-600 hover:bg-rose-50 px-2 py-1 rounded transition"
                >
                  删除
                </button>
              </div>
            </div>
          ))
        )}
      </div>
      <div className="p-4 rounded-2xl bg-indigo-50/50">
        <div className="text-sm font-medium mb-2">➕ 新增 token</div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            type="text"
            placeholder="名字（如 backup）"
            className="px-3 py-2 rounded-lg border border-black/10 text-sm w-40"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            type="text"
            placeholder="32 位 PushPlus token"
            className="px-3 py-2 rounded-lg border border-black/10 text-sm flex-1 w-full md:min-w-[280px] font-mono"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <button
            onClick={add}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition"
          >
            添加
          </button>
        </div>
        <div className="text-xs text-[var(--text-tertiary)] mt-2">
          去{" "}
          <a href="https://www.pushplus.plus" target="_blank" className="text-indigo-600 underline">
            pushplus.plus
          </a>{" "}
          微信扫码登录 → 复制 token 到这里
        </div>
      </div>
    </Card>
  );
}

function ItemsSection() {
  const qc = useQueryClient();
  const { data: state } = useQuery({ queryKey: ["state"], queryFn: () => api.state() });
  const { data: secs } = useQuery({ queryKey: ["sectors"], queryFn: () => api.sectorOptions() });
  const items =
    ((state?.items as { id: string; short_name?: string; name: string; image_url?: string; url?: string; history?: unknown[] }[] | undefined) ??
      []);
  const [form, setForm] = useState({
    url: "", name: "", short: "", sector: "",
    strong: "", primary: "", r1: "", r2: "", r3: "",
  });
  function reset() {
    setForm({ url: "", name: "", short: "", sector: "", strong: "", primary: "", r1: "", r2: "", r3: "" });
  }
  async function add() {
    if (!form.url || !form.name) return showToast("URL 和名称都必填", "error");
    if (!form.sector) return showToast("请选择板块", "error");
    if (!form.url.startsWith("https://www.steamdt.com/"))
      return showToast("URL 必须是 SteamDT 商品页", "error");
    const r = await api.addItem({
      url: form.url,
      name: form.name,
      short_name: form.short || null,
      sector: form.sector,
      strong_support: parseFloat(form.strong) || null,
      primary_support: parseFloat(form.primary) || null,
      resistance_1: parseFloat(form.r1) || null,
      resistance_2: parseFloat(form.r2) || null,
      resistance_3: parseFloat(form.r3) || null,
    });
    if (r.ok) {
      showToast(`✓ 品种已添加（id: ${r.data.id}），下次扫描自动抓取`);
      reset();
      qc.invalidateQueries({ queryKey: ["state"] });
    } else showToast("失败：" + r.error, "error");
  }
  async function del(id: string, dn: string) {
    if (!confirm(`确定删除 "${dn}"？历史数据也会一并清掉，且不可逆。`)) return;
    const r = await api.deleteItem(id);
    if (r.ok) {
      showToast(`✓ "${dn}" 已删除`);
      qc.invalidateQueries({ queryKey: ["state"] });
    } else showToast("失败：" + r.error, "error");
  }
  async function setImg(id: string, dn: string) {
    const url = window.prompt(
      `给"${dn}"设置 Steam CDN 图片 URL\n\n如何获取：\n1. 去 Steam 社区市场 / 第三方平台找到该饰品\n2. 右键饰品图 → "复制图片链接"\n3. URL 应该形如:\n   https://community.cloudflare.steamstatic.com/economy/image/...\n\n粘贴在下方:（留空则清除）`,
      ""
    );
    if (url === null) return;
    const r = await api.setItemImage(id, url.trim());
    if (r.ok) {
      showToast(url.trim() ? "✓ 图片已设置" : "✓ 图片已清除");
      qc.invalidateQueries({ queryKey: ["state"] });
    } else showToast("失败：" + r.error, "error");
  }

  return (
    <Card>
      <h3 className="text-lg font-medium mb-4">🎯 监控品种</h3>
      <div className="space-y-2 mb-4">
        {items.length === 0 ? (
          <div className="text-sm text-[var(--text-tertiary)]">暂无监控品种</div>
        ) : (
          items.map((it) => {
            const dn = it.short_name || it.name;
            return (
              <div key={it.id} className="flex items-center justify-between p-3 rounded-xl bg-black/[0.03]">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  {it.image_url ? (
                    <img
                      src={it.image_url}
                      alt=""
                      loading="lazy"
                      referrerPolicy="no-referrer"
                      className="w-10 h-10 rounded-lg object-contain bg-white/60 flex-shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-black/[0.06] flex items-center justify-center text-xs text-[var(--text-tertiary)] flex-shrink-0">
                      无图
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="font-medium">{dn}</div>
                    <div className="text-xs text-[var(--text-tertiary)] truncate">
                      {it.id} · {it.history?.length || 0} 条历史
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-3">
                  {it.url && (
                    <a href={it.url} target="_blank" className="text-xs text-indigo-600 hover:underline">
                      SteamDT ↗
                    </a>
                  )}
                  <button
                    onClick={() => setImg(it.id, dn)}
                    className="text-xs text-indigo-600 hover:bg-indigo-50 px-2 py-1 rounded transition"
                  >
                    {it.image_url ? "换图" : "设图"}
                  </button>
                  <button
                    onClick={() => del(it.id, dn)}
                    className="text-xs text-rose-600 hover:bg-rose-50 px-2 py-1 rounded transition"
                  >
                    删除
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="p-4 rounded-2xl bg-indigo-50/50">
        <div className="text-sm font-medium mb-3">➕ 新增监控品种</div>
        <div className="space-y-2">
          <input
            type="text"
            placeholder="SteamDT URL（必填，https://www.steamdt.com/...）"
            className="w-full px-3 py-2 rounded-lg border border-black/10 text-sm"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
          />
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              placeholder="完整名称（如 AWP | 二西莫夫 (崭新出厂)）"
              className="flex-1 w-full md:min-w-[260px] px-3 py-2 rounded-lg border border-black/10 text-sm"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <input
              type="text"
              placeholder="短名（推送显示）"
              className="flex-1 w-full md:min-w-[200px] px-3 py-2 rounded-lg border border-black/10 text-sm"
              value={form.short}
              onChange={(e) => setForm({ ...form, short: e.target.value })}
            />
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            <label className="text-xs text-[var(--text-secondary)]">板块：</label>
            <select
              className="px-3 py-2 rounded-lg border border-black/10 text-sm bg-white cursor-pointer"
              value={form.sector}
              onChange={(e) => setForm({ ...form, sector: e.target.value })}
            >
              <option value="">— 选择板块 —</option>
              {secs?.sectors.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <details className="text-sm">
            <summary className="cursor-pointer text-indigo-600 hover:underline py-1">
              关键位（可选，建议填以激活信号判定）
            </summary>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-2">
              <input type="number" step="0.01" placeholder="强支撑 ¥" className="px-3 py-2 rounded-lg border border-black/10 text-sm" value={form.strong} onChange={(e) => setForm({ ...form, strong: e.target.value })} />
              <input type="number" step="0.01" placeholder="主支撑 ¥" className="px-3 py-2 rounded-lg border border-black/10 text-sm" value={form.primary} onChange={(e) => setForm({ ...form, primary: e.target.value })} />
              <input type="number" step="0.01" placeholder="阻力 R1" className="px-3 py-2 rounded-lg border border-black/10 text-sm" value={form.r1} onChange={(e) => setForm({ ...form, r1: e.target.value })} />
              <input type="number" step="0.01" placeholder="阻力 R2" className="px-3 py-2 rounded-lg border border-black/10 text-sm" value={form.r2} onChange={(e) => setForm({ ...form, r2: e.target.value })} />
              <input type="number" step="0.01" placeholder="阻力 R3" className="px-3 py-2 rounded-lg border border-black/10 text-sm" value={form.r3} onChange={(e) => setForm({ ...form, r3: e.target.value })} />
            </div>
          </details>
          <button
            onClick={add}
            className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition"
          >
            添加品种
          </button>
        </div>
        <div className="text-xs text-[var(--text-tertiary)] mt-2">
          添加后下次 fast 任务自动开始抓取（约 10 分钟内）。
        </div>
      </div>
    </Card>
  );
}

function LLMSection() {
  const qc = useQueryClient();
  const { data: cfg } = useQuery({ queryKey: ["llm-config"], queryFn: () => api.llmConfig() });
  const [form, setForm] = useState({
    provider: "anthropic",
    model: "",
    api_key: "",
    base_url: "",
    news: false,
    review: false,
    proposal: false,
  });
  const [test, setTest] = useState<{ text: string; color: string }>({ text: "", color: "" });
  const [classify, setClassify] = useState<{ text: string; color: string }>({ text: "", color: "" });

  useEffect(() => {
    if (!cfg) return;
    setForm({
      provider: cfg.provider || "anthropic",
      model: cfg.model || "",
      api_key: "",
      base_url: cfg.base_url || "",
      news: !!cfg.enabled_modules?.news_classification,
      review: !!cfg.enabled_modules?.daily_review,
      proposal: !!cfg.enabled_modules?.param_proposal,
    });
  }, [cfg]);

  async function save() {
    if (!form.model) return showToast("Model 必填", "error");
    const r = await api.saveLLMConfig({
      provider: form.provider,
      model: form.model,
      api_key: form.api_key || null,
      base_url: form.base_url,
      enabled_modules: {
        news_classification: form.news,
        daily_review: form.review,
        param_proposal: form.proposal,
      },
    });
    if (r.ok) {
      showToast("✓ LLM 配置已保存");
      qc.invalidateQueries({ queryKey: ["llm-config"] });
    } else showToast("保存失败：" + r.error, "error");
  }

  async function testConn() {
    setTest({ text: "测试中...", color: "#6E6E73" });
    const r = await api.testLLM();
    if (r.ok && r.data?.ok) {
      setTest({
        text: `✓ 连通 ${r.data.latency_ms}ms · ${r.data.model} · 回 "${r.data.response}"`,
        color: "#10B981",
      });
    } else {
      const err = (r.ok ? r.data?.error : (r as { error?: string }).error) || "未知错误";
      setTest({ text: `✗ ${err}`, color: "#EF4444" });
    }
  }

  async function runClassify() {
    setClassify({ text: "抓 Steam News + 调 LLM...（最多约 90 秒，请耐心等）", color: "#6E6E73" });
    const r = await api.classifyNewsNow();
    if (r.ok) {
      const n = (r.data.items || []).length;
      setClassify({ text: `✓ 分类 ${n} 条 → 综合 bias=${r.data.aggregate_bias}`, color: "#10B981" });
      qc.invalidateQueries({ queryKey: ["fundamentals"] });
    } else {
      setClassify({ text: `✗ ${r.error}`, color: "#EF4444" });
    }
  }

  const apiPlaceholder = cfg?.configured
    ? `已配置: ${cfg.api_key_masked} (留空保持不变)`
    : "sk-... (脱敏存储于 state.json)";

  return (
    <Card>
      <h3 className="text-lg font-medium mb-4">🤖 大模型接入（Phase 1：新闻语义分类）</h3>
      <div className="space-y-3 mb-4">
        <div className="flex flex-wrap gap-2 items-center">
          <label className="text-xs text-[var(--text-secondary)] w-20">Provider</label>
          <select
            className="px-3 py-2 rounded-lg border border-black/10 text-sm bg-white"
            value={form.provider}
            onChange={(e) => setForm({ ...form, provider: e.target.value })}
          >
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
            <option value="custom">自定义 (DeepSeek / Qwen / Moonshot / 自托管)</option>
          </select>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <label className="text-xs text-[var(--text-secondary)] w-20">Model</label>
          <input
            type="text"
            placeholder="如 claude-sonnet-4-6 / gpt-4o-mini / deepseek-chat"
            className="flex-1 w-full md:min-w-[280px] px-3 py-2 rounded-lg border border-black/10 text-sm"
            value={form.model}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
          />
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <label className="text-xs text-[var(--text-secondary)] w-20">API Key</label>
          <input
            type="password"
            placeholder={apiPlaceholder}
            className="flex-1 w-full md:min-w-[280px] px-3 py-2 rounded-lg border border-black/10 text-sm font-mono"
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
          />
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <label className="text-xs text-[var(--text-secondary)] w-20">Base URL</label>
          <input
            type="text"
            placeholder="留空用默认；自定义如 https://api.deepseek.com/v1"
            className="flex-1 w-full md:min-w-[280px] px-3 py-2 rounded-lg border border-black/10 text-sm font-mono"
            value={form.base_url}
            onChange={(e) => setForm({ ...form, base_url: e.target.value })}
          />
        </div>
        <div className="flex flex-wrap gap-2 items-center mt-2">
          <button onClick={save} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition">
            保存配置
          </button>
          <button onClick={testConn} className="px-4 py-2 rounded-lg bg-emerald-50 text-emerald-700 text-sm font-medium hover:bg-emerald-100 transition">
            测试连通
          </button>
          <span className="text-xs" style={{ color: test.color }}>{test.text}</span>
        </div>
      </div>

      <div className="border-t border-black/5 pt-4">
        <div className="text-sm font-medium mb-2">启用模块</div>
        <div className="space-y-2 text-sm">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.news} onChange={(e) => setForm({ ...form, news: e.target.checked })} />
            <span>新闻语义分类</span>
            <span className="text-xs text-[var(--text-tertiary)]">
              (替代关键词，用 LLM 读 Steam News 写 fundamentals.bias)
            </span>
          </label>
          <label className="flex items-center gap-2 cursor-not-allowed opacity-50">
            <input type="checkbox" disabled />
            <span>庄家公告解析</span>
            <span className="text-xs text-[var(--text-tertiary)]">(Phase 2，待开放)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.review} onChange={(e) => setForm({ ...form, review: e.target.checked })} />
            <span>每日复盘评论</span>
            <span className="text-xs text-[var(--text-tertiary)]">
              (daily_review 时自动生成 AI 评论，写入 ai_review)
            </span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.proposal} onChange={(e) => setForm({ ...form, proposal: e.target.checked })} />
            <span>参数调整提案</span>
            <span className="text-xs text-[var(--text-tertiary)]">
              (看 shadow 数据生成提案，需 ≥5 条样本)
            </span>
          </label>
        </div>
        <div className="flex flex-wrap gap-2 items-center mt-4">
          <button onClick={runClassify} className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-medium hover:bg-indigo-100 transition">
            立即跑一次新闻分类
          </button>
          <span className="text-xs" style={{ color: classify.color }}>{classify.text}</span>
        </div>
      </div>

      <div className="mt-4 p-3 rounded-xl bg-amber-50/60 text-xs text-amber-900 leading-relaxed">
        ⚠️ API key 会以明文存到{" "}
        <code className="bg-white px-1 rounded">m4a4_buzz_kill_state.json</code>。
        该文件仅在你本地，但请不要把 state.json 上传到任何代码仓库。
      </div>
    </Card>
  );
}

function WhaleToggleSection() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["whale"], queryFn: () => api.whaleToggle() });
  const [status, setStatus] = useState<{ text: string; color: string }>({ text: "", color: "" });

  async function save(checked: boolean) {
    setStatus({ text: "保存中...", color: "#6E6E73" });
    const r = await api.setWhaleToggle(checked);
    if (r.ok) {
      setStatus({ text: checked ? "✓ 已屏蔽" : "✓ 已启用", color: "#10B981" });
      qc.invalidateQueries({ queryKey: ["whale"] });
      setTimeout(() => setStatus({ text: "", color: "" }), 2000);
    } else {
      setStatus({ text: "✗ " + r.error, color: "#EF4444" });
    }
  }

  return (
    <Card>
      <h3 className="text-lg font-medium mb-4">🎚️ 策略行为开关</h3>
      <label className="flex items-start gap-3 cursor-pointer p-3 rounded-xl hover:bg-black/[0.02] transition">
        <input
          type="checkbox"
          className="mt-1 cursor-pointer"
          checked={!!data?.ignore_whale_signals}
          onChange={(e) => save(e.target.checked)}
        />
        <div className="flex-1">
          <div className="font-medium text-sm">屏蔽庄家信号干扰</div>
          <div className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
            勾选后，系统将无视所有庄家相关规则：
            <span className="text-[var(--text-tertiary)]">
              {" "}BUY-WHALE 不再触发 · A1-WHALE-STOP 止损不再激活 · bias 不会升级到 positive_with_whale_buy
            </span>
          </div>
          <div className="text-xs text-[var(--text-tertiary)] mt-1">
            适合：你不相信庄家公告 / 想让系统纯按技术信号决策。
          </div>
        </div>
        <span className="text-xs" style={{ color: status.color }}>{status.text}</span>
      </label>
    </Card>
  );
}

function FundamentalsSection() {
  const { data: fund } = useQuery<Fundamentals | null>({
    queryKey: ["fundamentals"],
    queryFn: () => api.fundamentals(),
  });
  if (!fund) {
    return (
      <Card>
        <h3 className="text-lg font-medium mb-4">🌍 基本面</h3>
        <div className="text-sm space-y-2">加载中...</div>
      </Card>
    );
  }

  const methodBadge =
    fund.last_check_method === "llm" ? (
      <span className="pill" style={{ background: "rgba(99,102,241,0.1)", color: "#6366F1", fontSize: 11 }}>
        LLM 分析
      </span>
    ) : fund.last_check_method === "keyword" ? (
      <span className="pill" style={{ background: "rgba(0,0,0,0.06)", color: "#6E6E73", fontSize: 11 }}>
        关键词
      </span>
    ) : null;

  const updates = (fund.recent_updates ?? []) as Array<{
    title?: string;
    topic?: string;       // 老字段名（关键词分类器写入）
    summary?: string;     // 备用：LLM 写入
    impact?: string;
    date?: string;
    type?: string;
    confidence?: number;
    rationale?: string;
    url?: string;
  }>;
  // type 短中文标签
  const TYPE_LABEL: Record<string, string> = {
    whale: "庄家",
    minor: "小更新",
    major: "大更新",
    tech: "技术",
    season: "赛季",
    case: "箱子",
    update: "更新",
  };
  // impact 长 string 缩短显示
  function shortImpact(s?: string) {
    if (!s) return "—";
    return s
      .replace("_short_term", "·短期")
      .replace("_long_term", "·长期")
      .replace("strong_", "强")
      .replace("with_whale_buy", "+庄家");
  }
  const impact = BIAS_IMPACT[fund.bias || "neutral"] || BIAS_IMPACT.neutral;

  return (
    <Card>
      <h3 className="text-lg font-medium mb-4">🌍 基本面</h3>
      <div className="text-sm space-y-2">
        <div>
          当前 bias：<strong>{fund.bias || "未知"}</strong> {methodBadge}
        </div>
        <div>最近检查：{fund.last_check_time || "—"}</div>
        <div>下次检查：{fund.next_check_due || "—"}</div>
        <div className="text-[var(--text-secondary)] mt-2">{(fund.summary || "").slice(0, 400)}</div>
        {!!fund.whale_signals?.length && (
          <div className="mt-3 p-3 rounded-xl bg-indigo-50/50">
            活跃庄家信号：{fund.whale_signals.length} 条
          </div>
        )}
        <div className="mt-3 p-3 rounded-xl bg-gradient-to-r from-indigo-50/50 to-purple-50/30 border border-indigo-100/50">
          <div className="text-xs font-medium text-[var(--text-secondary)] mb-2">
            📊 当前 bias 实际影响（A+B 调节器）
          </div>
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div>
              <div className="text-[var(--text-tertiary)]">BUY 优先级</div>
              <div
                className={`font-mono font-medium ${
                  impact.buy_pri === "屏蔽"
                    ? "text-rose-600"
                    : impact.buy_pri.startsWith("+")
                    ? "text-emerald-600"
                    : "text-slate-700"
                }`}
              >
                {impact.buy_pri}
              </div>
            </div>
            <div>
              <div className="text-[var(--text-tertiary)]">止损阈值</div>
              <div className="font-mono font-medium">{impact.stop_mult}</div>
            </div>
            <div>
              <div className="text-[var(--text-tertiary)]">止盈阈值</div>
              <div className="font-mono font-medium">{impact.tp_mult}</div>
            </div>
          </div>
          <div className="text-xs text-[var(--text-secondary)] mt-2">{impact.desc}</div>
        </div>
        {updates.length > 0 && (
          <details className="mt-4">
            <summary className="cursor-pointer text-indigo-600 hover:underline text-sm font-medium">
              📋 查看逐条分析（{updates.length} 条）
            </summary>
            <div className="mt-3 space-y-2 max-h-96 overflow-y-auto pr-2">
              {updates.map((u, i) => {
                const headline = u.title || u.topic || u.summary || "—";
                const typeLabel = u.type ? TYPE_LABEL[u.type] || u.type : "—";
                return (
                  <div key={i} className="p-3 rounded-xl border border-black/5 bg-white">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="text-sm font-medium flex-1 min-w-0">{headline}</div>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${biasColor(u.impact)}`}
                        title={u.impact || ""}
                      >
                        {shortImpact(u.impact)}
                      </span>
                    </div>
                    <div className="text-xs text-[var(--text-tertiary)] mb-1">
                      {u.date || "—"} · {typeLabel}
                      {u.confidence != null ? ` · 置信 ${(u.confidence * 100).toFixed(0)}%` : ""}
                    </div>
                    {u.rationale && (
                      <div className="text-xs text-[var(--text-secondary)] mt-1">💭 {u.rationale}</div>
                    )}
                    {u.url && (
                      <a href={u.url} target="_blank" className="text-xs text-indigo-600 hover:underline mt-1 inline-block">
                        查看原文 ↗
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          </details>
        )}
      </div>
    </Card>
  );
}

function DataDirSection() {
  const { data } = useQuery({ queryKey: ["data-dir"], queryFn: () => api.dataDir() });
  const [result, setResult] = useState<{ text: string; color: string }>({ text: "", color: "" });

  async function open() {
    const r = await api.openDataDir();
    if (r.ok) {
      setResult({ text: "✓ 已打开", color: "#10B981" });
      setTimeout(() => setResult({ text: "", color: "" }), 2000);
    } else {
      setResult({ text: "✗ 失败：" + r.error, color: "#EF4444" });
    }
  }
  async function copy() {
    if (!data?.data_dir) return;
    try {
      await navigator.clipboard.writeText(data.data_dir);
      setResult({ text: "✓ 路径已复制", color: "#10B981" });
      setTimeout(() => setResult({ text: "", color: "" }), 2000);
    } catch {
      setResult({ text: "✗ 剪贴板访问失败", color: "#EF4444" });
    }
  }

  let source = "—";
  if (data) {
    if (data.from_env) source = "来源：环境变量 SENTINEL_DATA_DIR";
    else if (data.data_dir.toLowerCase().includes("appdata"))
      source = "来源：%APPDATA% (Windows 默认，跟随用户账号)";
    else if (data.data_dir === data.project_dir) source = "来源：安装目录（兜底，未启用持久化）";
    else source = "来源：用户主目录";
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-medium">📁 数据目录</h3>
        <span className="pill" style={{ fontSize: 11 }}>v2.1+ 持久化</span>
      </div>
      <p className="text-xs text-[var(--text-tertiary)] mb-3">
        所有用户数据（state.json / shadow / cookies / 截图 / 日志）保存在此目录，
        <b>跨版本升级 0 迁移</b>。把新版本解压到任意位置，启动后会自动从这里读取数据。
      </p>
      <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-200/60 mb-3">
        <div className="text-xs text-[var(--text-tertiary)] mb-1">当前数据目录</div>
        <code className="text-xs font-mono break-all text-slate-700">
          {data?.data_dir || "检测中..."}
        </code>
        <div className="text-[11px] text-[var(--text-tertiary)] mt-1">{source}</div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button onClick={open} className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-medium hover:bg-indigo-100 transition">
          📂 打开数据目录
        </button>
        <button onClick={copy} className="px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 text-xs font-medium hover:bg-slate-200 transition">
          📋 复制路径
        </button>
        <span className="text-xs self-center" style={{ color: result.color }}>{result.text}</span>
      </div>
    </Card>
  );
}

function LanAccessSection() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["lan-config"],
    queryFn: () => api.lanConfig(),
    refetchInterval: 30_000,
  });
  const [showToken, setShowToken] = useState(false);
  const [busy, setBusy] = useState(false);
  const [selectedIp, setSelectedIp] = useState<string>("");
  const qrRef = useRef<HTMLCanvasElement>(null);

  // 选第一个 LAN IP 作为 QR 默认
  useEffect(() => {
    if (!selectedIp && data?.ips?.length) setSelectedIp(data.ips[0]);
  }, [data, selectedIp]);

  // 渲染 QR 码 — 信任内网模式用纯 URL，否则带 ?token=
  useEffect(() => {
    if (!data || !selectedIp || !qrRef.current) return;
    const base = `http://${selectedIp}:${data.port}`;
    const url = data.trust_private ? `${base}/` : `${base}/?token=${data.token}`;
    QRCode.toCanvas(qrRef.current, url, { width: 220, margin: 1 }).catch(() => {});
  }, [data, selectedIp]);

  async function toggleEnabled(enabled: boolean) {
    setBusy(true);
    const r = await api.setLanConfig({ enabled });
    setBusy(false);
    if (r.ok) {
      showToast("✓ 已保存。重启 backend 后生效");
      qc.invalidateQueries({ queryKey: ["lan-config"] });
    } else {
      showToast("失败：" + r.error, "error");
    }
  }

  async function toggleTrust(trust: boolean) {
    if (trust) {
      const ok = confirm(
        "开启「内网设备免 token」后，同一 WiFi 下的任何设备都能修改你的仓位/调度/品种，无需 token。\n\n" +
          "✓ 适合：自己家 WiFi、独立路由器\n" +
          "✗ 不要在公共 WiFi（咖啡店/办公室/校园网）开\n\n" +
          "继续？"
      );
      if (!ok) return;
    }
    setBusy(true);
    const r = await api.setLanConfig({ trust_private: trust });
    setBusy(false);
    if (r.ok) {
      showToast(trust ? "✓ 内网信任已开（实时生效）" : "✓ 内网信任已关，恢复 token 鉴权");
      qc.invalidateQueries({ queryKey: ["lan-config"] });
    } else {
      showToast("失败：" + r.error, "error");
    }
  }

  async function resetTok() {
    if (!confirm("重置 Token 后所有手机端会话失效，需重新扫码。继续？")) return;
    const r = await api.resetLanToken();
    if (r.ok) {
      showToast("✓ 已重置");
      if (getToken()) setToken(r.data.token);
      qc.invalidateQueries({ queryKey: ["lan-config"] });
    } else showToast("失败：" + r.error, "error");
  }

  function copyURL() {
    if (!data || !selectedIp) return;
    const base = `http://${selectedIp}:${data.port}`;
    const url = data.trust_private ? `${base}/` : `${base}/?token=${data.token}`;
    navigator.clipboard.writeText(url).then(
      () => showToast("✓ URL 已复制"),
      () => showToast("剪贴板访问失败", "error")
    );
  }

  const tokenMasked = data?.token
    ? data.token.slice(0, 6) + "•".repeat(20) + data.token.slice(-6)
    : "—";

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-medium">📱 局域网访问 / 手机端</h3>
        <span
          className={data?.enabled ? "pill green" : "pill"}
          style={{ fontSize: 11 }}
        >
          {data?.enabled
            ? data?.trust_private
              ? "🟢 LAN + 内网信任"
              : "🟢 LAN（token 模式）"
            : "🔒 仅本机"}
        </span>
      </div>
      <p className="text-xs text-[var(--text-tertiary)] mb-4 leading-relaxed">
        启用后 backend 绑定 0.0.0.0:8000，手机连同 WiFi 可访问。
        <b>切换需要重启 backend</b>（关 Sentinel 窗口或退出托盘程序后重开）。
      </p>

      {/* 1. LAN 模式开关 */}
      <label className="flex items-start gap-3 cursor-pointer p-3 rounded-xl hover:bg-black/[0.02] transition mb-3">
        <input
          type="checkbox"
          className="mt-1 cursor-pointer"
          disabled={busy}
          checked={!!data?.enabled}
          onChange={(e) => toggleEnabled(e.target.checked)}
        />
        <div className="flex-1">
          <div className="font-medium text-sm">① 允许局域网访问（绑定 0.0.0.0）</div>
          <div className="text-xs text-[var(--text-secondary)] mt-1">
            关闭 = 仅本机回环（默认）。开启时 Windows 防火墙首次会弹询问 → 选「专用网络」。
          </div>
        </div>
      </label>

      {/* 2. 内网信任模式 */}
      {data?.enabled && (
        <label className="flex items-start gap-3 cursor-pointer p-3 rounded-xl hover:bg-black/[0.02] transition mb-4 border border-amber-200/60 bg-amber-50/30">
          <input
            type="checkbox"
            className="mt-1 cursor-pointer"
            disabled={busy}
            checked={!!data?.trust_private}
            onChange={(e) => toggleTrust(e.target.checked)}
          />
          <div className="flex-1">
            <div className="font-medium text-sm">
              ② 内网设备免 token（同 WiFi 直接输 URL 就能用）
              <span className="ml-2 text-xs text-amber-700">实时生效，不需要重启</span>
            </div>
            <div className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
              开启后：来自私网 IP（192.168.x.x / 10.x.x.x / 172.16-31.x.x / IPv6 ULA）的请求都
              <b>不需要 X-Sentinel-Token</b>。
              手机连同 WiFi → Chrome 直接输 <code className="bg-white px-1 rounded">http://192.168.x.x:8000</code> 就能 CRUD。
              <br />
              <span className="text-amber-700">⚠️ 公共 WiFi（咖啡店/办公室）下不要开 — 同网段任何人都能改你数据。</span>
            </div>
          </div>
        </label>
      )}

      {data?.enabled && (
        <>
          {/* IP 列表 + QR 码 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <div className="text-xs text-[var(--text-tertiary)] mb-2">
                本机 IP（在手机 Chrome 输入下面任一 URL）
              </div>
              {data.ips?.length ? (
                <div className="space-y-1">
                  {data.ips.map((ip) => (
                    <label
                      key={ip}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer border transition ${
                        selectedIp === ip
                          ? "bg-indigo-50 border-indigo-200"
                          : "bg-white border-black/5 hover:bg-black/[0.02]"
                      }`}
                    >
                      <input
                        type="radio"
                        checked={selectedIp === ip}
                        onChange={() => setSelectedIp(ip)}
                      />
                      <code className="font-mono select-all">{`http://${ip}:${data.port}`}</code>
                    </label>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-[var(--text-tertiary)]">未检测到 LAN IP</div>
              )}
              <button
                onClick={copyURL}
                className="mt-3 px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-medium hover:bg-indigo-100 transition"
              >
                {data.trust_private ? "📋 复制纯 URL" : "📋 复制完整 URL（含 token）"}
              </button>
            </div>
            <div className="flex flex-col items-center justify-start">
              <div className="text-xs text-[var(--text-tertiary)] mb-2">
                {data.trust_private ? "或扫码（无 token，纯 URL）" : "手机 Chrome 扫码"}
              </div>
              <div className="p-2 rounded-lg bg-white border border-black/10">
                <canvas ref={qrRef} />
              </div>
              <div className="text-[11px] text-[var(--text-tertiary)] mt-2">
                {data.trust_private
                  ? "QR 内容：纯 LAN URL"
                  : "扫码后浏览器自动入库 token"}
              </div>
            </div>
          </div>

          {/* Token 管理（仅 token 模式下显示） */}
          {!data.trust_private && (
            <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-200/60">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-[var(--text-tertiary)]">X-Sentinel-Token</div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowToken((v) => !v)}
                    className="text-xs px-2 py-1 rounded bg-white border border-black/10 hover:bg-black/[0.04]"
                  >
                    {showToken ? "隐藏" : "显示"}
                  </button>
                  <button
                    onClick={resetTok}
                    className="text-xs px-2 py-1 rounded bg-rose-50 text-rose-700 hover:bg-rose-100"
                  >
                    重置 Token
                  </button>
                </div>
              </div>
              <code className="text-xs font-mono break-all text-slate-700 select-all">
                {showToken ? data.token : tokenMasked}
              </code>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

export default function Settings() {
  return (
    <div style={{ paddingTop: 100 }}>
      <section className="py-12 px-6 max-w-4xl mx-auto">
        <h2 className="text-4xl font-semibold tracking-tight mb-3">设置</h2>
        <p className="text-[var(--text-secondary)] mb-10">
          PushPlus 推送 token + 监控品种 + 系统参数。
        </p>
        <div className="space-y-10">
          <TokensSection />
          <ItemsSection />
          <LLMSection />
          <WhaleToggleSection />
          <FundamentalsSection />
          <SchedulerSection />
          <LanAccessSection />
          <DataDirSection />
        </div>
      </section>
    </div>
  );
}
