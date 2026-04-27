# 发布到 GitHub 前的检查清单

按顺序做，每完成一项打勾。

---

## ① 安全审查（最重要）

- [ ] `m4a4_buzz_kill_state.json` 在 `.gitignore` 里 ✅（已配置）
- [ ] `.playwright_profile/` 在 `.gitignore` 里 ✅（已配置）
- [ ] `shadow_signals.json` 在 `.gitignore` 里 ✅（已配置）
- [ ] `logs/` 和 `*.log` 排除 ✅（已配置）
- [ ] 代码里没有硬编码 token / API key（已检查，全是 placeholder）
- [ ] README 里没有真 token / 真 API key

**手动验证**：
```powershell
git init
git add .
git status   # 看会上传什么
```

如果 `git status` 列出了 `m4a4_buzz_kill_state.json` 或任何含 token 的文件，**立即停止**。

---

## ② 仓库元信息

- [ ] LICENSE 文件 ✅（MIT，已生成）
- [ ] README.md（已存在）
- [ ] CONTRIBUTING.md ✅（已生成）
- [ ] state.example.json（脱敏模板）✅（已生成）
- [ ] requirements.txt（已存在）

---

## ③ 推荐手动做的事

### 改一下 LICENSE 里的版权人
打开 `LICENSE` 把 `Copyright (c) 2026 frozen` 改成你想要的署名。

### 加项目截图（提升 README 吸引力）
1. 把 dashboard 不同页的截图保存到 `docs/screenshots/` 文件夹
2. README 顶部加一段：
```markdown
![Dashboard](docs/screenshots/home.png)
```

### （可选）改名 `m4a4_buzz_kill_state.json` → `state.json`
原名是单品监控时代的遗物。如果想改：
1. `lib/config.py` 里 `STATE_FILE = ... "state.json"`
2. `m4a4_errors.log` → `errors.log` 同理
3. `.gitignore` 仍然能匹配（已经写了 `state.json`）

---

## ④ 第一次推 GitHub

```powershell
cd D:\claude\xuanxiao

# 初始化
git init
git config user.name "你的GitHub用户名"
git config user.email "你的GitHub邮箱"

# 看看会上传什么 — 一定要看
git add .
git status

# 如果发现敏感文件，立刻 git rm --cached <文件> 然后改 .gitignore

# 提交
git commit -m "Initial public release: Sentinel CS2 monitor v1.0"

# 在 GitHub 网页上创建一个空仓库（不要勾 Add README/LICENSE，因为本地已有）
# 假设你创建了 https://github.com/<user>/sentinel-cs2

git branch -M main
git remote add origin https://github.com/<user>/sentinel-cs2.git
git push -u origin main
```

---

## ⑤ 发布后立即做

### 在 GitHub 仓库设置里：
- [ ] About 区填项目描述（中英都可）：`CS2 饰品智能监控系统：规则引擎 + LLM 语义层 + 多页 SPA dashboard`
- [ ] Topics 加标签：`cs2`、`steam-skins`、`fastapi`、`playwright`、`trading-bot`、`llm`、`personal-finance`
- [ ] Settings → Features → 关掉 Wiki / Projects（没用上）
- [ ] Settings → Pages（如果想放 demo dashboard 静态版）

### 推荐立刻加：
- [ ] Issues 模板：`.github/ISSUE_TEMPLATE/bug_report.md`
- [ ] PR 模板：`.github/pull_request_template.md`
- [ ] CI（github actions 跑 syntax check）：`.github/workflows/test.yml`

---

## ⑥ 发布后**绝对不能**做

- ❌ 把删除过的真 token 重新 commit（即使 force push 也救不了 — 已被 GitHub 索引）
- ❌ 在 issue/PR 评论里贴 token（GitHub 也会扫）
- ❌ 截图里露出 token / API key（Settings 页有脱敏，OK 截图，但要再人眼检查）
- ❌ 截图里露出真实持仓金额（如果你介意隐私，把仓位管理页的 ¥ 数字也打码）

---

## ⑦ 万一不小心 push 了 token，怎么办？

立刻按顺序：

1. **先 revoke 那个 token**（去 PushPlus / Anthropic / OpenAI 控制台禁用）
2. 然后才考虑改 git history
3. 用 `git filter-branch` 或 BFG Repo-Cleaner 重写历史
4. `git push --force --all`
5. 通知任何已经 fork / clone 过的人

但**最稳妥的还是：第一次推之前认真检查**。

---

## ⑧ 做大之后可以考虑

- [ ] GitHub Releases：打 v1.0.0 tag + 写 release notes
- [ ] 发到 r/GlobalOffensive / r/csgomarketforum 看反馈
- [ ] 加英文 README（README.en.md）扩大受众
- [ ] 发到 Hacker News（Show HN）
- [ ] 加 GitHub Sponsors / Buy me a coffee（如果想接受赞助）
