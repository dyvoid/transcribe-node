# API & Interface Specification

Detailed specification for TranscribeNode's HTTP surface, model selection, hardware detection, the
browser UI, and the launcher scripts. See [Architecture Overview](overview.md) for how these pieces
fit together; this document is the spec-level detail behind them.

---

## API Endpoints

Implements the [OpenAI Audio Transcription API](https://platform.openai.com/docs/api-reference/audio/createTranscription)
spec 1:1. Any library or tool targeting `api.openai.com` works against this service with a base URL
swap to `http://localhost:9000`.

### `POST /v1/audio/transcriptions`
Primary transcription endpoint.

**Parameters (multipart/form-data):**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `file` | file | required | Any audio or video file (mp4, mkv, mp3, wav, m4a, etc.) |
| `model` | string | config default | Model to use, e.g. `whisper-1` or a local model name |
| `language` | string | auto | ISO-639-1 language code e.g. `nl`, `en` |
| `prompt` | string | — | Optional context to guide transcription style |
| `response_format` | string | `json` | `json`, `text`, `srt`, `vtt`, `verbose_json` |
| `temperature` | float | `0` | Sampling temperature |
| `timestamp_granularities` | array | `["segment"]` | `segment` and/or `word` — pass `["word"]` for per-word timestamps |
| `vad_filter` | bool | `true` | Non-standard. Silero VAD strips silence/noise before transcription. Reduces repetition loops. |
| `condition_on_previous_text` | bool | `false` | Non-standard. When `false`, each segment is decoded without feeding prior output back as context, breaking repetition feedback loops. |

**Response (`verbose_json` — recommended for pipeline use):**
```json
{
  "task": "transcribe",
  "language": "en",
  "duration": 142.3,
  "text": "Full transcript here...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 3.2,
      "text": "Hello and welcome",
      "words": [
        { "word": "Hello", "start": 0.0, "end": 0.4 },
        { "word": "and", "start": 0.4, "end": 0.6 },
        { "word": "welcome", "start": 0.6, "end": 1.1 }
      ]
    }
  ]
}
```

### `POST /v1/audio/translations`
Same as transcriptions but always outputs English, regardless of source language.

Whisper's `translate` task was only trained on X→English pairs, not X→Y for arbitrary target
languages, so there is no `target_language` parameter — English is the only output. This mirrors
the OpenAI API itself, not a limitation specific to this service. Non-English targets require a
separate text-to-text translation step downstream of this endpoint.

### `GET /system`
Returns detected hardware (device, compute type, available memory) and the recommended model for
this machine. The UI reads this on load. Non-standard.

### `POST /engine/load` · `POST /engine/unload` · `GET /engine/status`
Control and report engine state — which model is loaded and whether the service is accepting work.
These back the UI's Start/Stop controls. Non-standard.

### `GET /health`
Returns process liveness. Non-standard convenience endpoint.

### `GET /v1/models`
Returns available models in OpenAI list format. Non-standard but useful for tooling.

---

## Model Selection

| Model | VRAM | Quality | Use case |
|-------|------|---------|----------|
| `large-v3` | ~6GB | Best | High quality batch transcription |
| `distil-large-v3` | ~4GB | Near-large | Faster, smaller footprint |
| `large-v3-turbo` | ~3GB | Good | Speed/quality balance |
| `medium` | ~3GB | Good | Constrained VRAM |
| `small` | ~2GB | OK | Fast previews |

Default model is set in `pyproject.toml` and can be overridden per-request.

The server recommends a model by comparing detected memory against the requirements above: it picks
the highest-quality model that fits comfortably, leaving headroom. This recommendation is computed
server-side and exposed via `GET /system`. It is advisory only — any model can be selected manually.

Models download from HuggingFace on first use and are cached in `/models`. Subsequent starts load
from cache.

---

## Hardware Detection

On startup the server queries available hardware and exposes it via `GET /system`. The browser UI
uses this to recommend a model.

| Platform | Detection method | Acceleration |
|----------|-----------------|--------------|
| Windows / Linux + NVIDIA | `nvidia-smi` | CUDA |
| Windows / Linux (no GPU) | Fallback | CPU (int8) |
| Mac (Apple Silicon) | `system_profiler` | Metal / CPU |
| Mac (Intel) | Fallback | CPU (int8) |

Compute type selected automatically:
- NVIDIA GPU → `int8_float16`
- CPU / Mac → `int8`

---

## Browser UI

Served by FastAPI at `http://localhost:9000` (default port, configurable via
`TRANSCRIBENODE_PORT`). Opened automatically by the server on startup at the resolved
host and port. Single screen, no navigation.

**Four zones, top to bottom: Settings, Engine, Transcribe, Live log.** See
[ADR 0005](../adr/0005-ui-panel-lifecycle-and-transcribe-zone.md) for why Transcribe exists and how
panel active/inactive state works.

**Settings** — configured before loading a model:
- Model picker with spec table (memory, quality, use case) inline. On load, the UI reads `GET /system`
  and highlights the server-recommended model. User can select any model regardless.
- Language (default: auto-detect)
- Response format default
- Port

Active while the engine is `idle`/`loading`. Collapses to its header, dimmed and non-interactive,
once the engine is `loaded` — there is no user control to expand it manually; it re-expands only
when the engine returns to `idle`.

**Engine** — Start / Stop button, loads or unloads the selected model (engine state). Explicit user
action; no model is loaded until clicked. The button reflects current engine state. This does not
start or stop the server process — the process runs as long as the window is open. Always active,
regardless of engine state.

**Transcribe** — the inverse of Settings: collapsed, dimmed, and non-interactive while the engine is
`idle`/`loading`, active once the engine is `loaded`. Holds:
- A drag/drop-or-click file input.
- A small per-job form exposing the parameters this branch's `/v1/audio/transcriptions` /
  `/translations` endpoints accept: task (transcribe/translate), language, prompt, response format,
  word-level timestamps, and the anti-repetition toggles `vad_filter` (on by default) and
  `condition_on_previous_text` (off by default). `temperature` is intentionally not exposed
  (advanced, rarely needed). This form is authored by hand, not derived from the API schema, so it
  must be updated whenever the endpoint's parameter set changes.
- On completion: the transcript rendered inline, with a copy-to-clipboard action and a download
  action (file named after the source file, extension matching the selected response format).

Calls the existing transcription endpoints directly; no new backend surface.

**Live log** — scrolling feed of incoming requests once a model is loaded: timestamp,
filename, model used, processing time, status. Always active, regardless of engine state.

**Scope:** the four zones above and nothing more. Model management (deleting cached models),
request history persistence, and authentication are explicitly out of scope. Download progress is
console-only (see [ADR 0006](../adr/0006-download-progress-console-logging.md)), not a UI
progress bar. The UI is an operator console, not an admin panel, and holds no logic the API
doesn't already expose.

---

## Launchers

Two separate scripts, each doing exactly one thing for their platform.

**`start.bat` (Windows)**
1. Runs `uv sync --extra cuda` to ensure dependencies (including GPU libraries) are installed
2. Starts the FastAPI server via `uv run python main.py`
3. Close the window to stop the process (and with it the UI and API)

**`start.sh` (Mac / Linux)**
Same steps, Unix paths and commands. Mark executable with `chmod +x start.sh` after cloning.

The server itself opens the browser at the configured port once it's accepting connections, so
changing the port (via `TRANSCRIBENODE_PORT` or `pyproject.toml`) opens the correct URL without
touching the launcher.

### Platform Notes
- **Windows / Linux:** NVIDIA GPU detected via `nvidia-smi`, VRAM reported to UI
- **Mac:** No NVIDIA support. Apple Silicon unified memory queried via `system_profiler`. Runs on
  CPU with Metal acceleration where available via `mlx` or falls back to standard CPU inference.

---

## Setup (One-Time Per Machine)

1. Install `uv` from `astral.sh/uv`
2. Clone or copy the project folder to the machine
3. Run `start.bat` (Windows) or `./start.sh` (Mac/Linux) — uv creates the venv and installs
   dependencies on first run
4. Browser opens automatically at the resolved host and port (default `http://localhost:9000`)
5. First transcription for a given model triggers a download (~3GB for large-v3), cached after that
