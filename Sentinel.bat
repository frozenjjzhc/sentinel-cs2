@echo off
REM ============================================================
REM Sentinel.bat - One-click launcher for the entire system
REM   - Starts API on port 8000
REM   - Embedded scheduler runs monitor_fast/slow/daily_review
REM   - Opens browser to dashboard automatically
REM
REM Close this window to stop everything (API + monitoring).
REM
REM Note: kept fully ASCII to avoid Windows codepage issues.
REM ============================================================

chcp 65001 > nul
cd /d "%~dp0"

REM First-run auto-init: copy state.example.json -> state.json
if not exist "m4a4_buzz_kill_state.json" (
    if exist "state.example.json" (
        echo [Sentinel] First run - creating state.json from state.example.json
        copy "state.example.json" "m4a4_buzz_kill_state.json" >nul
        echo [Sentinel] OK. Configure tokens / monitored items via Settings page after launch.
        echo.
    ) else (
        echo [Sentinel] ERROR: state.example.json not found.
        echo Please re-extract the project archive.
        pause
        exit /b 1
    )
)

REM Detect if port 8000 is already in use
netstat -ano | findstr ":8000.*LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [Sentinel] API already running on port 8000. Opening dashboard...
    timeout /t 1 /nobreak >nul
    start "" http://localhost:8000
    exit /b 0
)

echo.
echo ============================================================
echo   Sentinel - Starting...
echo   API + Embedded Monitor + Dashboard - All in one process
echo ============================================================
echo.
echo   API:       http://localhost:8000
echo   Monitor:   embedded (auto-starts with API)
echo              - monitor_fast:  every 10 min
echo              - monitor_slow:  every 60 min
echo              - daily_review:  daily at 23:00
echo   Stop:      close this window (Ctrl+C or X button)
echo.

REM Open browser after 4-second delay (in background)
start "Sentinel Browser" /B cmd /c "timeout /t 4 /nobreak >nul && start """" http://localhost:8000"

REM Run API in foreground (closing window stops everything)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python backend_api.py
