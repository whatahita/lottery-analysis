@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set PY=py -3
) else (
  set PY=python
)

echo 前端启动中：http://127.0.0.1:5173
echo 如果要用手机访问，请把 127.0.0.1 换成这台电脑的局域网 IP。
%PY% -m http.server 5173 --bind 0.0.0.0
pause
