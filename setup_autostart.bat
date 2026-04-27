@echo off
REM ============================================================
REM setup_autostart.bat - 一次性安装：让 Sentinel API 跟开机自启
REM 安装后，下次登录 Windows 时 API 会静默后台启动（无窗口）
REM 配合 Windows 任务计划器里的监控任务，整套系统全自动
REM ============================================================
chcp 65001 > nul
cd /d "%~dp0"

echo.
echo ============================================================
echo   Sentinel API 自启安装向导
echo ============================================================
echo.
echo 这会在 Windows 任务计划器里创建一个 "Sentinel API Service"
echo 任务，让 API 服务跟你登录 Windows 一起自动启动。
echo.
echo 安装后日常使用：
echo   - 浏览器直接打开 http://localhost:8000 即可
echo   - 不需要再手动开 run_backend_api.bat
echo   - 关闭浏览器不会停止监控（监控由别的任务跑）
echo.
echo 取消安装：运行 uninstall_autostart.bat
echo.
pause

set "VBS_PATH=%~dp0start_api_silent.vbs"
set "TASK_NAME=Sentinel API Service"

REM 删除可能存在的旧任务
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

REM 创建任务：登录时启动，无最高权限（API 只用 127.0.0.1 不需要管理员）
schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "wscript.exe \"%VBS_PATH%\"" ^
    /SC ONLOGON ^
    /F

if errorlevel 1 (
    echo.
    echo X 创建失败。可能需要以管理员身份运行此脚本。
    pause
    exit /b 1
)

echo.
echo OK API 自启已安装。
echo.
echo 立刻启动一次（不用等下次登录）？(Y/N)
set /p RUNNOW=
if /i "%RUNNOW%"=="Y" (
    schtasks /Run /TN "%TASK_NAME%"
    timeout /t 3 /nobreak >nul
    echo.
    echo OK API 已在后台启动。打开浏览器访问 http://localhost:8000
    start "" http://localhost:8000
)

echo.
pause
