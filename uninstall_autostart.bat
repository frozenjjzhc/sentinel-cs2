@echo off
REM Uninstall Sentinel API auto-start.
REM Kept fully ASCII to avoid Windows codepage issues.
chcp 65001 > nul
echo Uninstalling Sentinel API auto-start...
schtasks /Delete /TN "Sentinel API Service" /F
echo.
echo Done. API will no longer start at login.
echo (Monitor tasks in Windows Task Scheduler are unaffected.)
pause
