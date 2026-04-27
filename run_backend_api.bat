@echo off
REM Start Sentinel backend API service (FastAPI on port 8000)
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
echo Starting Sentinel API on http://localhost:8000 ...
echo Press Ctrl+C to stop.
python backend_api.py
pause
