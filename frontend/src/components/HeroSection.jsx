/**
 * HeroSection — 首屏主视觉
 *
 * 结构：
 *   ┌───────────────────────────────────────┐
 *   │   [漂浮渐变光晕 × 3]                    │
 *   │                                       │
 *   │           Pill 标签                    │
 *   │       极简 · 极智 · 极速                │
 *   │       slogan 副标题                    │
 *   │       [开始监控] [查看演示]              │
 *   │                                       │
 *   │       4 │ 10分钟 │ 96%                │
 *   │   监控品种│扫描频率│Token节省            │
 *   └───────────────────────────────────────┘
 */

import { motion } from "framer-motion";
import MagneticButton from "./MagneticButton";

const SKIN_GRADIENTS = {
  marble:   "linear-gradient(135deg, #FF3CAC, #784BA0 50%, #2B86C5)",
  doppler:  "linear-gradient(135deg, #4158D0, #C850C0 46%, #FFCC70)",
  tempered: "linear-gradient(135deg, #FA8BFF, #2BD2FF 50%, #2BFF88)",
};

// 入场动画配置（共用）
const fadeUp = {
  hidden: { opacity: 0, y: 60 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.1,
      duration: 0.9,
      ease: [0.16, 1, 0.3, 1],   // bezier easeOutExpo
    },
  }),
};

function GlowOrb({ gradient, size, top, left, right, bottom, delay = 0 }) {
  return (
    <motion.div
      animate={{
        x: [0, 40, -30, 0],
        y: [0, -30, 20, 0],
        scale: [1, 1.06, 0.96, 1],
      }}
      transition={{
        duration: 18,
        repeat: Infinity,
        ease: "easeInOut",
        delay,
      }}
      style={{
        position: "absolute",
        width: size,
        height: size,
        top, left, right, bottom,
        borderRadius: "50%",
        background: gradient,
        filter: "blur(80px)",
        opacity: 0.55,
        pointerEvents: "none",
      }}
    />
  );
}

function StatItem({ value, suffix, label, delay }) {
  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={{ amount: 0.12, margin: "-10%" }}
      custom={delay}
    >
      <div className="text-4xl font-semibold tracking-tight">
        {value}
        {suffix && (
          <span className="text-xl text-[var(--text-tertiary)]">{suffix}</span>
        )}
      </div>
      <div className="text-sm text-[var(--text-secondary)] mt-1">{label}</div>
    </motion.div>
  );
}

export default function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-14">
      {/* 漂浮光晕背板 */}
      <GlowOrb gradient={SKIN_GRADIENTS.marble}   size={480} top="-120px" left="-120px" />
      <GlowOrb gradient={SKIN_GRADIENTS.doppler}  size={380} top="40%"   right="-100px" delay={-6} />
      <GlowOrb gradient={SKIN_GRADIENTS.tempered} size={420} bottom="-160px" left="30%" delay={-12} />

      <div className="relative z-10 text-center px-6 max-w-5xl">
        {/* Pill 状态标签 */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ amount: 0.12 }}
          custom={0}
          className="mb-8"
        >
          <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full
                           text-xs font-medium
                           bg-indigo-500/[0.08] text-indigo-600
                           border border-indigo-500/[0.18]">
            ⚡ 24/7 智能监控 · 信号已发出 1,284 次
          </span>
        </motion.div>

        {/* 主标题 */}
        <motion.h1
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ amount: 0.12 }}
          custom={1}
          className="text-7xl md:text-[88px] font-semibold tracking-tight leading-[1.05] mb-6"
        >
          <ShimmerText>极简</ShimmerText> · <ShimmerText>极智</ShimmerText> · <ShimmerText>极速</ShimmerText>
        </motion.h1>

        {/* 副标题 */}
        <motion.p
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ amount: 0.12 }}
          custom={2}
          className="text-xl md:text-2xl text-[var(--text-secondary)] mb-12 max-w-2xl mx-auto leading-relaxed"
        >
          为 CS2 饰品交易者打造的智能信号引擎。<br />
          让每一次买卖，都有数据支撑。
        </motion.p>

        {/* CTA 按钮组 */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ amount: 0.12 }}
          custom={3}
          className="flex items-center justify-center gap-4"
        >
          <MagneticButton variant="primary" onClick={() => console.log("start")}>
            开始监控
            <ArrowIcon />
          </MagneticButton>
          <MagneticButton variant="secondary" onClick={() => console.log("demo")}>
            查看演示
          </MagneticButton>
        </motion.div>

        {/* 关键指标 */}
        <div className="mt-20 grid grid-cols-3 gap-12 max-w-3xl mx-auto">
          <StatItem value="4"    label="监控品种"    delay={4} />
          <StatItem value="10"   suffix="分钟" label="扫描频率" delay={4.5} />
          <StatItem value="96"   suffix="%"  label="Token 节省" delay={5} />
        </div>
      </div>
    </section>
  );
}

// 流光渐变文字（CS2 饰品色谱）
function ShimmerText({ children }) {
  return (
    <span
      className="bg-clip-text text-transparent"
      style={{
        backgroundImage:
          "linear-gradient(120deg, #1D1D1F 0%, #6366F1 25%, #EC4899 60%, #F59E0B 100%)",
        backgroundSize: "220% 220%",
        animation: "shimmer 8s ease-in-out infinite",
      }}
    >
      {children}
      <style>{`
        @keyframes shimmer {
          0%, 100% { background-position: 0% 50%; }
          50%      { background-position: 100% 50%; }
        }
      `}</style>
    </span>
  );
}

function ArrowIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}
