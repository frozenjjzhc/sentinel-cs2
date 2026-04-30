import { useEffect } from "react";

// 双向触发的 IntersectionObserver — 元素进入视口加 .in-view，离开移除
export function useRevealObserver() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("in-view");
          else e.target.classList.remove("in-view");
        }),
      { threshold: 0.12, rootMargin: "0px 0px -10% 0px" }
    );
    document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  });
}

// 30 秒轮询 hook（驱动 hero / 状态 pill 等）
export function useInterval(fn: () => void, ms: number) {
  useEffect(() => {
    fn();
    const id = setInterval(fn, ms);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms]);
}
