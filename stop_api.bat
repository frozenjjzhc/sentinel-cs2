@echo off
REM ============================================================
REM stop_api.bat - Force stop Sentinel API server
REM Monitor tasks (if any in Windows Task Scheduler) are unaffected.
REM Kept fully ASCII to avoid Windows codepage issues.
REM ============================================================

chcp 65001 > nul

echo Stopping Sentinel API...

REM 1. Stop scheduled task version (if installed via setup_autostart.bat)
schtasks /End /TN "Sentinel API Service" >nul 2>&1

REM 2. Kill any process listening on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM 3. Belt-and-suspenders: kill any python.exe running backend_api.py
wmic process where "name='python.exe' and commandline like '%%backend_api%%'" delete >nul 2>&1

echo Done. ^(Monitor tasks in Windows Task Scheduler unaffected.^)
pause
