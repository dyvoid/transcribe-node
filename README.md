# TranscribeNode

[![CI](https://github.com/dyvoid/transcribe-node/actions/workflows/ci.yml/badge.svg)](https://github.com/dyvoid/transcribe-node/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Managed with uv](https://img.shields.io/badge/managed%20with-uv-de5fe9.svg)
![Built with FastAPI](https://img.shields.io/badge/built%20with-FastAPI-009688.svg)
![Backend: faster-whisper](https://img.shields.io/badge/backend-faster--whisper-ff6f00.svg)

A self-contained, on-demand local speech-to-text API service for Windows, Mac, and Linux. Launch it
with one script, pick a model in the browser, hit **Start**. It exposes an OpenAI-compatible REST
API at `http://localhost:9000` that accepts any audio *or video* file and returns transcripts with
segment- and word-level timestamps — all running locally, no data leaves your machine.

It's built as a shared primitive: anything that can make an HTTP request can use it for
transcription, and any tool written against the OpenAI audio API works by swapping the base URL.

## Features

- **OpenAI-compatible** — implements `POST /v1/audio/transcriptions` and `/v1/audio/translations`
  1:1, so existing OpenAI client libraries work with a base-URL swap.
- **Any audio or video format** — mp4, mkv, mov, mp3, wav, m4a, and more; the audio track is
  decoded automatically.
- **Word-level timestamps** via `response_format=verbose_json` with `timestamp_granularities=word`.
- **Multiple output formats** — `json`, `text`, `srt`, `vtt`, `verbose_json`.
- **Local and private** — powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper);
  audio never leaves the machine.
- **GPU or CPU** — automatic NVIDIA CUDA detection with CPU fallback. CUDA libraries install via
  pip, so no system CUDA Toolkit is required.
- **Operator UI** — a single-screen browser console to pick a model, start/stop the engine, and
  watch a live request log.

## Requirements

- [uv](https://astral.sh/uv) (manages Python, the virtualenv, and dependencies — no system Python
  needed)
- Optional: an NVIDIA GPU with current drivers for CUDA acceleration. Without one, it runs on CPU.

## Quick Start

```bash
git clone <repo-url>
cd TranscribeNode

# Windows
./start.bat

# Mac / Linux
chmod +x start.sh   # first time only
./start.sh
```

The launcher runs `uv sync` (installs everything on first run), starts the server, and opens
`http://localhost:9000`. In the UI, pick a model and click **Start** — the first load downloads the
model from HuggingFace (cached under `models/` afterward).

## Usage

Transcribe a file (plain text):

```bash
curl -X POST http://localhost:9000/v1/audio/transcriptions \
  -F "file=@meeting.mp4" \
  -F "response_format=text"
```

Word-level timestamps:

```bash
curl -X POST http://localhost:9000/v1/audio/transcriptions \
  -F "file=@meeting.mp4" \
  -F "response_format=verbose_json" \
  -F "timestamp_granularities=word"
```

Generate subtitles:

```bash
curl -X POST http://localhost:9000/v1/audio/transcriptions \
  -F "file=@meeting.mp4" -F "response_format=srt" -o meeting.srt
```

Use it from the OpenAI Python client by pointing at the local base URL:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:9000/v1", api_key="not-needed")
with open("meeting.mp4", "rb") as f:
    print(client.audio.transcriptions.create(model="large-v3", file=f).text)
```

See the [API & Interface Spec](docs/architecture/api.md) for every endpoint, parameter, and the full
`verbose_json` schema.

## Models

The server detects your hardware and recommends a model on load; you can pick any of them manually.

| Model | VRAM | Quality | Use case |
|-------|------|---------|----------|
| `large-v3` | ~6GB | Best | High quality batch transcription |
| `distil-large-v3` | ~4GB | Near-large | Faster, smaller footprint |
| `large-v3-turbo` | ~3GB | Good | Speed/quality balance |
| `medium` | ~3GB | Good | Constrained VRAM |
| `small` | ~2GB | OK | Fast previews |

Change the default in `pyproject.toml` under `[tool.transcribenode]`.

## Project Structure

```
main.py            FastAPI server + serves the UI
engine.py          Engine interface + faster-whisper adapter + state manager
hardware.py        Device / compute-type / memory detection
catalog.py         Model catalog + recommendation
config.py          Config from pyproject.toml + env overrides
formatting.py      text / srt / vtt / verbose_json output
static/            Browser UI
tests/             Unit + API tests
docs/              Architecture, ADRs, and guides
start.bat/.sh      Launchers
```

## Development

```bash
uv sync                # base install (CPU); tests and checks run on this
uv sync --extra cuda   # add NVIDIA CUDA libraries to exercise the GPU path
uv run pytest          # tests
uv run ruff check .    # lint
uv run mypy .          # type check
```

The launchers (`start.bat` / `start.sh`) install the `cuda` extra for you; it's a no-op on macOS.

## Notes & Limitations

- **`/v1/audio/translations` only outputs English.** This mirrors Whisper's `translate` task, which
  was trained X→English only. Other target languages need a separate translation step.
- One model is loaded at a time; transcription requests are processed serially.
- v1 UI is an operator console only — no model management, download bars, request history, or auth.

## License

Released under the [MIT License](LICENSE).

## Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [API & Interface Spec](docs/architecture/api.md)
- [Architecture Decisions](docs/adr/)
- [Git Strategy](docs/git-strategy.md)
- [Roadmap](docs/ROADMAP.md)
