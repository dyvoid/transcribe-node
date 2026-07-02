# TranscribeNode

A self-contained, on-demand local speech-to-text API service for Windows, Mac, and Linux. Launch
via a platform script, configure settings in the browser, hit Start. Exposes an OpenAI-compatible
REST API at `localhost:9000` accepting any audio or video format and returning word-level
transcripts with precise timestamps.

## Status

Active development. The API surface targets 1:1 compatibility with the
[OpenAI Audio Transcription API](https://platform.openai.com/docs/api-reference/audio/createTranscription),
so any base-URL swap to `http://localhost:9000` should work against existing OpenAI-client tooling.

## Getting Started

```
# 1. Install uv: https://astral.sh/uv
# 2. Clone this repo
git clone <repo-url>
cd TranscribeNode

# 3. Run the launcher for your platform (installs deps on first run via uv)
./start.bat   # Windows
./start.sh    # Mac / Linux

# 4. Browser opens automatically at http://localhost:9000
```

## Project Structure

```
docs/            Architecture, decisions, and guides
.prompts/        Versioned prompts that generated significant code
static/          Browser UI (settings, start/stop, live log)
main.py          FastAPI server + serves static UI
pyproject.toml   Dependencies and project metadata
start.bat        Windows launcher
start.sh         Mac / Linux launcher
AGENTS.md        Context and instructions for AI agents
```

## Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [API & Interface Spec](docs/architecture/api.md)
- [Architecture Decisions](docs/adr/)
- [Git Strategy](docs/git-strategy.md)
- [Roadmap](docs/ROADMAP.md)
