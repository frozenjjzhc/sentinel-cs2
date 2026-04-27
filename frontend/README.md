# Sentinel · CS2 饰品监控前端

苹果式极简 + CS2 高级色彩点缀的前端 UI。

## 一、设计哲学

### 1. 矛盾即美学 · "白底之上，色彩斑斓"

CS2 饰品本身色彩极度丰富（多普勒的迷幻渐变、表面淬火的斑斓、大理石的极致色谱），传统饰品交易站把这些色彩堆满整个界面，结果是**视觉疲劳**。

我们的策略：
- **主战场绝对纯净**：白色 (#FFFFFF) + 高级灰 (#F5F5F7) 占 90% 视觉
- **CS2 色彩作为光晕注入**：通过 `filter: blur(80px)` 的渐变光球漂浮在 hero / section 背景，让色彩"渗透"而不是"占据"
- **流光文字 / 流光边框**：渐变 + 动画，强化"价值感"

→ 结果：每一个色彩元素都成为视觉锚点，用户的注意力被精准引导。

### 2. 形状反对方框

苹果产品的精髓是**圆角的精度**。我们的组件：
- 按钮 = `border-radius: 9999px`（完整 pill）
- 卡片 = `border-radius: 28px`（大圆角，超越普通 12px）
- 装饰元素 = 不规则流体形状

### 3. 动效服务于"高级感"，不是炫技

每一个动画都有目的：
- **入场 reveal**：让用户感知到"页面在为我展开"
- **磁吸按钮**：让用户感觉"按钮主动想被点击"
- **Sticky 视差**：让滚动从"翻页"变成"叙事"
- **数字平滑递增**：把"显示"变成"演化"

## 二、技术架构

| 层 | 推荐 | 备选 |
|---|---|---|
| 框架 | React 18 + Vite | Next.js 14 (SSR) |
| 样式 | Tailwind CSS 3 | UnoCSS |
| 动画 | Framer Motion | GSAP（更精细控制）|
| 图表 | Recharts | D3.js（自定义） |
| 部署 | Vercel | Cloudflare Pages |
| 数据接入 | 读取 state.json 经 Python FastAPI 暴露 | 直接 fetch JSON |

### 数据流

```
本地 Python state.json
    ↓
FastAPI/Express 简单 REST 包装层 (8000 端口)
    ↓ (SSE / 轮询)
React 前端
    ↓ (用户操作)
反向调用 add_item.py 等脚本
```

如果你不想跑后端服务，前端可以**直接读 state.json**（同源部署到本地），用 Tauri/Electron 封装就是桌面 app。

## 三、文件清单

```
frontend/
├── README.md                        本文件
├── preview.html                     单文件 demo（双击直接看）
├── package.json                     React 项目依赖
├── vite.config.js                   构建配置
├── tailwind.config.js               设计令牌
├── index.html                       Vite 入口
└── src/
    ├── App.jsx                      根组件
    ├── main.jsx                     React 挂载
    ├── styles/
    │   └── globals.css              Tailwind + 自定义变量
    ├── components/
    │   ├── Nav.jsx                  顶部导航
    │   ├── HeroSection.jsx          首屏（光晕 + CTA）
    │   ├── MagneticButton.jsx       磁吸胶囊按钮
    │   ├── SkinCard.jsx             玻璃卡片（饰品展示）
    │   ├── StickyScrollReveal.jsx   苹果式视差
    │   ├── PriceChart.jsx           SVG 路径绘制图表
    │   └── PriceAnalysisSection.jsx 价格分析区
    ├── hooks/
    │   ├── useScrollReveal.js       IntersectionObserver 封装
    │   └── useMagneticHover.js      磁吸 hover 逻辑
    └── lib/
        └── api.js                   读 state.json
```

## 四、快速预览

```bash
# 方式 A：双击 preview.html（无需任何安装）
# Windows 资源管理器打开 D:\claude\xuanxiao\frontend\preview.html

# 方式 B：本地服务器（避免 CORS）
cd D:\claude\xuanxiao\frontend
python -m http.server 8000
# 浏览器访问 http://localhost:8000/preview.html
```

## 五、部署到生产环境

```bash
cd frontend
npm install
npm run dev      # 开发模式 (http://localhost:5173)
npm run build    # 构建到 dist/
npm run preview  # 预览构建结果
```

## 六、设计要点决策记录（ADR）

| 决策 | 选项 | 选择 | 原因 |
|---|---|---|---|
| 主字体 | Inter / Noto Sans / SF Pro | **SF Pro Display** + 中文 PingFang SC | 苹果视觉一致性 |
| 圆角策略 | 统一 12px | **分层圆角** 8/16/28/9999px | 不同层级有不同重量感 |
| 颜色编码 | HSL 调色板 | **CS2 饰品色谱直采** | 让色彩本身就是品牌 |
| 阴影 | Material 8 级 | **仅 hover 时浮起** | 平时纯净，交互时有反馈 |
| 字号阶梯 | 1.25x ratio | **苹果官网阶梯** 17/24/40/56/88 | 经过验证的视觉节奏 |

## 七、扩展方向

- 暗色模式（black 主背景 + 同色系光晕降低饱和度）
- 实时 WebSocket 推送（信号触发时前端立刻闪烁）
- 持仓 P&L 图表（resampled 时间序列）
- AI 助手对话框（接 Claude API 处理"该加仓吗"等问题）
- 移动端 PWA（推送通知支持）
