# ADR 0004: Configuration resolution order

- **Status:** Accepted
- **Date:** 2026-07-02

## Context

TranscribeNode needs runtime settings: default model, bind host, port, and the models cache
directory. These have to come from somewhere, and operators want more than one knob:

- A checked-in baseline so a fresh clone runs with sensible defaults.
- A per-machine override that doesn't touch version control (different port per box, a custom
  models directory on a bigger disk).
- A per-invocation override for one-off runs (try a different model, bind to `0.0.0.0` for a
  session).

Putting all of these through a single source would force one of those use cases to lose. Putting
them in code means redeploying to change a port. The configuration system has to layer them.

## Decision

Resolve each setting through a fixed precedence chain, highest first:

1. A real environment variable (`TRANSCRIBENODE_*`).
2. A value in a local `.env` file (gitignored; see `.env.example`).
3. The `[tool.transcribenode]` table in `pyproject.toml` (checked in).
4. A built-in default in `config.py`.

`python-dotenv` loads `.env` with `override=False`, so a real env var always wins and `.env` only
fills gaps. The `.env` reader uses `encoding="utf-8-sig"` to tolerate a UTF-8 BOM, which some
Windows editors prepend and would otherwise corrupt the first key (see the fix commit).

`pyproject.toml` is the checked-in baseline: a clone with no `.env` and no env vars runs on the
defaults recorded there. `.env` is the per-machine layer; env vars are the per-invocation layer.

## Consequences

- Operators get three override points without touching code: edit `pyproject.toml` (committed),
  drop a `.env` (local), or export an env var (ephemeral).
- The resolution order is documented in `config.py`, `.env.example`, and the README, so the chain
  is discoverable without reading the implementation.
- Adding a new setting means one line in `Config`, one `os.getenv` call, and one row in the
  README/`.env.example`. No separate schema file or loader framework.
- `.env` is gitignored and must never be committed; `.env.example` is the template and is tracked.
- The BOM-tolerant reader is a Windows-specific hardening, not a general encoding policy. If a
  future setting needs a non-UTF-8 source, that's a separate decision.
