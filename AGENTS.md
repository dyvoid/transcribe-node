# AGENTS.md

This file is the primary context source for AI agents working in this repository. Read it before
doing anything else, and follow the instructions here. For deeper context on a specific topic,
follow the links in the index at the bottom.

This is the one place that governs how AI agents behave in this repo. The linked docs carry context
and decisions; they deliberately avoid AI-specific instructions so there's no second source of truth.

---

## Project Overview

TranscribeNode is a self-contained, on-demand local speech-to-text API service for Windows, Mac,
and Linux. A platform launcher script starts a FastAPI server that serves both a browser-based
settings UI and an OpenAI-compatible REST API at `localhost:9000` (default port,
configurable via `TRANSCRIBENODE_PORT`). It accepts any audio or video
format and returns word-level transcripts with precise timestamps, using `faster-whisper` as the
transcription backend. It's intended as a shared primitive: any project that can make an HTTP
request can use it as a transcription service.

---

## Architecture

Python service managed with `uv`, built on FastAPI/uvicorn, with `faster-whisper` doing the actual
transcription. The design deliberately separates **process lifecycle** (owned by the launcher --
the server runs as long as the window is open) from **engine state** (owned by the engine module --
which model is loaded and whether the service accepts work). See
[Architecture Overview](docs/architecture/overview.md) for the full picture, and
[the ADR log](docs/adr/) for the reasoning behind specific decisions.

---

## AI Instructions

### You can do these freely
- Write, edit, and refactor code that follows the patterns already in the codebase
- Create new files consistent with existing conventions
- Update documentation to match code changes
- Add tests for new or existing functionality

### These need human review before they land
- `.gitignore` and `.gitattributes`
- Authentication, authorization, or anything touching secrets
- Dependency changes (lockfiles, package manifests)
- Refactors that cut across multiple modules
- CI/CD configuration

### Do not do these
- Commit directly to `main`
- Delete or rename files without being asked
- Change architecture without recording an ADR in `docs/adr/`
- Add third-party dependencies without explicit instruction

---

## Conventions

### Branching
Short-lived branches only: `task/`, `fix/`, `experiment/`. Details in [Git Strategy](docs/git-strategy.md).

### Commits
One commit per task or prompt session. [Conventional Commits](https://www.conventionalcommits.org).
Put AI context in the body, not the subject:

```
feat(scope): short imperative summary

ai-assisted: <model>
```

### Python specifics
- Dependency manager: `uv`. Do not switch to poetry/pip-tools without an ADR. Python version is
  pinned in `pyproject.toml`.
- Commit `uv.lock`; never commit `.venv/`.
- Formatting/linting: `ruff` for lint + format, `mypy` for type checking. Match existing style
  rather than introducing new tooling.
- Type hints are expected on public functions.
- Flat layout (no `src/`): `main.py` at the project root, application code in plain modules
  alongside it (see [Architecture Overview](docs/architecture/overview.md)).
- Tests (once added) run with `pytest` and live under `tests/`.

---

## Document Index

| Document | What it covers |
|---|---|
| [Architecture Overview](docs/architecture/overview.md) | System structure, key components, data flow |
| [API & Interface Spec](docs/architecture/api.md) | Endpoint spec, model table, hardware detection, UI zones, launchers |
| [ADR Log](docs/adr/) | Architecture decisions and their rationale |
| [Roadmap](docs/ROADMAP.md) | Feature candidates, planned work, and status |
| [Git Strategy](docs/git-strategy.md) | Branching, merging, commit rules |
