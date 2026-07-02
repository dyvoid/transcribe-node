"""Transcription engine: a stable interface, a faster-whisper adapter, and the
engine-state manager that the API and UI drive.

The interface is a real seam: faster-whisper is the only adapter in v1, but a
WhisperX adapter (for diarization) is anticipated and slots in without structural
change.
"""

import os
import sys
import sysconfig
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


def _register_cuda_dll_dirs() -> None:
    """Put the pip-installed NVIDIA CUDA DLLs on Windows' loader search path.

    The nvidia-cublas-cu12 / nvidia-cudnn-cu12 wheels drop their DLLs under
    site-packages/nvidia/*/bin, but ctranslate2 (via faster-whisper) can't find
    them there unless the directories are registered explicitly.
    """
    if sys.platform != "win32":
        return
    nvidia_root = Path(sysconfig.get_paths()["purelib"]) / "nvidia"
    for bin_dir in nvidia_root.glob("*/bin"):
        os.add_dll_directory(str(bin_dir))


def _is_model_cached(model: str, download_root: Path) -> bool:
    """Heuristic: is this model already present under the cache directory?

    faster-whisper downloads via huggingface_hub, which lays models out as
    ``models--<org>--faster-whisper-<name>``. A local path or an already-cached
    directory counts as present. This is advisory only (see ADR 0006): a partial
    or corrupt cache is misreported as present, but faster-whisper still errors
    on genuine failure.
    """
    if Path(model).is_dir():
        return True
    token = model.replace("/", "--")
    return any(token in entry.name for entry in download_root.glob("*") if entry.is_dir())


@dataclass
class Word:
    word: str
    start: float
    end: float


@dataclass
class Segment:
    id: int
    start: float
    end: float
    text: str
    words: list[Word] | None = None


@dataclass
class TranscriptionResult:
    task: str
    language: str
    duration: float
    text: str
    segments: list[Segment]


@dataclass
class TranscribeOptions:
    task: str = "transcribe"  # "transcribe" | "translate"
    language: str | None = None
    prompt: str | None = None
    temperature: float = 0.0
    word_timestamps: bool = False
    # Anti-repetition defaults: Whisper's repetition/hallucination loops are
    # triggered by trailing silence and by feeding bad segments back as context.
    # VAD strips silence before transcription; disabling previous-text conditioning
    # breaks the feedback loop. See openai/whisper#679 and faster-whisper#465.
    vad_filter: bool = True
    condition_on_previous_text: bool = False


@dataclass
class LogEntry:
    timestamp: str
    filename: str
    model: str
    processing_seconds: float
    status: str


class TranscriptionEngine(ABC):
    """Backend-agnostic transcription interface."""

    @abstractmethod
    def load(self, model: str, device: str, compute_type: str, download_root: str) -> None: ...

    @abstractmethod
    def unload(self) -> None: ...

    @abstractmethod
    def transcribe(self, audio_path: str, options: TranscribeOptions) -> TranscriptionResult: ...


class FasterWhisperEngine(TranscriptionEngine):
    """faster-whisper adapter. Imports the backend lazily so unrelated modules
    (and tests) don't pay the import cost."""

    def __init__(self) -> None:
        self._model = None

    def load(self, model: str, device: str, compute_type: str, download_root: str) -> None:
        if device == "cuda":
            _register_cuda_dll_dirs()
        from faster_whisper import WhisperModel

        root = Path(download_root)
        root.mkdir(parents=True, exist_ok=True)
        if not _is_model_cached(model, root):
            print(
                f"[engine] downloading model '{model}' (first use, may take a while)...",
                flush=True,
            )
        self._model = WhisperModel(
            model,
            device=device,
            compute_type=compute_type,
            download_root=download_root,
        )
        print(f"[engine] model '{model}' ready.", flush=True)

    def unload(self) -> None:
        self._model = None

    def transcribe(self, audio_path: str, options: TranscribeOptions) -> TranscriptionResult:
        if self._model is None:
            raise RuntimeError("Engine has no model loaded.")

        segments_gen, info = self._model.transcribe(
            audio_path,
            task=options.task,
            language=options.language,
            initial_prompt=options.prompt,
            temperature=options.temperature,
            word_timestamps=options.word_timestamps,
            vad_filter=options.vad_filter,
            condition_on_previous_text=options.condition_on_previous_text,
        )

        segments: list[Segment] = []
        texts: list[str] = []
        for index, seg in enumerate(segments_gen):
            words = None
            if options.word_timestamps and seg.words:
                words = [
                    Word(w.word, round(float(w.start), 2), round(float(w.end), 2))
                    for w in seg.words
                ]
            segments.append(
                Segment(
                    index, round(float(seg.start), 2), round(float(seg.end), 2), seg.text, words
                )
            )
            texts.append(seg.text)

        return TranscriptionResult(
            task=options.task,
            language=info.language,
            duration=round(float(info.duration), 2),
            text="".join(texts).strip(),
            segments=segments,
        )


class EngineManager:
    """Owns engine state (which model is loaded, whether work is accepted) and a
    rolling request log. Serializes inference; only one model is loaded at a time.
    """

    def __init__(self, engine: TranscriptionEngine, download_root: str) -> None:
        self._engine = engine
        self._download_root = download_root
        self._state = "idle"  # "idle" | "loading" | "loaded"
        self._model: str | None = None
        self._device: str | None = None
        self._compute_type: str | None = None
        self._state_lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._log: deque[LogEntry] = deque(maxlen=200)

    def status(self) -> dict[str, object]:
        return {
            "state": self._state,
            "model": self._model,
            "device": self._device,
            "compute_type": self._compute_type,
        }

    def load(self, model: str, device: str, compute_type: str) -> dict[str, object]:
        with self._state_lock:
            self._state = "loading"
            try:
                self._engine.load(model, device, compute_type, self._download_root)
            except Exception:
                self._state = "idle"
                self._model = None
                raise
            self._model = model
            self._device = device
            self._compute_type = compute_type
            self._state = "loaded"
        return self.status()

    def unload(self) -> dict[str, object]:
        with self._state_lock:
            self._engine.unload()
            self._state = "idle"
            self._model = None
            self._device = None
            self._compute_type = None
        return self.status()

    @property
    def is_loaded(self) -> bool:
        return self._state == "loaded"

    def transcribe(
        self, audio_path: str, filename: str, options: TranscribeOptions
    ) -> TranscriptionResult:
        if not self.is_loaded:
            raise RuntimeError("No model loaded. Load a model before transcribing.")

        started = time.perf_counter()
        with self._infer_lock:
            try:
                result = self._engine.transcribe(audio_path, options)
            except Exception:
                self._record(filename, time.perf_counter() - started, "error")
                raise
        self._record(filename, time.perf_counter() - started, "ok")
        return result

    def log_entries(self) -> list[dict[str, object]]:
        return [entry.__dict__ for entry in self._log]

    def _record(self, filename: str, seconds: float, status: str) -> None:
        self._log.appendleft(
            LogEntry(
                timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
                filename=filename,
                model=self._model or "-",
                processing_seconds=round(seconds, 2),
                status=status,
            )
        )
