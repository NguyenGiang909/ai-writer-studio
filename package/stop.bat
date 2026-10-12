@echo off
rem Dung AI Writer Studio: giet writer-api.exe + tien trinh node chay web\server.js
cd /d "%~dp0"

taskkill /f /im writer-api.exe >nul 2>&1
if %errorlevel%==0 (echo [ok] da dung writer-api.exe) else (echo [--] writer-api.exe khong chay)

rem node.exe trong package chay server.js — giet theo command line chua 'web\server.js'
for /f "tokens=2" %%p in ('wmic process where "name='node.exe' and commandline like '%%server.js%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
  taskkill /f /pid %%p >nul 2>&1 && echo [ok] da dung node.exe (pid %%p)
)
rem fallback: PowerShell (wmic co the bi bo tren Windows moi)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='node.exe'\" | Where-Object { $_.CommandLine -like '*server.js*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('[ok] da dung node.exe (pid ' + $_.ProcessId + ')') }" 2>nul

echo Xong. Du lieu van con trong %%LOCALAPPDATA%%\AIWriterStudio.
pause >nul
