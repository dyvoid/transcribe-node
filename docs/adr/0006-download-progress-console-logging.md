# ADR 0006: Download progress as console milestones, not a UI progress bar

- **Status:** Proposed
- **Date:** 2026-07-06

## Context

Models download from HuggingFace on first `POST /engine/load` for a given model and are cached
under `TRANSCRIBENODE_MODELS_DIR`. That download happens synchronously inside `WhisperModel(...)`
construction in `FasterWhisperEngine.load()`, which faster-whisper/`huggingface_hub` does not
expose a progress callback for through the surface this codebase currently uses. For a large model
(`large-v3` is ~6GB) that's minutes of the server appearing to hang, with the `/engine/load` request
just sitting open and the UI stuck on `loading` with no other signal.

The architecture overview records "download progress bars" as explicitly out of scope for v1. That
was the right call for a UI progress bar, which would need either wrapping `huggingface_hub`'s
download internals or polling partial file sizes on disk — both real (if not huge) chunks of work
for what's fundamentally a "did I hang or not" question.

## Decision

Log two milestones to the server console (not the UI) around the model load:

1. Before calling into faster-whisper: check whether the model's cache directory already exists
   under `download_root`. If not, print that a download is starting for that model.
2. After `WhisperModel(...)` returns successfully: print that the model is ready.

This is a `print()`/logging call in `FasterWhisperEngine.load()`, gated on a cheap directory-existence
check, not a bytes-transferred or percentage progress bar. No new dependency, no polling loop, no
UI change, no new endpoint.

## Consequences

- An operator watching the terminal (which is already the norm — `start.bat`/`start.sh` run in a
  visible window) gets a clear "why is this taking a while" signal without touching the UI.
- The UI's `loading` state and its console counterpart can now disagree in granularity (the UI just
  says "loading", the console explains why) — that's accepted as intentional; the UI keeps zero
  download-progress logic per ADR 0005's scope boundary.
- The cache-directory check is a heuristic, not a guarantee: a partially-downloaded or corrupted
  cache directory would be misreported as already cached. This is acceptable because the console
  message is advisory, not load-bearing — faster-whisper's own errors still surface on genuine
  failure.
- If a future need arises for an actual UI progress bar or percentage, that is a separate decision
  and likely requires wrapping `huggingface_hub`'s downloader directly; this ADR does not attempt
  that and should not be read as a stepping stone to it.
