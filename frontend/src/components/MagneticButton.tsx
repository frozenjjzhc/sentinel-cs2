import { CSSProperties, MouseEvent, ReactNode, useState } from "react";

type Props = {
  children: ReactNode;
  onClick?: () => void;
  style?: CSSProperties;
  className?: string;
};

// 磁吸胶囊按钮 — 鼠标位置驱动 transform，离开归位
export default function MagneticButton({ children, onClick, style, className = "" }: Props) {
  const [transform, setTransform] = useState("");

  function handleMove(e: MouseEvent<HTMLButtonElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - r.left - r.width / 2;
    const y = e.clientY - r.top - r.height / 2;
    setTransform(`translate(${x * 0.18}px, ${y * 0.25}px) scale(1.04)`);
  }

  function handleLeave() {
    setTransform("");
  }

  return (
    <button
      className={`magnetic-btn ${className}`}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      onClick={onClick}
      style={{ ...style, transform: transform || style?.transform }}
    >
      {children}
    </button>
  );
}
