@echo off
chcp 65001 >nul
cd /d "%~dp0backend"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set PY=py -3
) else (
  set PY=python
)

echo 正在创建 Python 虚拟环境...
%PY% -m venv .venv
if errorlevel 1 (
  echo.
  echo 没有找到 Python。请先安装 Python 3.11 或 3.12，然后重新运行本文件。
  echo 下载地址：https://www.python.org/downloads/
  pause
  exit /b 1
)

echo 正在安装后端依赖...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo 依赖安装失败。请检查网络，或重新运行本文件。
  pause
  exit /b 1
)

echo.
echo 后端依赖安装完成。
pause
