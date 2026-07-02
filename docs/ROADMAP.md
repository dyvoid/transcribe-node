# Roadmap

| Feature | Status | Description | ADR |
|---------|--------|-------------|-----|
| Core transcription API | Planned | `/v1/audio/transcriptions` + `/translations`, OpenAI-compatible, faster-whisper backend | — |
| Hardware detection + model recommendation | Planned | `GET /system`; probes device/compute type/memory and recommends a model | — |
| Browser UI (settings, start/stop, live log) | Planned | v1 operator console, three zones only | — |
| Batch queue for processing multiple files | Candidate | Queue up multiple files instead of one-at-a-time | — |
| Speaker diarization via WhisperX | Candidate | Second engine adapter, "who said what" | — |
| Real-time streaming transcription mode | Candidate | Stream partial transcripts instead of batch-only | — |
| Mac Metal acceleration via mlx-whisper | Candidate | Native Apple Silicon acceleration path | — |

---

## Archive

_Nothing archived yet._
