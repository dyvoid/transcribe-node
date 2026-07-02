@echo off
REM Windows launcher: sync deps, open the UI, run the server.
cd /d "%~dp0"

call uv sync --extra cuda
if errorlevel 1 (
    echo uv sync failed. Is uv installed? See https://astral.sh/uv
    pause
    exit /b 1
)

start "" "http://localhost:9000"
uv run python main.py
