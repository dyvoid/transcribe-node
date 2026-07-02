# ADR 0002: Register pip-installed CUDA DLLs on Windows at load time

- **Status:** Accepted
- **Date:** 2026-07-02

## Context

TranscribeNode installs the CUDA runtime via pip (`nvidia-cublas-cu12`,
`nvidia-cudnn-cu12`) rather than requiring a system CUDA Toolkit install (see
[Architecture Overview](../architecture/overview.md) constraints). Those wheels drop their DLLs
under `site-packages/nvidia/*/bin`.

On Windows, ctranslate2 (the backend under `faster-whisper`) loads these DLLs through the OS loader,
which does not search `site-packages/nvidia/*/bin`. The result is a runtime failure at model load:

```
RuntimeError: Library cublas64_12.dll is not found or cannot be loaded
```

This only surfaces when actually loading a CUDA model, so it passes import-time and unit tests and
fails only in live use. Linux does not hit this because the wheels' `.so` files are resolved
differently.

## Decision

Before loading a model on the `cuda` device, `FasterWhisperEngine.load()` calls
`_register_cuda_dll_dirs()`, which on Windows walks `site-packages/nvidia/*/bin` and registers each
directory with `os.add_dll_directory()`. It is a no-op on non-Windows platforms and is skipped
entirely for CPU loads.

## Consequences

- CUDA transcription works on Windows with the pip-only CUDA approach, keeping the "no system CUDA
  Toolkit" constraint intact.
- The registration is tied to the CUDA load path specifically, so CPU-only runs pay nothing for it.
- If the DLL registration is removed (e.g. as "dead code"), Windows CUDA users regress to the
  `cublas64_12.dll not found` error. This ADR is the record of why it exists.
- Coupled to the wheel layout (`nvidia/*/bin`). If NVIDIA changes where the wheels place DLLs, this
  glob needs updating.
