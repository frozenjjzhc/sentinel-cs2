@echo off
REM ============================================================
REM setup_autostart.bat - One-time install: auto-start API on login
REM After install, the API silently starts every time you log into Windows.
REM Works alongside Windows Task Scheduler monitor tasks for full automation.
REM Kept fully ASCII to avoid Windows codepage issues.
REM ============================================================
chcp 65001 > nul
cd /d "%~dp0"

echo.
echo ============================================================
echo   Sentinel API Auto-start Install Wizard
echo ============================================================
echo.
echo This creates a Windows Scheduled Task named "Sentinel API Service"
echo so the API starts automatically when you log into Windows.
echo.
echo After install:
echo   - Just open http://localhost:8000 in your browser
echo   - No need to double-click run_backend_api.bat or Sentinel.bat
echo   - Closing browser does NOT stop monitoring (monitor uses a separate task)
echo.
echo To uninstall later: run uninstall_autostart.bat
echo.
pause

set "VBS_PATH=%~dp0start_api_silent.vbs"
set "TASK_NAME=Sentinel API Service"

REM Delete existing task if present
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

REM Create task: trigger on logon, normal user privilege (API only binds 127.0.0.1)
schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "wscript.exe \"%VBS_PATH%\"" ^
    /SC ONLOGON ^
    /F

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create task. Try running this script as Administrator.
    pause
    exit /b 1
)

echo.
echo OK - API auto-start installed.
echo.
set /p RUNNOW=Start API now without waiting for next login? (Y/N):
if /i "%RUNNOW%"=="Y" (
    schtasks /Run /TN "%TASK_NAME%"
    timeout /t 3 /nobreak >nul
    echo.
    echo OK - API started in background. Opening dashboard...
    start "" http://localhost:8000
)

echo.
pause
