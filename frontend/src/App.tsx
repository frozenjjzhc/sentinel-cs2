import { Route, Routes, useLocation } from "react-router-dom";
import { useEffect } from "react";
import Nav from "./components/Nav";
import Home from "./pages/Home";
import Charts from "./pages/Charts";
import Positions from "./pages/Positions";
import Strategy from "./pages/Strategy";
import AIReview from "./pages/AIReview";
import Settings from "./pages/Settings";

export default function App() {
  const { pathname } = useLocation();

  // 切页面后回到顶部（与原版 switchPage 等效）
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [pathname]);

  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/charts" element={<Charts />} />
        <Route path="/positions" element={<Positions />} />
        <Route path="/strategy" element={<Strategy />} />
        <Route path="/ai" element={<AIReview />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Home />} />
      </Routes>
      <footer className="border-t border-black/5 py-12 px-6 text-center text-sm text-[var(--text-tertiary)]">
        <p>Sentinel · Built with React · Tailwind · Vite</p>
        <p className="mt-2">© 2026 · 设计灵感来自 Apple.com</p>
      </footer>
    </>
  );
}
