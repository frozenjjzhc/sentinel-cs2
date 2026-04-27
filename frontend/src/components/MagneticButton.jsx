/**
 * MagneticButton — 苹果式磁吸胶囊按钮
 *
 * 特性：
 * - 鼠标跟随磁吸（mousemove → translate transform）
 * - 鼠标移出弹性归位（spring damping）
 * - hover 时流光边框（CSS @keyframes border gradient）
 * - 点击时 scale(0.98) 微下沉
 *
 * 使用：
 * <MagneticButton onClick={...} variant="primary">开始监控</MagneticButton>
 */

import { useRef, useState } from "react";
import { motion, useSpring, useTransform } from "framer-motion";

const VARIANTS = {
  primary: {
    bg: "#1D1D1F",
    color: "white",
    border: "transparent",
  },
  secondary: {
    bg: "transparent",
    color: "var(--text-primary)",
    border: "rgba(0,0,0,0.12)",
  },
};

export default function MagneticButton({
  children,
  onClick,
  variant = "primary",
  className = "",
  style = {},
  magneticStrength = 0.22,   // 0 = 关闭磁吸；越大跟随越夸张
  ...props
}) {
  const ref = useRef(null);
  const [hover, setHover] = useState(false);

  // Spring-based offset (more natural than linear interpolation)
  const x = useSpring(0, { stiffness: 280, damping: 22, mass: 0.4 });
  const y = useSpring(0, { stiffness: 280, damping: 22, mass: 0.4 });

  const handleMouseMove = (e) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const offsetX = (e.clientX - rect.left - rect.width / 2) * magneticStrength;
    const offsetY = (e.clientY - rect.top - rect.height / 2) * magneticStrength;
    x.set(offsetX);
    y.set(offsetY);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
    setHover(false);
  };

  const v = VARIANTS[variant];

  return (
    <motion.button
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      whileTap={{ scale: 0.98 }}
      style={{
        x,
        y,
        background: v.bg,
        color: v.color,
        border: `1px solid ${v.border}`,
        ...style,
      }}
      className={`
        relative inline-flex items-center gap-2.5
        px-8 py-4 rounded-full font-medium text-base
        cursor-pointer overflow-hidden
        transition-shadow duration-500
        ${hover && variant === "primary"
          ? "shadow-[0_18px_40px_-12px_rgba(99,102,241,0.45)]"
          : ""}
        ${className}
      `}
      {...props}
    >
      {/* 流光边框（仅 hover 时出现）*/}
      {hover && variant === "primary" && (
        <span
          className="pointer-events-none absolute inset-[-2px] rounded-full p-[2px]"
          style={{
            background:
              "linear-gradient(120deg, #6366F1, #EC4899, #F59E0B, #6366F1)",
            backgroundSize: "300% 300%",
            WebkitMask:
              "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
            WebkitMaskComposite: "xor",
            maskComposite: "exclude",
            animation: "borderflow 4s linear infinite",
          }}
        />
      )}

      <span className="relative z-10 flex items-center gap-2.5">
        {children}
      </span>

      <style>{`
        @keyframes borderflow {
          0%   { background-position: 0% 50%; }
          100% { background-position: 300% 50%; }
        }
      `}</style>
    </motion.button>
  );
}
