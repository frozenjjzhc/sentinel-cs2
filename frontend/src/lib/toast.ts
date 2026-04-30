// 全局 toast — 直接 DOM 注入。和 preview.html 完全等价。
export function showToast(msg: string, type: "success" | "error" = "success"): void {
  const t = document.createElement("div");
  t.className =
    "fixed bottom-8 right-8 z-50 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium transition-all";
  t.style.cssText = `
    background: ${type === "success" ? "rgba(16,185,129,0.95)" : "rgba(239,68,68,0.95)"};
    color: white;
    transform: translateY(20px);
    opacity: 0;
    backdrop-filter: blur(20px);
  `;
  t.textContent = msg;
  document.body.appendChild(t);
  requestAnimationFrame(() => {
    t.style.transform = "translateY(0)";
    t.style.opacity = "1";
  });
  setTimeout(() => {
    t.style.transform = "translateY(20px)";
    t.style.opacity = "0";
    setTimeout(() => t.remove(), 300);
  }, 2800);
}
