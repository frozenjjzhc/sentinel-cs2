@echo off
REM stop_api.bat - 强制停止 Sentinel API（如果想手动关掉后台进程）
REM 监控任务不受影响
chcp 65001 > nul

echo 正在停止 Sentinel API...

REM 先尝试通过任务计划器停止（如果是它启动的）
schtasks /End /TN "Sentinel API Service" >nul 2>&1

REM 然后杀掉所有占用 8000 端口的 python 进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM 防止漏网，再杀一次所有 backend_api.py 相关 python
wmic process where "name='python.exe' and commandline like '%%backend_api%%'" delete >nul 2>&1

echo OK 完成。
echo （监控任务仍在按计划运行）
pause
