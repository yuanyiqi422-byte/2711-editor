@echo off
chcp 65001 >nul
title 2711编辑器 · 2711 Editor
cd /d "%~dp0"

if not exist "backend\.env" (
  echo.
  echo [提示] 找不到 backend\.env
  if exist "backend\.env.example" (
    copy /Y "backend\.env.example" "backend\.env" >nul
    echo 已从 .env.example 复制，请编辑 backend\.env 填入 AI_API_KEY 后重新运行。
  ) else (
    echo 请创建 backend\.env 并填入 AI_API_KEY。
  )
  echo.
  pause
  exit /b 1
)

echo.
echo [启动] 释放 8010 端口（若被占用）…
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

cd /d "%~dp0backend"

echo 正在安装/检查依赖…
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" -m pip install -r requirements.txt -q
  set "PY=%~dp0.venv\Scripts\python.exe"
) else (
  python -m pip install -r requirements.txt -q
  set "PY=python"
)

echo.
echo 启动中… http://127.0.0.1:8010
echo 后端代码与 .env 变更会自动 reload，无需手动重启
echo 按 Ctrl+C 停止
echo.

start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8010"

"%PY%" -m uvicorn main:app --host 127.0.0.1 --port 8010 --reload --reload-dir . --reload-include .env
pause
