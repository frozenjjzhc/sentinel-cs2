@echo off
REM Windows Task Scheduler entry for monitor_slow.py (every hour at minute 5)
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist logs mkdir logs
python monitor_slow.py >> logs\monitor_slow.log 2>&1
