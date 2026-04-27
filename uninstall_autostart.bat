@echo off
REM 卸载 Sentinel API 自启动任务
chcp 65001 > nul
echo 正在卸载 Sentinel API 自启动...
schtasks /Delete /TN "Sentinel API Service" /F
echo.
echo 完成。下次登录将不再自动启动 API。
echo （监控任务不受影响，仍按计划运行）
pause
