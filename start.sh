#!/usr/bin/env bash
# Mac / Linux launcher: sync deps, open the UI, run the server.
set -euo pipefail
cd "$(dirname "$0")"

# The cuda extra is a no-op on macOS (dependency markers exclude it there).
uv sync --extra cuda

# main.py opens the browser at the configured port once the server is ready.
uv run python main.py
