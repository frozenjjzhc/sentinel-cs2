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

REM --- Check state.json ---
echo [4/4] Checking state.json...
if exist "m4a4_buzz_kill_state.json" (
    echo Found existing state.json - will be reused.
) else (
    echo WARNING: m4a4_buzz_kill_state.json not found in this directory.
    echo Make sure you're running this from D:\claude\xuanxiao\
)
echo.

echo ===================================================
echo   Setup complete!
echo ===================================================
echo.
echo Next steps:
echo   1. Run a one-time test:    python monitor_fast.py --test
echo   2. Schedule via Windows Task Scheduler:
echo        Program: %CD%\run_monitor_fast.bat
echo        Trigger: Every 10 minutes
echo.
pause
