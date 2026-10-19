@echo off
setlocal
cd /d "%~dp0backend"
if not exist .env (
  echo Run setup.cmd first.
  pause
  exit /b 1
)
echo.
echo AssetHub is starting at http://localhost:8000/
echo Keep this window open while you use it. Close it to stop.
echo.
start "" /min cmd /c "timeout /t 4 /nobreak >nul && explorer http://localhost:8000/"
uv run uvicorn assethub.main:app --host 127.0.0.1 --port 8000
pause
