# Contributing to Sentinel

感谢有兴趣贡献。下面是一些约定。

## 开发环境

```powershell
git clone https://github.com/frozenjjzhc/sentinel-cs2.git
cd sentinel-cs2
.\setup.bat
copy state.example.json m4a4_buzz_kill_state.json
.\Sentinel.bat
```

## 分支约定

- `main` — 稳定可发布
- `dev`  — 日常开发
- `feature/xxx` — 新功能分支
- `fix/xxx`     — 修 bug 分支

## 提交格式

```
<type>: <subject>

<body>
```

`type` 用：`feat / fix / docs / refactor / test / chore`

例：
```
feat: add LLM-based whale announcement parser (Phase 2)

新增 lib/llm_analyst.py::parse_whale_announcement
支持中文公告文本 → 结构化 whale_signal 提取
```

## 代码风格

- Python：遵循 PEP 8，关键模块写 docstring
- JS：在 preview.html 内保持现有风格（2 空格缩进）
- 中文注释 OK，函数名 / 变量名用英文

## 测试

提交 PR 前请确保：

```powershell
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['backend_api.py', 'monitor_fast.py', 'monitor_slow.py', 'daily_review.py']]"
python monitor_fast.py --test
```

不报错即可。

## 不接受的 PR

- 引入自动下单 / 钱包对接 等会动用户钱的功能（与项目目标不符）
- 把 LLM key / token 等硬编码到代码里
- 添加任何爬取 Steam 或第三方网站时绕过反爬的代码
- 默认放开 0.0.0.0 监听 / 关掉 CORS

## 报 bug

issue 模板：

```
**环境**: Win10/11, Python 3.x, ...
**重现步骤**:
1. ...
2. ...
**期望**: ...
**实际**: ...
**日志**: 贴 m4a4_errors.log 末尾片段
```
