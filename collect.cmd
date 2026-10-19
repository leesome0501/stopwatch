@echo off
rem Fetch prices and exchange rates, then sync connected brokerage accounts (use with Task Scheduler).
setlocal
cd /d "%~dp0backend"
uv run python -m assethub.collect
uv run python -m assethub.sync_brokers
