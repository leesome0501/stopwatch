@echo off
rem Fetch the latest prices and exchange rates once (use with Task Scheduler).
setlocal
cd /d "%~dp0backend"
uv run python -m assethub.collect
