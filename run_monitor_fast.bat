@echo off
REM Windows Task Scheduler entry for monitor_fast.py
REM Run every 10 minutes
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist logs mkdir logs
python monitor_fast.py >> logs\monitor_fast.log 2>&1
