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

REM --- Install Playwright browser ---
REM Strategy:
REM   Step 1: Register system Chrome (instant, no download).
REM           Works for >95%% of users who have Chrome installed.
REM   Step 2: Only if Chrome registration fails, fall back to downloading Chromium.
REM           Try npmmirror.com first, then official source.
REM           This avoids the 150MB download which is slow in China.
echo [3/4] Setting up browser for Playwright...
echo [info] Trying to register system Chrome first ^(instant, no download^)...
python -m playwright install chrome
if not errorlevel 1 (
    echo OK - using system Chrome
    echo.
    goto browser_done
)

echo [warning] System Chrome not found. Downloading Chromium ^(~150MB^)...
echo           Trying npmmirror.com mirror first...
set "PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright"
python -m playwright install chromium
if not errorlevel 1 (
    echo OK
    echo.
    goto browser_done
)

echo [warning] Mirror download failed. Falling back to official source...
echo           ^(may need VPN if you're in China; this can be slow^)
set "PLAYWRIGHT_DOWNLOAD_HOST="
python -m playwright install chromium
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install browser.
    echo.
    echo Easiest fix: install Google Chrome from https://www.google.cn/chrome/
    echo            then re-run setup.bat. Chrome registration is instant.
    echo.
    echo Other options:
    echo   - Check internet ^(can you reach https://npmmirror.com?^)
    echo   - If in China: try VPN, then re-run setup.bat
    pause
    exit /b 1
)
echo OK
echo.

:browser_done

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
