@echo off
REM Windows launcher: sync deps, open the UI, run the server.
cd /d "%~dp0"

call uv sync --extra cuda
if errorlevel 1 (
    echo uv sync failed. Is uv installed? See https://astral.sh/uv
    pause
    exit /b 1
)

REM main.py opens the browser at the configured port once the server is ready.
uv run python main.py
