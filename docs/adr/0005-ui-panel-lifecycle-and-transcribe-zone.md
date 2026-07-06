# ADR 0005: UI panel lifecycle and a Transcribe zone

- **Status:** Proposed
- **Date:** 2026-07-06

## Context

The v1 UI is fixed to three zones (Settings, Engine, Live log), and the architecture overview
records model management, download progress, and anything beyond those three zones as explicitly
out of scope. That scope was right for a first release, but it leaves two gaps once the service is
actually used day to day:

- There is no way to transcribe a file from the browser. The UI can load a model and watch the
  live log, but every actual transcription has to go through a separate HTTP client. For an
  operator who just wants to transcribe one file, that's a detour through curl/Postman/a script for
  something the UI is otherwise built to do end-to-end.
- The Settings panel stays interactive after a model is loaded, and nothing in the UI reflects
  that changing the model picker or format at that point doesn't do anything until the engine is
  reloaded. An operator can click around in Settings while a model is loaded and reasonably expect
  it to have an effect; it doesn't.

Both gaps point at the same underlying issue: the UI has no concept of which panel is relevant to
the current engine state. Settings is only meaningful before load; a Transcribe zone is only
meaningful after load. Making that explicit fixes both problems with one mechanism.

## Decision

**Add a fourth zone, Transcribe, between Engine and Live log.** It holds a drag/drop-or-click file
input and, once a job completes, the resulting transcript rendered inline with copy and download
actions. It calls the existing `POST /v1/audio/transcriptions` (or `/translations`) endpoint —
no new backend endpoint is introduced. It exposes a small per-job settings form (task, language,
prompt, response format, word-level timestamps) that mirrors the parameters already accepted by
that endpoint; see [API & Interface Specification](../architecture/api.md) for the exact fields
exposed on this branch.

**Give panels an explicit active/inactive lifecycle, driven entirely by engine state:**

- **Settings** is active while the engine is `idle` or `loading`, and collapses to its header,
  dimmed and non-interactive, once the engine is `loaded`. This matches the existing constraint
  that model selection is disabled once loaded ("Model selection: disabled while a model is
  loaded" per the model-picker behavior in `api.md`) — it now applies to the whole panel, not just
  the model table.
- **Transcribe** is the inverse: collapsed, dimmed, and non-interactive while the engine is `idle`
  or `loading`, and active once the engine is `loaded`.
- Neither panel is user-collapsible. There is no toggle/disclosure control — collapsed state is a
  read-only reflection of engine state, not a UI interaction. This keeps the mechanism simple (one
  state variable drives two panels) and avoids a class of bugs where a manually-collapsed panel
  disagrees with engine state.
- **Engine** and **Live log** are unaffected — they are relevant in every engine state.

## Consequences

- The v1 UI scope constraint in [Architecture Overview](../architecture/overview.md) ("v1 UI scope
  is fixed to three zones... out of scope for v1") no longer holds and is updated by this ADR. Model
  management and request-history persistence remain out of scope; only the zone count and the
  panel-collapse behavior change.
- The UI gains its first piece of state-driven layout logic (collapse tied to engine state). This
  is still presentation-only — the UI continues to hold no business logic of its own; it reflects
  `GET /engine/status`, exactly as Settings and Live log already do.
- The Transcribe zone's per-job form only exposes parameters the currently running branch's
  `/v1/audio/transcriptions` endpoint actually accepts. If that endpoint's parameter set changes
  (e.g. anti-repetition options land from another branch), the form needs a matching update — it is
  not auto-derived from the API.
- No new backend endpoints, no new dependencies. The existing transcription endpoint, existing
  engine status polling, and browser-native `<input type="file">` drag/drop are sufficient.
