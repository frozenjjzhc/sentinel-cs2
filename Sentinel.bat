@echo off
REM ============================================================
REM Sentinel.bat - 一键启动整套系统（API + 监控 + Dashboard）
REM
REM 双击即用：API 进程内嵌监控调度器，
REM   - 自动每 10min 跑 monitor_fast
REM   - 自动每 1H   跑 monitor_slow
REM   - 自动每天 23:00 跑 daily_review
REM 同时打开浏览器 dashboard。
REM
REM 关闭这个窗口即停止 API + 监控（一切干净）
REM ============================================================
chcp 65001 > nul
cd /d "%~dp0"

REM 首次运行自动初始化 state.json（如果跳过了 setup.bat）
if not exist "m4a4_buzz_kill_state.json" (
    if exist "state.example.json" (
        echo [Sentinel] 首次启动 - 从 state.example.json 创建 state.json
        copy "state.example.json" "m4a4_buzz_kill_state.json" >nul
        echo [Sentinel] OK 初始化完成。dashboard 启动后请进设置页配置 token 和监控品种。
        echo.
    ) else (
        echo [Sentinel] ERROR: state.example.json 也不存在。
        echo 请重新解压项目压缩包，或检查文件是否齐全。
        pause
        exit /b 1
    )
)

REM 检测 8000 端口是否已占用
netstat -ano | findstr ":8000.*LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [Sentinel] 检测到 API 已在运行，直接打开 dashboard
    timeout /t 1 /nobreak >nul
    start "" http://localhost:8000
    exit /b 0
)

echo.
echo ============================================================
echo   Sentinel 启动中...
echo   API + 监控调度器 + Dashboard 一体化运行
echo ============================================================
echo.
echo  - API:        http://localhost:8000
echo  - 监控:       嵌入式（API 启动后自动开跑）
echo  - 关闭系统：  关掉这个窗口（Ctrl+C 或 X）
echo.

REM 后台等待 4 秒后自动打开浏览器
start "Sentinel Browser Opener" /B cmd /c "timeout /t 4 /nobreak >nul && start """" http://localhost:8000"

REM 前台跑 API（关窗口即停一切）
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python backend_api.py
