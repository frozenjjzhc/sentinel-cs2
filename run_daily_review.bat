@echo off
REM Windows Task Scheduler entry for daily_review.py (every day at 23:00)
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist logs mkdir logs
python daily_review.py >> logs\daily_review.log 2>&1
