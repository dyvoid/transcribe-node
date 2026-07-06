# Roadmap

| Feature | Status | Description | ADR |
|---------|--------|-------------|-----|
| Browser-based transcription (drag/drop upload + download) | Candidate | Transcribe zone between Engine and Live log; upload a file via drag/drop or file picker, view/copy/download the result | [0005](adr/0005-ui-panel-lifecycle-and-transcribe-zone.md) |
| Panel active/inactive lifecycle | Candidate | Settings panel collapses once the engine is loaded; Transcribe panel stays collapsed until it is | [0005](adr/0005-ui-panel-lifecycle-and-transcribe-zone.md) |
| Model download milestones in console | Candidate | Log "downloading"/"ready" milestones to the server console during model load | [0006](adr/0006-download-progress-console-logging.md) |
| Batch queue for processing multiple files | Candidate | Queue up multiple files instead of one-at-a-time | — |
| Speaker diarization via WhisperX | Candidate | Second engine adapter, "who said what" | — |
| Real-time streaming transcription mode | Candidate | Stream partial transcripts instead of batch-only | — |
| Mac Metal acceleration via mlx-whisper | Candidate | Native Apple Silicon acceleration path | — |

---

## Archive

Shipped in v1:

| Feature | Description |
|---------|-------------|
| Core transcription API | `/v1/audio/transcriptions` + `/translations`, OpenAI-compatible, faster-whisper backend |
| Hardware detection + model recommendation | `GET /system`; probes device/compute type/memory and recommends a model |
| Browser UI (settings, start/stop, live log) | Operator console, three zones |
| Runtime configuration | `.env` + `TRANSCRIBENODE_*` env vars + `pyproject.toml` + defaults, with documented precedence |
| Configurable host and port | Bind to any interface/port; launcher opens the browser at the resolved address |
