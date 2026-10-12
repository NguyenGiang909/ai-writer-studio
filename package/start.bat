@echo off
rem AI Writer Studio - local desktop launcher
rem Chay writer-api.exe (backend :8765) + node web\server.js (frontend :3300)
rem Dong app bang stop.bat — KHONG dong cua so nay (khong giet process con).
cd /d "%~dp0"

rem build_id.txt do build_package.ps1 ghi — hien thi de doi chieu phien ban
if exist build_id.txt (set /p BUILD_ID=<build_id.txt) else (set BUILD_ID=dev)
echo AI Writer Studio - build %BUILD_ID%

rem backend can environment production de DB/secret roi vao user-data dir
set WRITER_ENV=production
start "" /min writer-api.exe

set PORT=3300
set HOSTNAME=127.0.0.1
start "" /min node.exe web\server.js

rem cho backend len (onefile cold-start co the 3-10s), toi da ~30s
set TRIES=0
:wait_api
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8765/health 2>nul | findstr /b "200" >nul && goto api_ok
set /a TRIES+=1
if %TRIES% GEQ 30 goto api_fail
timeout /t 1 /nobreak >nul
goto wait_api

:api_ok
echo Backend san sang tai http://127.0.0.1:8765
start "" http://127.0.0.1:3300
echo.
echo  AI Writer Studio dang chay tai http://127.0.0.1:3300
echo  Du lieu luu trong %%LOCALAPPDATA%%\AIWriterStudio
echo  Chay stop.bat de dung app va giai phong port.
pause >nul
goto :eof

:api_fail
echo [LOI] Backend khong len duoc sau 30s — xem log hoac chay lai.
echo Kiem tra port 8765 co dang bi chiem khong.
pause >nul
