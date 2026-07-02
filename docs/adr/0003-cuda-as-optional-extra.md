# ADR 0003: Ship CUDA libraries as an optional extra, not a core dependency

- **Status:** Accepted
- **Date:** 2026-07-02

## Context

TranscribeNode installs the CUDA runtime via pip rather than a system CUDA Toolkit
(see [ADR 0002](0002-windows-cuda-dll-registration.md) and the overview constraints). Originally the
`nvidia-cublas-cu12` and `nvidia-cudnn-cu12` wheels were listed as core dependencies, gated with a
`platform_system != 'Darwin'` marker.

That made every non-macOS install pull ~1 GB of GPU libraries — including CI on GitHub's Ubuntu
runners, which has no GPU and runs the tests on CPU/stubs. CPU-only users paid the same cost for
libraries they never load. The base install was heavier than the common case needs.

## Decision

Move the CUDA wheels into an optional dependency group, `[project.optional-dependencies] cuda`.

- The launchers (`start.bat`, `start.sh`) run `uv sync --extra cuda`, so end users on real machines
  get GPU support automatically.
- The `platform_system != 'Darwin'` markers stay on the extra, so requesting it on macOS is a no-op
  and `start.sh` needs no OS branching.
- CI and plain `uv sync` (used for development and testing) do **not** install the extra, keeping
  those environments lean.

## Consequences

- CI installs no GPU libraries; test runs are faster and lighter.
- CPU-only deployments have a smaller footprint.
- Developers who want to exercise the CUDA path locally must run `uv sync --extra cuda` (documented
  in the README).
- The lockfile still resolves the extra, so `uv.lock` continues to pin the CUDA wheels for
  reproducibility when the extra is requested.
