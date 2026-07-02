#!/usr/bin/env bash
# Mac / Linux launcher: sync deps, open the UI, run the server.
set -euo pipefail
cd "$(dirname "$0")"

uv sync

# Open the browser shortly after the server starts.
( sleep 2; python3 -m webbrowser "http://localhost:9000" >/dev/null 2>&1 || true ) &

uv run python main.py
