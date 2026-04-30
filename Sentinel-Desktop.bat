@echo off
REM ============================================================
REM Sentinel-Desktop.bat - Launch as native desktop app (silent)
REM   - Uses pythonw (no console window pops up)
REM   - Closing the window minimizes to system tray; backend keeps running
REM   - Right-click tray icon -> "Quit Sentinel" to fully stop
REM   - On crash see desktop_app_error.log next to this bat
REM   Note: kept fully ASCII to avoid Windows codepage issues.
REM ============================================================

chcp 65001 > nul
cd /d "%~dp0"

REM First-run auto-init same as Sentinel.bat
if not exist "m4a4_buzz_kill_state.json" (
    if exist "state.example.json" (
        copy "state.example.json" "m4a4_buzz_kill_state.json" >nul
    )
)

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM Prefer pythonw (silent). Fall back to python with console if pythonw missing.
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw desktop_app.py
    exit /b 0
)

echo [Sentinel-Desktop] pythonw not found, falling back to python with console
python desktop_app.py
if errorlevel 1 (
    echo.
    echo desktop_app.py exited with error. See desktop_app_error.log
    pause
)
