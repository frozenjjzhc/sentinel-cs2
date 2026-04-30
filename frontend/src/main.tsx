import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { captureTokenFromQuery } from "./lib/api";
import "./index.css";

// 第一时间处理 ?token=... — 手机扫 QR 时 URL 自带 token，写入 localStorage 后清掉 query
captureTokenFromQuery();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 25_000,
      refetchOnWindowFocus: false,
      retry: 0,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
