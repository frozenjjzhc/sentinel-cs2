@echo off
REM ============================================================
REM CS2 Skin Monitor - One-Time Setup
REM   1. Installs Python dependencies
REM   2. Downloads Playwright Chromium (with China mirror)
REM   3. Initializes state.json from state.example.json
REM
REM Note: kept fully ASCII to avoid Windows codepage / encoding issues.
REM ============================================================

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
    echo Python is not installed, or "Add to PATH" was unchecked.
    echo.
    echo Install steps:
    echo   1. Open https://www.python.org/downloads/
    echo   2. Download Python 3.9+
    echo   3. Run the installer. On the FIRST screen, CHECK the box:
    echo        [X] Add python.exe to PATH
    echo      ^(without this, Python won't be findable from cmd^)
    echo   4. Click "Install Now"
    echo   5. Close this window. Open a NEW one. Re-run setup.bat.
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
echo [3/4] Installing Playwright Chromium browser ^(~150MB, one-time^)...
echo [info] Trying npmmirror.com mirror first ^(faster in China^)...
echo.

set "PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright"
python -m playwright install chromium

if errorlevel 1 (
    echo.
    echo [warning] Mirror download failed. Falling back to official source...
    echo           ^(may need VPN if you're in China^)
    set "PLAYWRIGHT_DOWNLOAD_HOST="
    python -m playwright install chromium
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install Chromium.
        echo.
        echo Troubleshooting:
        echo   1. Check internet connection ^(can you reach https://npmmirror.com?^)
        echo   2. If in China and mirror failed: try VPN, then re-run setup.bat
        echo   3. If outside China: try VPN or check firewall
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
        echo Configure tokens / monitored items via Dashboard ^(Settings page^) after launch.
    ) else (
        echo WARNING: Neither state.json nor state.example.json found.
        echo Please re-extract the project archive.
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
echo        - Settings page: add PushPlus tokens, monitored items, optional LLM
echo        - AI Review page: see shadow stats once data accumulates
echo.
echo For developer / debug mode:
echo   - Manual fast scan:    python monitor_fast.py --test
echo   - API-only ^(no auto monitor^): set scheduler.mode=external in dashboard,
echo     then run .\run_backend_api.bat
echo.
pause
