' start_api_silent.vbs - 静默启动 Sentinel API（无控制台窗口弹出）
' 用于 Windows 任务计划程序的"登录时启动"
Set WshShell = CreateObject("WScript.Shell")
strPath = WScript.ScriptFullName
strFolder = Left(strPath, InStrRev(strPath, "\") - 1)
WshShell.CurrentDirectory = strFolder
WshShell.Run """" & strFolder & "\run_backend_api.bat""", 0, False
