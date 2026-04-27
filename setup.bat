@echo off
REM ============================================================
REM CS2 Skin Monitor - One-Time Setup
REM 1. Installs Python dependencies
REM 2. Downloads Playwright Chromium
REM 3. Verifies state.json exists
REM ============================================================

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
    echo ERROR: Python not found in PATH.
    echo Install Python 3.9+ from https://www.python.org/downloads/
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
python -m playwright install chromium
if errorlevel 1 (
    echo ERROR: Failed to install Chromium.
    pause
    exit /b 1
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
