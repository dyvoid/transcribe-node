# Architecture Overview

## What this is

TranscribeNode is a self-contained, on-demand local speech-to-text API service for Windows, Mac,
and Linux. A platform launcher script starts a FastAPI server that serves both a browser-based
settings UI and an OpenAI-compatible REST API at `localhost:9000`. It accepts any audio or video
format and returns word-level transcripts with precise timestamps, using `faster-whisper` as the
transcription backend. It's designed as a shared primitive: any project that can make an HTTP
request can use it for transcription.

## Shape

Two lifecycles are kept deliberately separate:

- **Process lifecycle** -- owned by the launcher script (`start.bat` / `start.sh`). Starting the
  process serves the UI and API; killing the process (closing the window) stops everything.
- **Engine state** -- owned by the engine module. Which model is loaded, and whether the service is
  accepting transcription work. The UI's Start/Stop controls this; it loads or unloads a model, it
  does not start or stop the process.

```
Launcher (start.bat/.sh)
  -> uv sync, uv run
  -> FastAPI process (serves UI + API for its lifetime)
       -> UI (static/index.html): reads engine state + hardware info, controls load/unload
       -> API (/v1/audio/*, /system, /engine/*, /health, /v1/models)
       -> Engine: load(model) / unload() / status() / transcribe(audio, options)
            -> faster-whisper adapter (v1) -- future: WhisperX adapter for diarization
       -> Hardware detection: device, compute type, available memory
       -> Recommendation: maps detected hardware -> best-fitting model
```

## Key components

- **Engine** -- wraps the transcription backend behind a stable interface: `load(model)`,
  `unload()`, `status()`, `transcribe(audio, options) -> Result`, where `Result` is already shaped
  to the OpenAI response schema. `faster-whisper` is the only adapter in v1; a second adapter
  (WhisperX, for diarization) is anticipated, which is why this interface exists as a real seam.
- **Hardware detection** -- single module that probes the platform and returns device, compute
  type, and available memory together, since detection and compute-type selection are one concept.
- **Recommendation** -- maps detected hardware to the best-fitting model. Lives server-side behind
  the API so any caller (UI, future CLI, script) gets the same answer.
- **API** -- the OpenAI-compatible HTTP surface. One implementation; the leverage is on the caller
  side (any OpenAI-client tooling works with a base-URL swap).
- **UI** -- operator console served by the API. Reads engine state and hardware info, displays the
  recommendation, controls load/unload. Holds no business logic of its own.

## Data / control flow

A typical transcription request: client `POST`s a file to `/v1/audio/transcriptions` ->
API validates the request and engine state -> Engine runs the loaded `faster-whisper` model against
the audio -> Result is shaped into the OpenAI response schema (`json`, `text`, `srt`, `vtt`, or
`verbose_json`) -> returned to the caller. The live log on the UI reflects each request via engine
status.

## Python structure

- Flat layout, no `src/` directory: `main.py` at the project root serves the FastAPI app and the
  static UI; supporting modules (engine, hardware detection, recommendation) sit alongside it as
  plain Python modules.
- Dependency manager: `uv`. Dependencies and metadata in `pyproject.toml`; lockfile (`uv.lock`) is
  committed.
- Models cache to `/models`, downloaded from HuggingFace on first use.
- Tests, once added, run with `pytest` under `tests/`.

## Constraints

- No system-level CUDA Toolkit install required -- CUDA libraries come via pip
  (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`); NVIDIA drivers alone are sufficient.
- No system Python required -- `uv` manages Python, the venv, and dependencies in one tool.
- API surface must implement the OpenAI Audio Transcription API 1:1 for `/v1/audio/transcriptions`
  and `/v1/audio/translations`; non-standard endpoints (`/system`, `/engine/*`, `/health`,
  `/v1/models`) are additive, not replacements.
- v1 UI scope is fixed to three zones (settings, start/stop, live log). Model management, download
  progress bars, request history persistence, and authentication are explicitly out of scope for v1.

## Decisions

The reasoning behind specific choices lives in the [ADR log](../adr/). Start there before changing
anything structural.

## Further detail

The full endpoint spec (parameters, response schemas), model selection table, hardware detection
table, browser UI zone spec, and launcher script behavior live in
[API & Interface Specification](api.md).
