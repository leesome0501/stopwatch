@echo off
rem Sync connected brokerage accounts, then fetch prices and exchange rates (use with Task Scheduler).
setlocal
cd /d "%~dp0backend"
uv run python -m assethub.sync_brokers
uv run python -m assethub.collect
