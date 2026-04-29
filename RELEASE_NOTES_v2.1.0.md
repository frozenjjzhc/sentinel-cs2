# v2.1.0 — 跨版本数据持久化（0 迁移升级）

## 重点
**用户数据搬到 `%APPDATA%\Sentinel\`**，从此每次升级新版本只要覆盖代码，数据永远在那一个固定位置 — **再也不用手动复制 state.json 了**。

## 新增
- 用户数据默认存到 **`C:\Users\<你>\AppData\Roaming\Sentinel\`**，跨版本升级 0 迁移成本
- v1.x / v2.0.x 用户**首次启动 v2.1+ 时自动迁移**老数据到新位置（旧文件保留作备份）
- `SENTINEL_DATA_DIR` 环境变量支持自定义数据目录（多实例隔离 / 测试场景）
- 设置页 → 「📁 数据目录」卡片：显示路径 + 来源，一键「📂 打开数据目录」/「📋 复制路径」
- 新 API 端点：`GET /api/global/data_dir`、`POST /api/global/open_data_dir`

## 升级方法（朋友最关心的部分）

### v1.x / v2.0.x → v2.1.0

**方法 A — 就地覆盖（推荐）**
```powershell
cd D:\你的旧 sentinel 目录
# 解压新 zip 到临时目录
Expand-Archive Sentinel-v2.1.0.zip -DestinationPath $env:TEMP\sentinel-v21 -Force
# 只覆盖代码（数据原封不动）
Copy-Item "$env:TEMP\sentinel-v21\sentinel-cs2\*.py","$env:TEMP\sentinel-v21\sentinel-cs2\*.bat","$env:TEMP\sentinel-v21\sentinel-cs2\*.md" . -Force
Copy-Item "$env:TEMP\sentinel-v21\sentinel-cs2\lib","$env:TEMP\sentinel-v21\sentinel-cs2\frontend" . -Recurse -Force
# 启动
.\Sentinel.bat
```
首次启动时控制台会打印 `[Sentinel] 首次启动 v2.1+：用户数据已从 ... 迁移到 C:\Users\...\AppData\Roaming\Sentinel\`，搞定。

**方法 B — 完全干净的新装**
解压新 zip 到任意位置（不一定是旧位置）→ 双击 `Sentinel.bat` → 启动器会自动找到 `%APPDATA%\Sentinel\` 里的老数据。

### v2.1.0 之后再升级（v2.2 / v3 / …）
直接覆盖代码就行，**数据完全不用动**。

## 看一眼路径

启动 dashboard 后到 **设置页 → 数据目录卡片**，显示：
```
当前数据目录
C:\Users\<你>\AppData\Roaming\Sentinel\
来源：%APPDATA% (Windows 默认，跟随用户账号)
[📂 打开数据目录] [📋 复制路径]
```

## 兼容性

- ✅ 100% 向后兼容：v1.x / v2.0.x 用户首次跑 v2.1+ 自动迁移
- ✅ 旧安装目录里的 state.json 等文件**不会被删除**，作为备份保留，跑稳之后手动清理即可
- ✅ 想保留旧行为：`set SENTINEL_DATA_DIR=D:\你的安装目录` 后再启动
- ✅ 重装 Windows：`%APPDATA%` 会跟随系统备份 / OneDrive 同步还原，数据不会丢

---

完整变更日志：[CHANGELOG.md](https://github.com/frozenjjzhc/sentinel-cs2/blob/main/CHANGELOG.md)
