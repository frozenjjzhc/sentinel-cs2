import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 后端 FastAPI 在 :8000，dev 时直接代理 /api → :8000
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": "/src" },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
  },
});
