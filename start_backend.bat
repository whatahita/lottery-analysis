@echo off
chcp 65001 >nul
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
  echo 还没有安装后端依赖，请先双击 setup_backend.bat
  pause
  exit /b 1
)

echo 后端启动中：http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
