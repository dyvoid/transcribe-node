"""Transcription engine: a stable interface, a faster-whisper adapter, and the
engine-state manager that the API and UI drive.

The interface is a real seam: faster-whisper is the only adapter in v1, but a
WhisperX adapter (for diarization) is anticipated and slots in without structural
change.
"""

import contextlib
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


# faster-whisper's default fallback schedule. OpenAI documents temperature=0 as "start greedy and
# raise the temperature when a segment fails the log-prob/compression checks"; a bare 0.0 would
# disable that retry, which is Whisper's main guard against repetition loops.
TEMPERATURE_FALLBACK = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


class EngineNotLoadedError(RuntimeError):
    """Raised when work is requested but no model is loaded (or one is being switched in)."""


class InvalidInputError(ValueError):
    """The backend rejected the request's audio or parameters (undecodable file, bad language)."""


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
            raise EngineNotLoadedError("Engine has no model loaded.")
        from av.error import DecoderNotFoundError, DemuxerNotFoundError

        temperature = TEMPERATURE_FALLBACK if options.temperature == 0 else options.temperature
        try:
            segments_gen, info = self._model.transcribe(
                audio_path,
                task=options.task,
                language=options.language,
                initial_prompt=options.prompt,
                temperature=temperature,
                word_timestamps=options.word_timestamps,
                vad_filter=options.vad_filter,
                condition_on_previous_text=options.condition_on_previous_text,
            )
            # Segments are produced lazily, so decoding can still fail while iterating.
            return self._collect(segments_gen, info, options)
        # Client-side faults only: undecodable data (av's InvalidDataError is a ValueError), an
        # unsupported container/codec, or a rejected parameter such as an unknown language code.
        # Other FFmpeg errors (out of memory, missing temp file) stay server errors.
        except (ValueError, DecoderNotFoundError, DemuxerNotFoundError) as exc:
            raise InvalidInputError(str(exc)) from exc

    @staticmethod
    def _collect(segments_gen, info, options: TranscribeOptions) -> TranscriptionResult:
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
        # (model, device, compute_type) being switched in. Kept apart from the fields above, which
        # only change under the infer lock, so a running job always sees the model it runs on.
        self._pending: tuple[str, str, str] | None = None
        self._state_lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._log: deque[LogEntry] = deque(maxlen=200)

    def status(self) -> dict[str, object]:
        pending = self._pending
        fields: tuple[str | None, str | None, str | None] = (
            pending
            if self._state == "loading" and pending is not None
            else (self._model, self._device, self._compute_type)
        )
        model, device, compute_type = fields
        return {
            "state": self._state,
            "model": model,
            "device": device,
            "compute_type": compute_type,
        }

    def load(self, model: str, device: str, compute_type: str) -> dict[str, object]:
        # Lock order is always state -> infer. Holding the infer lock waits out any running
        # transcription, and releasing the current model first means two models never share memory.
        with self._state_lock:
            self._pending = (model, device, compute_type)  # set before state; readers check state
            self._state = "loading"
            with self._infer_lock:
                try:
                    self._engine.unload()
                    self._engine.load(model, device, compute_type, self._download_root)
                except BaseException:
                    # Whatever failed, end in a clean idle state; a stuck "loading" would lock the
                    # operator out (the UI disables Start/Stop while loading).
                    with contextlib.suppress(Exception):
                        self._engine.unload()
                    self._clear()
                    raise
                self._model, self._device, self._compute_type = model, device, compute_type
                self._pending = None
                self._state = "loaded"
        return self.status()

    def unload(self) -> dict[str, object]:
        with self._state_lock, self._infer_lock:
            try:
                self._engine.unload()
            finally:
                self._clear()
        return self.status()

    def _clear(self) -> None:
        self._state = "idle"
        self._pending = None
        self._model = None
        self._device = None
        self._compute_type = None

    @property
    def is_loaded(self) -> bool:
        return self._state == "loaded"

    def transcribe(
        self, audio_path: str, filename: str, options: TranscribeOptions
    ) -> TranscriptionResult:
        self.ensure_loaded()
        started = time.perf_counter()
        with self._infer_lock:
            # Re-check under the lock: an unload or model switch may have run while this waited.
            self.ensure_loaded()
            model = self._model or "-"  # captured now; a pending switch rewrites self._model
            try:
                result = self._engine.transcribe(audio_path, options)
            except Exception:
                self._record(filename, model, time.perf_counter() - started, "error")
                raise
        self._record(filename, model, time.perf_counter() - started, "ok")
        return result

    def ensure_loaded(self) -> None:
        if self._state == "loading":
            pending = self._pending  # read once: a finishing load() may reset it concurrently
            incoming = pending[0] if pending else "unknown"
            raise EngineNotLoadedError(
                f"Model '{incoming}' is loading. Retry once the engine reports loaded."
            )
        if not self.is_loaded:
            raise EngineNotLoadedError("No model loaded. Load a model before transcribing.")

    def log_entries(self) -> list[dict[str, object]]:
        return [entry.__dict__ for entry in self._log]

    def _record(self, filename: str, model: str, seconds: float, status: str) -> None:
        self._log.appendleft(
            LogEntry(
                timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
                filename=filename,
                model=model,
                processing_seconds=round(seconds, 2),
                status=status,
            )
        )
