"""Shared test doubles."""

from engine import Segment, TranscribeOptions, TranscriptionEngine, TranscriptionResult


class StubEngine(TranscriptionEngine):
    """In-memory engine that records calls and never touches faster-whisper."""

    def __init__(self) -> None:
        self.loaded = False
        self.load_args: tuple[str, str, str, str] | None = None
        self.calls: list[tuple[str, TranscribeOptions]] = []
        self.raise_on_transcribe = False

    def load(self, model: str, device: str, compute_type: str, download_root: str) -> None:
        self.loaded = True
        self.load_args = (model, device, compute_type, download_root)

    def unload(self) -> None:
        self.loaded = False

    def transcribe(self, audio_path: str, options: TranscribeOptions) -> TranscriptionResult:
        self.calls.append((audio_path, options))
        if self.raise_on_transcribe:
            raise RuntimeError("boom")
        return TranscriptionResult(
            task=options.task,
            language="en",
            duration=1.0,
            text="hello world",
            segments=[Segment(0, 0.0, 1.0, "hello world", None)],
        )
