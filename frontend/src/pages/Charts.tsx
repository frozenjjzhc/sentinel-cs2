import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, HistoryEntry, ItemSummary } from "@/lib/api";
import { fmtPrice, fmtPct, pctClass } from "@/lib/format";

type ChartType = "line" | "kline";
type KlineGran = "hour" | "day";

type Candle = {
  t: string;
  bucket: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

// 把 raw points 按时间桶聚合成 OHLC + 成交量增量
// today_volume 是当日累计；先算每点增量，再按桶求和；午夜跨日 reset 时取当桶 today_volume 作增量
function aggregateBuckets(points: HistoryEntry[], bucketMs: number): Candle[] {
  const sorted = [...points]
    .filter((p) => p.price != null)
    .sort((a, b) => new Date(a.t).getTime() - new Date(b.t).getTime());

  let prevVol: number | null = null;
  const annotated = sorted.map((p) => {
    const curVol = p.today_volume || 0;
    let inc = 0;
    if (prevVol !== null) {
      const delta = curVol - prevVol;
      inc = delta < 0 ? curVol : delta;
    }
    prevVol = curVol;
    return { ...p, _incVol: inc };
  });

  const groups = new Map<number, typeof annotated>();
  for (const p of annotated) {
    const t = new Date(p.t).getTime();
    const bucket = Math.floor(t / bucketMs) * bucketMs;
    if (!groups.has(bucket)) groups.set(bucket, []);
    groups.get(bucket)!.push(p);
  }

  return [...groups.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([bucket, slice]) => {
      const ps = slice.map((p) => p.price as number);
      const incSum = slice.reduce((s, p) => s + (p._incVol || 0), 0);
      return {
        t: new Date(bucket).toISOString(),
        bucket,
        open: ps[0],
        high: Math.max(...ps),
        low: Math.min(...ps),
        close: ps[ps.length - 1],
        volume: incSum,
      };
    });
}

type HoverPoint = {
  t: string;
  price: number;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  today_volume?: number;
  today_pct?: number | null;
  week_pct?: number | null;
  market_index?: number | null;
};

export default function Charts() {
  const items = useQuery({ queryKey: ["items"], queryFn: () => api.items() });
  const [itemId, setItemId] = useState<string>("");
  const [type, setType] = useState<ChartType>("line");
  const [hours, setHours] = useState(24);
  const [kline, setKline] = useState<KlineGran>("hour");

  // 默认选中第一个
  useEffect(() => {
    if (!itemId && items.data?.items?.[0]) setItemId(items.data.items[0].id);
  }, [items.data, itemId]);

  const fetchHours = type === "line" ? hours : kline === "hour" ? 72 : 30 * 24;

  const item = useQuery({
    queryKey: ["item", itemId],
    queryFn: () => api.item(itemId),
    enabled: !!itemId,
  });
  const hist = useQuery({
    queryKey: ["history", itemId, fetchHours],
    queryFn: () => api.itemHistory(itemId, fetchHours),
    enabled: !!itemId,
  });

  const rawPoints = (hist.data?.history ?? []).filter((h) => h.price != null);

  const candles = useMemo(() => {
    if (type !== "kline" || rawPoints.length < 2) return null;
    const bucketMs = kline === "hour" ? 3_600_000 : 86_400_000;
    return aggregateBuckets(rawPoints, bucketMs);
  }, [type, kline, rawPoints]);

  return (
    <div style={{ paddingTop: 100 }}>
      <section className="relative py-12 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="mb-10">
            <h2 className="text-4xl font-semibold tracking-tight mb-3">走势图</h2>
            <p className="text-[var(--text-secondary)]">选择品种查看实时价格趋势 + 成交量。</p>
          </div>

          <div className="flex flex-wrap items-center gap-3 mb-8">
            <select
              value={itemId}
              onChange={(e) => setItemId(e.target.value)}
              className="w-full sm:w-auto px-4 py-2.5 rounded-full border border-black/10 bg-white text-sm font-medium cursor-pointer hover:border-black/20 transition"
            >
              {items.data?.items.map((it) => (
                <option key={it.id} value={it.id}>
                  {it.short_name || it.name}
                </option>
              )) ?? <option>加载中...</option>}
            </select>

            <div className="flex items-center gap-1 p-1 rounded-full bg-black/[0.04]">
              <button
                className={`chart-type-btn ${type === "line" ? "active" : ""}`}
                onClick={() => setType("line")}
              >
                折线
              </button>
              <button
                className={`chart-type-btn ${type === "kline" ? "active" : ""}`}
                onClick={() => setType("kline")}
              >
                K 线
              </button>
            </div>

            {type === "line" ? (
              <div className="flex items-center gap-1 p-1 rounded-full bg-black/[0.04]">
                {[24, 72, 168].map((h) => (
                  <button
                    key={h}
                    className={`chart-range-btn ${hours === h ? "active" : ""}`}
                    onClick={() => setHours(h)}
                  >
                    {h === 24 ? "24H" : h === 72 ? "3D" : "7D"}
                  </button>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-1 p-1 rounded-full bg-black/[0.04]">
                <button
                  className={`chart-kline-btn ${kline === "hour" ? "active" : ""}`}
                  onClick={() => setKline("hour")}
                >
                  时K
                </button>
                <button
                  className={`chart-kline-btn ${kline === "day" ? "active" : ""}`}
                  onClick={() => setKline("day")}
                >
                  日K
                </button>
              </div>
            )}

            <button
              onClick={() => hist.refetch()}
              className="px-4 py-2.5 rounded-full bg-indigo-50 text-indigo-600 text-sm font-medium hover:bg-indigo-100 transition cursor-pointer"
            >
              ↻ 刷新
            </button>
          </div>

          <ChartCard
            type={type}
            kline={kline}
            hours={hours}
            item={item.data}
            rawPoints={rawPoints}
            candles={candles}
            count={hist.data?.count ?? 0}
          />
        </div>
      </section>
    </div>
  );
}

function ChartCard(props: {
  type: ChartType;
  kline: KlineGran;
  hours: number;
  item: ItemSummary | null | undefined;
  rawPoints: HistoryEntry[];
  candles: Candle[] | null;
  count: number;
}) {
  const { type, kline, hours, item, rawPoints, candles, count } = props;
  const wrapRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const crosshairRef = useRef<SVGLineElement>(null);
  const volCrossRef = useRef<SVGLineElement>(null);
  const dotRef = useRef<SVGCircleElement>(null);

  const W = 800;
  const H = 320;

  const series: HistoryEntry[] | Candle[] = candles || rawPoints;
  const N = series.length;

  // X 轴：按真实时间位置（不是 index）
  const tStart = N > 0 ? new Date(series[0].t).getTime() : 0;
  const tEnd = N > 0 ? new Date(series[N - 1].t).getTime() : 1;
  const tRange = Math.max(1, tEnd - tStart);
  const xPosOf = (p: { t: string }) => ((new Date(p.t).getTime() - tStart) / tRange) * W;

  const allPrices = candles
    ? candles.flatMap((c) => [c.high, c.low])
    : rawPoints.map((p) => p.price as number);
  const min = allPrices.length ? Math.min(...allPrices) * 0.998 : 0;
  const max = allPrices.length ? Math.max(...allPrices) * 1.002 : 1;
  const yScale = (p: number) => H - ((p - min) / (max - min)) * H;

  // 折线路径
  let lineD = "";
  let areaD = "";
  if (type === "line" && rawPoints.length >= 2) {
    rawPoints.forEach((p, i) => {
      const x = xPosOf(p);
      const y = yScale(p.price as number);
      if (i === 0) {
        lineD = `M ${x},${y}`;
      } else {
        const prevX = xPosOf(rawPoints[i - 1]);
        const prevY = yScale(rawPoints[i - 1].price as number);
        const cx = (prevX + x) / 2;
        const cy = (prevY + y) / 2;
        lineD += ` Q ${cx},${cy} ${x},${y}`;
      }
    });
    const lastX = xPosOf(rawPoints[rawPoints.length - 1]);
    const firstX = xPosOf(rawPoints[0]);
    areaD = lineD + ` L ${lastX},${H} L ${firstX},${H} Z`;
  }

  // K 线 candle 宽度
  let candleW = 6;
  if (candles && candles.length > 1) {
    let minGap = W;
    for (let i = 1; i < candles.length; i++) {
      const gap = xPosOf(candles[i]) - xPosOf(candles[i - 1]);
      if (gap < minGap) minGap = gap;
    }
    candleW = Math.max(2, Math.min(20, minGap * 0.7));
  }

  // 成交量参数
  const VW = 800;
  const VH = 80;
  const maxVol = candles ? Math.max(1, ...candles.map((c) => c.volume)) : 1;
  const vxPosOf = (p: { t: string }) => ((new Date(p.t).getTime() - tStart) / tRange) * VW;

  // X 轴标签
  const NUM_TICKS = 6;
  const fmtTick = (date: Date) => {
    const mo = (date.getMonth() + 1).toString().padStart(2, "0");
    const da = date.getDate().toString().padStart(2, "0");
    const hh = date.getHours().toString().padStart(2, "0");
    const mm = date.getMinutes().toString().padStart(2, "0");
    if (type === "kline" && kline === "day") return `${mo}-${da}`;
    if (type === "kline" && kline === "hour") return `${mo}-${da} ${hh}h`;
    if (type === "line" && hours > 24) return `${mo}-${da} ${hh}h`;
    return `${hh}:${mm}`;
  };
  const ticks: string[] = [];
  if (N > 0) {
    for (let i = 0; i < NUM_TICKS; i++) {
      const tick = tStart + (tEnd - tStart) * (i / (NUM_TICKS - 1));
      ticks.push(fmtTick(new Date(tick)));
    }
  }

  // hover 数据
  const hoverPoints: HoverPoint[] = candles
    ? candles.map((c) => ({
        t: c.t,
        price: c.close,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        today_volume: c.volume,
      }))
    : rawPoints.map((p) => ({
        t: p.t,
        price: p.price as number,
        today_volume: p.today_volume ?? 0,
        today_pct: p.today_pct,
        week_pct: p.week_pct,
        market_index: p.market_index,
      }));
  const hoverPosX = candles ? candles.map((c) => xPosOf(c)) : rawPoints.map((p) => xPosOf(p));

  // hover/touch 共用逻辑
  function _moveAt(clientX: number, clientY: number) {
    if (!hoverPoints.length || !wrapRef.current) return;
    const rect = wrapRef.current.getBoundingClientRect();
    const relX = clientX - rect.left;
    const relY = clientY - rect.top;
    const mouseVBX = (relX / rect.width) * W;

    let idx = 0;
    let minDist = Infinity;
    for (let i = 0; i < hoverPosX.length; i++) {
      const d = Math.abs(hoverPosX[i] - mouseVBX);
      if (d < minDist) {
        minDist = d;
        idx = i;
      }
    }
    const p = hoverPoints[idx];
    if (!p) return;

    const xVB = hoverPosX[idx];
    const yVB = yScale(p.price);

    crosshairRef.current?.setAttribute("x1", String(xVB));
    crosshairRef.current?.setAttribute("x2", String(xVB));
    crosshairRef.current?.setAttribute("opacity", "0.6");

    volCrossRef.current?.setAttribute("x1", String(xVB));
    volCrossRef.current?.setAttribute("x2", String(xVB));
    volCrossRef.current?.setAttribute("opacity", "0.6");

    dotRef.current?.setAttribute("cx", String(xVB));
    dotRef.current?.setAttribute("cy", String(yVB));
    dotRef.current?.setAttribute("opacity", "1");

    const tooltip = tooltipRef.current;
    if (!tooltip) return;

    const d = new Date(p.t);
    const dateStr = d.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
    const timeStr = d.toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });

    if (type === "kline" && p.open != null) {
      const upClr = p.close! >= p.open ? "#34D399" : "#FB7185";
      const change = p.open ? ((p.close! - p.open) / p.open) * 100 : 0;
      tooltip.innerHTML = `
        <div style="opacity:0.7; font-size:10px; margin-bottom:4px;">${dateStr} ${timeStr}</div>
        <div>开 <span style="float:right; font-weight:600; margin-left:16px;">${fmtPrice(p.open)}</span></div>
        <div>高 <span style="float:right; color:#34D399; font-weight:600;">${fmtPrice(p.high)}</span></div>
        <div>低 <span style="float:right; color:#FB7185; font-weight:600;">${fmtPrice(p.low)}</span></div>
        <div>收 <span style="float:right; color:${upClr}; font-weight:600;">${fmtPrice(p.close)} (${change >= 0 ? "+" : ""}${change.toFixed(2)}%)</span></div>
        <div>成交 <span style="float:right; font-weight:600;">${p.today_volume ?? 0}</span></div>
      `;
    } else {
      const tPctClr =
        p.today_pct == null ? "#9CA3AF" : p.today_pct >= 0 ? "#34D399" : "#FB7185";
      const wPctClr =
        p.week_pct == null ? "#9CA3AF" : p.week_pct >= 0 ? "#34D399" : "#FB7185";
      tooltip.innerHTML = `
        <div style="opacity:0.7; font-size:10px; margin-bottom:4px;">${dateStr} ${timeStr}</div>
        <div>价格 <span style="float:right; font-weight:600; margin-left:16px;">${fmtPrice(p.price)}</span></div>
        ${p.today_pct != null ? `<div>今日 <span style="float:right; color:${tPctClr}; font-weight:600;">${p.today_pct >= 0 ? "+" : ""}${p.today_pct.toFixed(2)}%</span></div>` : ""}
        ${p.week_pct != null ? `<div>本周 <span style="float:right; color:${wPctClr}; font-weight:600;">${p.week_pct >= 0 ? "+" : ""}${p.week_pct.toFixed(2)}%</span></div>` : ""}
        <div>成交 <span style="float:right; font-weight:600;">${p.today_volume ?? 0}</span></div>
        ${p.market_index != null ? `<div>大盘 <span style="float:right; opacity:0.7;">${p.market_index.toFixed(1)}</span></div>` : ""}
      `;
    }

    const tipW = 160,
      tipH = 110,
      gap = 12;
    let tx = relX + gap;
    let ty = relY + gap;
    if (tx + tipW > rect.width) tx = relX - tipW - gap;
    if (ty + tipH > rect.height) ty = relY - tipH - gap;
    tooltip.style.left = `${tx}px`;
    tooltip.style.top = `${ty}px`;
    tooltip.style.opacity = "1";
  }

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    _moveAt(e.clientX, e.clientY);
  }
  function onTouch(e: React.TouchEvent<HTMLDivElement>) {
    const t = e.touches[0];
    if (t) _moveAt(t.clientX, t.clientY);
  }

  function onLeave() {
    if (tooltipRef.current) tooltipRef.current.style.opacity = "0";
    crosshairRef.current?.setAttribute("opacity", "0");
    volCrossRef.current?.setAttribute("opacity", "0");
    dotRef.current?.setAttribute("opacity", "0");
  }

  const metaText =
    type === "line"
      ? `${item?.phase || ""} · 折线 · 最近 ${hours}h · 共 ${count} 个数据点`
      : kline === "hour"
      ? `${item?.phase || ""} · 时K · 最近 72h`
      : `${item?.phase || ""} · 日K · 最近 30 天`;

  return (
    <div
      className="rounded-[28px] p-8 backdrop-blur-2xl"
      style={{
        background: "rgba(255,255,255,0.65)",
        border: "1px solid rgba(255,255,255,0.35)",
        boxShadow: "0 30px 80px -30px rgba(15,23,42,0.18)",
      }}
    >
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h3 className="text-2xl font-semibold tracking-tight">{item?.name || item?.short_name || "—"}</h3>
            <span className="pill" style={{ fontSize: 12 }}>
              {item?.current_stage || item?.phase || "—"}
            </span>
          </div>
          <p className="text-sm text-[var(--text-tertiary)]">{metaText}</p>
        </div>
        <div className="text-right">
          <div className="text-4xl font-semibold tracking-tight">{fmtPrice(item?.price ?? null)}</div>
          <div className={`text-sm font-medium ${pctClass(item?.today_pct ?? null)}`}>
            {fmtPct(item?.today_pct ?? null)} 今日
          </div>
        </div>
      </div>

      <div
        ref={wrapRef}
        className="relative"
        style={{ cursor: "crosshair", touchAction: "pan-y" }}
        onMouseMove={onMove}
        onMouseLeave={onLeave}
        onTouchStart={onTouch}
        onTouchMove={onTouch}
        onTouchEnd={onLeave}
      >
        <div className="relative w-full" style={{ height: 320 }}>
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="w-full h-full">
            <defs>
              <linearGradient id="ch2Grad" x1="0" x2="1" y1="0" y2="0">
                <stop offset="0%" stopColor="#6366F1" />
                <stop offset="50%" stopColor="#EC4899" />
                <stop offset="100%" stopColor="#F59E0B" />
              </linearGradient>
              <linearGradient id="ch2Area" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#6366F1" stopOpacity="0.18" />
                <stop offset="100%" stopColor="#6366F1" stopOpacity="0" />
              </linearGradient>
            </defs>
            <g stroke="rgba(0,0,0,0.05)" strokeWidth="1">
              <line x1="0" y1={H * 0.25} x2={W} y2={H * 0.25} />
              <line x1="0" y1={H * 0.5} x2={W} y2={H * 0.5} />
              <line x1="0" y1={H * 0.75} x2={W} y2={H * 0.75} />
            </g>
            {rawPoints.length < 2 ? (
              <text x="400" y="160" textAnchor="middle" fill="#86868B" fontSize="14">
                数据点不足，等监控积累...
              </text>
            ) : type === "line" ? (
              <g>
                <path d={areaD} fill="url(#ch2Area)" />
                <path d={lineD} fill="none" stroke="url(#ch2Grad)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </g>
            ) : (
              <g>
                {candles?.map((c, i) => {
                  const up = c.close >= c.open;
                  const color = up ? "#10B981" : "#EF4444";
                  const bodyTop = yScale(Math.max(c.open, c.close));
                  const bodyBot = yScale(Math.min(c.open, c.close));
                  const wickTop = yScale(c.high);
                  const wickBot = yScale(c.low);
                  const cx = xPosOf(c);
                  return (
                    <g key={i}>
                      <line x1={cx} y1={wickTop} x2={cx} y2={wickBot} stroke={color} strokeWidth="1" />
                      <rect
                        x={cx - candleW / 2}
                        y={bodyTop}
                        width={candleW}
                        height={Math.max(2, bodyBot - bodyTop)}
                        fill={color}
                      />
                    </g>
                  );
                })}
              </g>
            )}
            <line ref={crosshairRef} x1="0" y1="0" x2="0" y2={H} stroke="rgba(99,102,241,0.5)" strokeWidth="1" strokeDasharray="4 3" opacity="0" pointerEvents="none" />
            <circle ref={dotRef} cx="0" cy="0" r="5" fill="white" stroke="#6366F1" strokeWidth="2.5" opacity="0" pointerEvents="none" />
          </svg>
        </div>

        {type === "kline" && (
          <div className="relative w-full mt-2" style={{ height: 100 }}>
            <div className="text-xs text-[var(--text-tertiary)] mb-1">成交量</div>
            <svg viewBox={`0 0 ${VW} 80`} preserveAspectRatio="none" className="w-full" style={{ height: 80 }}>
              <g>
                {candles?.map((c, i) => {
                  const h = (c.volume / maxVol) * VH * 0.95;
                  const up = c.close >= c.open;
                  const color = up ? "#10B981" : "#EF4444";
                  const cx = vxPosOf(c);
                  return (
                    <rect
                      key={i}
                      x={cx - candleW / 2}
                      y={VH - h}
                      width={candleW}
                      height={h}
                      fill={color}
                      opacity="0.6"
                    />
                  );
                })}
              </g>
              <line ref={volCrossRef} x1="0" y1="0" x2="0" y2="80" stroke="rgba(99,102,241,0.5)" strokeWidth="1" strokeDasharray="4 3" opacity="0" pointerEvents="none" />
            </svg>
          </div>
        )}

        <div
          ref={tooltipRef}
          className="absolute pointer-events-none z-20 px-3 py-2 rounded-xl text-xs font-medium leading-relaxed"
          style={{
            background: "rgba(29,29,31,0.92)",
            color: "white",
            backdropFilter: "blur(10px)",
            boxShadow: "0 8px 24px -4px rgba(0,0,0,0.25)",
            opacity: 0,
            transition: "opacity 0.12s",
            minWidth: 140,
          }}
        />
      </div>

      <div className="flex justify-between mt-2 text-xs text-[var(--text-tertiary)]">
        {ticks.map((t, i) => (
          <span key={i}>{t}</span>
        ))}
      </div>
    </div>
  );
}
