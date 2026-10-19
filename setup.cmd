@echo off
setlocal
cd /d "%~dp0"
echo.
echo === AssetHub setup ===
echo.
where uv >nul 2>nul || (
  echo [!] uv is not installed. Run this, then open a NEW terminal and run setup.cmd again:
  echo     winget install -e --id astral-sh.uv
  goto :fail
)
where npm >nul 2>nul || (
  echo [!] Node.js is not installed. Run this, then open a NEW terminal and run setup.cmd again:
  echo     winget install -e --id OpenJS.NodeJS.LTS
  goto :fail
)

echo [1/3] Installing Python packages...
pushd backend
call uv sync
if errorlevel 1 (popd & goto :fail)

echo.
echo [2/3] Preparing the database...
call uv run python -m assethub.setup_local %*
if errorlevel 1 (popd & goto :fail)
popd

echo [3/3] Building the dashboard...
pushd frontend
call npm install --no-audit --no-fund
if errorlevel 1 (popd & goto :fail)
call npm run build
if errorlevel 1 (popd & goto :fail)
popd

echo.
echo Done. Double-click start.cmd to open AssetHub.
pause
exit /b 0

:fail
echo.
echo Setup stopped. Please read the message above.
pause
exit /b 1
