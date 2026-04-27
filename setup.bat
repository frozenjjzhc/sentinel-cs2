@echo off
REM ============================================================
REM CS2 Skin Monitor - One-Time Setup
REM 1. Installs Python dependencies
REM 2. Downloads Playwright Chromium (with China mirror)
REM 3. Initializes state.json from state.example.json
REM ============================================================

REM 设置 UTF-8 代码页（避免中文消息乱码）
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

setlocal enabledelayedexpansion

echo.
echo ===================================================
echo   CS2 Skin Monitor - Setup
echo ===================================================
echo.

REM --- Check Python ---
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  ERROR: Python not found in PATH.
    echo ============================================================
    echo.
    echo Python 没装，或者装的时候没勾 "Add python.exe to PATH"。
    echo.
    echo Install steps / 安装步骤:
    echo   1. 去 https://www.python.org/downloads/ 下载 Python 3.9+
    echo   2. 双击安装包，第一屏底部一定要勾上：
    echo      [X] Add python.exe to PATH      ^<-- 这个不勾的话装完也用不了
    echo   3. Install Now
    echo   4. 装完后关闭这个窗口，重新双击 setup.bat
    echo.
    pause
    exit /b 1
)
python --version
echo.

REM --- Install dependencies ---
echo [2/4] Installing Python packages (playwright, requests)...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python packages.
    pause
    exit /b 1
)
echo OK
echo.

REM --- Install Playwright Chromium ---
echo [3/4] Installing Playwright Chromium browser (~150MB, one-time)...
echo [info] Using npmmirror.com mirror for faster download in China...
echo        (If outside China, still works - falls back to official source if mirror fails)
echo.

REM 优先用淘宝镜像（国内秒下，国外也能走 CDN）
set "PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright"
python -m playwright install chromium

if errorlevel 1 (
    echo.
    echo [warning] 镜像下载失败，回落到 Playwright 官方源（可能需要 VPN）...
    set "PLAYWRIGHT_DOWNLOAD_HOST="
    python -m playwright install chromium
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install Chromium.
        echo.
        echo 排查方法：
        echo   1. 检查网络是否正常（能否访问 https://npmmirror.com）
        echo   2. 如果在国内：尝试启动 VPN 后重跑此脚本
        echo   3. 国外用户：直接重跑应该能用官方源
        pause
        exit /b 1
    )
)
echo OK
echo.

REM --- Check / init state.json ---
echo [4/4] Checking state.json...
if exist "m4a4_buzz_kill_state.json" (
    echo Found existing state.json - will be reused.
) else (
    if exist "state.example.json" (
        copy "state.example.json" "m4a4_buzz_kill_state.json" >nul
        echo Created m4a4_buzz_kill_state.json from state.example.json.
        echo You can fill in PushPlus tokens / monitored items via the dashboard ^(Settings page^) after launch.
    ) else (
        echo WARNING: Neither state.json nor state.example.json found.
        echo Please re-clone or re-extract the project archive.
    )
)
echo.

echo ===================================================
echo   Setup complete!
echo ===================================================
echo.
echo Next steps:
echo   1. Double-click  Sentinel.bat   ^(starts API + monitoring + opens dashboard^)
echo   2. In the dashboard:
echo        - Settings page: add PushPlus tokens, monitored items, optional LLM config
echo        - AI Review page: see shadow stats once data accumulates
echo.
echo For developer / debug mode:
echo   - Manual fast scan:    python monitor_fast.py --test
echo   - API-only ^(no auto monitor^): .\run_backend_api.bat ^(set scheduler.mode=external first^)
echo.
pause
