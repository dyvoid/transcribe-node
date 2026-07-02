# Roadmap

| Feature | Status | Description | ADR |
|---------|--------|-------------|-----|
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
