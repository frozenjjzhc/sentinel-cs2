/**
 * PriceAnalysisSection — 价格走势分析区
 *
 * 苹果式"嵌套滚动"实现：
 *   1. Scroll Reveal 入场：标题 → pill → 卡片
 *   2. SVG 路径绘制动画：stroke-dashoffset 0→2000
 *   3. 信号点 pulse：r 5→9 循环
 *   4. 区域填充延迟淡入：opacity 0→1（线画完后才出现）
 *
 * 设计要点：
 *   - 用 Recharts 的话样式不够"高级"，用原生 SVG 完全可控
 *   - 渐变线条（紫→粉→金）= CS2 饰品色谱品牌锚定
 *   - 信号点用 drop-shadow 模拟发光（GPU-accelerated）
 */

import { motion } from "framer-motion";

// 模拟 24h 数据（生产环境从 state.json 拉）
const MOCK_DATA = [
  { time: "00:00", price: 4250, signal: null },
  { time: "03:00", price: 4263, signal: null },
  { time: "06:00", price: 4220, signal: { type: "BUY-WHALE", desc: "触庄家承诺底" } },
  { time: "09:00", price: 4263, signal: null },
  { time: "12:00", price: 4280, signal: null },
  { time: "15:00", price: 4150, signal: null },
  { time: "17:00", price: 4290, signal: { type: "D1 反弹买入", desc: "放量 + 大盘配合", active: true } },
  { time: "20:00", price: 4310, signal: null },
  { time: "24:00", price: 4298, signal: null },
];

// 把数据点映射到 SVG 坐标
function buildPath(data, width = 800, height = 360) {
  const xStep = width / (data.length - 1);
  const prices = data.map(d => d.price);
  const min = Math.min(...prices) * 0.99;
  const max = Math.max(...prices) * 1.01;
  const yScale = p => height - ((p - min) / (max - min)) * height;

  // 用 cubic-bezier 平滑曲线
  let d = `M 0,${yScale(prices[0])}`;
  for (let i = 1; i < data.length; i++) {
    const x = i * xStep;
    const y = yScale(prices[i]);
    const cx = x - xStep / 2;
    const cy = (yScale(prices[i - 1]) + y) / 2;
    d += ` Q ${cx},${cy} ${x},${y}`;
  }
  const dArea = d + ` L ${width},${height} L 0,${height} Z`;
  const points = data.map((p, i) => ({ ...p, x: i * xStep, y: yScale(p.price) }));
  return { d, dArea, points };
}

const fadeUp = {
  hidden: { opacity: 0, y: 60 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.9, ease: [0.16, 1, 0.3, 1] },
  }),
};

