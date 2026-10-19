@echo off
setlocal
cd /d "%~dp0"
echo.
echo === AssetHub update ===
echo Close the start.cmd window first if AssetHub is running.
echo.
echo [1/4] Getting the latest code...
git pull
if errorlevel 1 goto :fail

echo [2/4] Updating Python packages...
pushd backend
call uv sync
if errorlevel 1 (popd & goto :fail)

echo [3/4] Updating the database (your data is kept)...
call uv run python -m assethub.migrate
if errorlevel 1 (popd & goto :fail)
popd

echo [4/4] Rebuilding the dashboard...
pushd frontend
call npm install --no-audit --no-fund
if errorlevel 1 (popd & goto :fail)
call npm run build
if errorlevel 1 (popd & goto :fail)
popd

echo.
echo Done. Start AssetHub with start.cmd.
pause
exit /b 0

:fail
echo.
echo Update stopped. Please read the message above.
pause
exit /b 1