export default function PriceAnalysisSection() {
  const { d, dArea, points } = buildPath(MOCK_DATA);

  return (
    <section className="relative py-32 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <motion.span
            variants={fadeUp} initial="hidden" whileInView="visible"
            viewport={{ amount: 0.12 }} custom={0}
            className="inline-block mb-6 px-3.5 py-1.5 rounded-full text-xs font-medium
                       bg-indigo-500/[0.08] text-indigo-600
                       border border-indigo-500/[0.18]"
          >
            PRICE INTELLIGENCE
          </motion.span>

          <motion.h2
            variants={fadeUp} initial="hidden" whileInView="visible"
            viewport={{ amount: 0.12 }} custom={1}
            className="text-5xl md:text-6xl font-semibold tracking-tight mb-6"
          >
            每一个数据点<br />
            <span
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage:
                  "linear-gradient(120deg, #1D1D1F, #6366F1 25%, #EC4899 60%, #F59E0B)",
              }}
            >
              都讲一个故事
            </span>
          </motion.h2>

          <motion.p
            variants={fadeUp} initial="hidden" whileInView="visible"
            viewport={{ amount: 0.12 }} custom={2}
            className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto"
          >
            累积 90 天滚动数据，多时间框架均线，6 阶段庄家识别。
          </motion.p>
        </div>

        {/* Glass Card 包裹整个图表 */}
        <motion.div
          variants={fadeUp} initial="hidden" whileInView="visible"
          viewport={{ amount: 0.12, margin: "-10%" }} custom={0}
          className="rounded-[28px] p-10 backdrop-blur-2xl"
          style={{
            background: "rgba(255,255,255,0.65)",
            border: "1px solid rgba(255,255,255,0.35)",
            boxShadow:
              "0 1px 0 rgba(255,255,255,0.6) inset, 0 30px 80px -30px rgba(15,23,42,0.18)",
          }}
        >
          {/* 卡片头：品种名 + 价格 + 涨跌 */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-2xl font-semibold tracking-tight">M4A4 | 喧嚣杀戮</h3>
                <span className="px-3 py-1 rounded-full text-xs font-medium
                                 bg-emerald-500/[0.08] text-emerald-600
                                 border border-emerald-500/[0.18]">
                  D1 信号
                </span>
              </div>
              <p className="text-sm text-[var(--text-tertiary)]">崭新出厂 · 24 小时趋势</p>
            </div>
            <div className="text-right">
              <div className="text-4xl font-semibold tracking-tight">¥4,298</div>
              <div className="text-sm text-emerald-600 font-medium">+0.83% (+¥35)</div>
            </div>
          </div>

          {/* SVG 价格图 */}
          <div className="relative w-full" style={{ height: 360 }}>
            <svg viewBox="0 0 800 360" preserveAspectRatio="none" className="w-full h-full">
              <defs>
                <linearGradient id="chartGradient" x1="0" x2="1" y1="0" y2="0">
                  <stop offset="0%"   stopColor="#6366F1" />
                  <stop offset="50%"  stopColor="#EC4899" />
                  <stop offset="100%" stopColor="#F59E0B" />
                </linearGradient>
                <linearGradient id="chartArea" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%"   stopColor="#6366F1" stopOpacity="0.18" />
                  <stop offset="100%" stopColor="#6366F1" stopOpacity="0" />
                </linearGradient>
              </defs>

              {/* 网格线 */}
              <g stroke="rgba(0,0,0,0.05)" strokeWidth="1">
                <line x1="0" y1="80"  x2="800" y2="80"  />
                <line x1="0" y1="160" x2="800" y2="160" />
                <line x1="0" y1="240" x2="800" y2="240" />
              </g>

              {/* 区域填充（线画完后淡入） */}
              <motion.path
                d={dArea}
                fill="url(#chartArea)"
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ amount: 0.12 }}
                transition={{ duration: 1.6, delay: 1.6 }}
              />

              {/* 主线（描边动画） */}
              <motion.path
                d={d}
                fill="none"
                stroke="url(#chartGradient)"
                strokeWidth={2.5}
                strokeLinecap="round"
                strokeLinejoin="round"
                initial={{ pathLength: 0 }}
                whileInView={{ pathLength: 1 }}
                viewport={{ amount: 0.12 }}
                transition={{ duration: 2.5, delay: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
              />

              {/* 信号点 */}
              {points.filter(p => p.signal).map((p, i) => (
                <motion.circle
                  key={i}
                  cx={p.x}
                  cy={p.y}
                  r={5}
                  fill="#6366F1"
                  filter="drop-shadow(0 0 8px rgba(99,102,241,0.6))"
                  animate={p.signal.active ? {
                    r: [5, 9, 5],
                    opacity: [1, 0.55, 1],
                  } : {}}
                  transition={p.signal.active ? {
                    duration: 2.4,
                    repeat: Infinity,
                    ease: "easeInOut",
                  } : {}}
                />
              ))}
            </svg>

            {/* X 轴 */}
            <div className="flex justify-between mt-4 text-xs text-[var(--text-tertiary)]">
              {MOCK_DATA.filter((_, i) => i % 2 === 0).map(d => (
                <span key={d.time}>{d.time}</span>
              ))}
            </div>
          </div>

          {/* 信号 timeline */}
          <div className="mt-8 grid grid-cols-3 gap-4">
            {MOCK_DATA.filter(d => d.signal).slice(0, 2).map((d, i) => (
              <div
                key={i}
                className={`p-4 rounded-2xl ${
                  d.signal.active
                    ? "bg-indigo-500/[0.08]"
                    : "bg-black/[0.03]"
                }`}
              >
                <div className={`text-xs mb-1 ${d.signal.active ? "text-indigo-600" : "text-[var(--text-tertiary)]"}`}>
                  {d.time}{d.signal.active && " · 当前"}
                </div>
                <div className={`font-medium ${d.signal.active ? "text-indigo-600" : ""}`}>
                  {d.signal.type}
                </div>
                <div className="text-sm text-[var(--text-secondary)]">{d.signal.desc}</div>
              </div>
            ))}
            <div className="p-4 rounded-2xl bg-black/[0.03]">
              <div className="text-xs text-[var(--text-tertiary)] mb-1">下一档</div>
              <div className="font-medium">C1 突破前期高</div>
              <div className="text-sm text-[var(--text-secondary)]">¥4,398 关键位</div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
