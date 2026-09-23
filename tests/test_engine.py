import threading

import pytest
from stubs import StubEngine

from engine import (
    TEMPERATURE_FALLBACK,
    EngineManager,
    EngineNotLoadedError,
    FasterWhisperEngine,
    InvalidInputError,
    TranscribeOptions,
    _is_model_cached,
)


def make_manager() -> tuple[EngineManager, StubEngine]:
    engine = StubEngine()
    return EngineManager(engine, "models"), engine


def test_starts_idle():
    manager, _ = make_manager()
    assert manager.is_loaded is False
    assert manager.status()["state"] == "idle"


def test_transcribe_before_load_raises():
    manager, _ = make_manager()
    with pytest.raises(RuntimeError):
        manager.transcribe("a.wav", "a.wav", TranscribeOptions())


def test_load_sets_state_and_forwards_args():
    manager, engine = make_manager()
    status = manager.load("small", "cuda", "int8_float16")
    assert manager.is_loaded is True
    assert status == {
        "state": "loaded",
        "model": "small",
        "device": "cuda",
        "compute_type": "int8_float16",
    }
    assert engine.load_args == ("small", "cuda", "int8_float16", "models")


def test_transcribe_returns_result_and_logs_ok():
    manager, _ = make_manager()
    manager.load("small", "cpu", "int8")
    result = manager.transcribe("clip.wav", "clip.wav", TranscribeOptions(task="translate"))
    assert result.task == "translate"
    assert result.text == "hello world"
    log = manager.log_entries()
    assert len(log) == 1
    assert log[0]["filename"] == "clip.wav"
    assert log[0]["status"] == "ok"
    assert log[0]["model"] == "small"


def test_transcribe_error_is_logged_and_reraised():
    manager, engine = make_manager()
    manager.load("small", "cpu", "int8")
    engine.raise_on_transcribe = True
    with pytest.raises(RuntimeError):
        manager.transcribe("clip.wav", "clip.wav", TranscribeOptions())
    assert manager.log_entries()[0]["status"] == "error"


def test_is_model_cached_detects_hf_layout(tmp_path):
    assert _is_model_cached("large-v3", tmp_path) is False
    (tmp_path / "models--Systran--faster-whisper-large-v3").mkdir()
    assert _is_model_cached("large-v3", tmp_path) is True


def test_is_model_cached_accepts_local_dir(tmp_path):
    local = tmp_path / "my-model"
    local.mkdir()
    assert _is_model_cached(str(local), tmp_path) is True


def test_unload_resets_state():
    manager, _ = make_manager()
    manager.load("small", "cpu", "int8")
    status = manager.unload()
    assert manager.is_loaded is False
    assert status["state"] == "idle"
    assert status["model"] is None


def test_anti_repetition_defaults():
    opts = TranscribeOptions()
    assert opts.vad_filter is True
    assert opts.condition_on_previous_text is False


def test_transcribe_forwards_anti_repetition_options():
    manager, engine = make_manager()
    manager.load("small", "cpu", "int8")
    manager.transcribe(
        "clip.wav",
        "clip.wav",
        TranscribeOptions(vad_filter=False, condition_on_previous_text=True),
    )
    opts = engine.calls[0][1]
    assert opts.vad_filter is False
    assert opts.condition_on_previous_text is True


def test_transcribe_before_load_raises_not_loaded():
    manager, _ = make_manager()
    with pytest.raises(EngineNotLoadedError):
        manager.transcribe("a.wav", "a.wav", TranscribeOptions())


def test_switching_models_releases_the_old_one_first():
    manager, engine = make_manager()
    manager.load("large-v3", "cuda", "int8_float16")
    engine.events.clear()
    manager.load("small", "cuda", "int8_float16")
    assert engine.events == ["unload", "load:small"]
    assert manager.status()["model"] == "small"


def test_failed_load_leaves_clean_idle_state():
    manager, engine = make_manager()
    manager.load("large-v3", "cuda", "int8_float16")
    engine.load_error = RuntimeError("out of memory")
    with pytest.raises(RuntimeError):
        manager.load("medium", "cuda", "int8_float16")
    assert manager.status() == {
        "state": "idle",
        "model": None,
        "device": None,
        "compute_type": None,
    }
    assert engine.loaded is False


def test_load_waits_for_running_transcription():
    manager, engine = make_manager()
    manager.load("small", "cpu", "int8")
    started, release = threading.Event(), threading.Event()
    original = engine.transcribe

    def slow_transcribe(path, options):
        started.set()
        release.wait(timeout=5)
        return original(path, options)

    engine.transcribe = slow_transcribe
    worker = threading.Thread(
        target=manager.transcribe, args=("a.wav", "a.wav", TranscribeOptions())
    )
    worker.start()
    started.wait(timeout=5)
    loader = threading.Thread(target=manager.load, args=("medium", "cpu", "int8"))
    loader.start()
    loader.join(timeout=0.2)
    assert loader.is_alive(), "load must not start while a transcription holds the model"
    # While waiting, status names the incoming model and new work is turned away clearly.
    assert manager.status()["state"] == "loading"
    assert manager.status()["model"] == "medium"
    with pytest.raises(EngineNotLoadedError, match="'medium' is loading"):
        manager.transcribe("b.wav", "b.wav", TranscribeOptions())
    release.set()
    worker.join(timeout=5)
    loader.join(timeout=5)
    assert manager.log_entries()[0]["model"] == "small"
    assert manager.status()["model"] == "medium"


def test_unload_waits_for_running_transcription():
    manager, engine = make_manager()
    manager.load("small", "cpu", "int8")
    started, release = threading.Event(), threading.Event()
    original = engine.transcribe

    def slow_transcribe(path, options):
        started.set()
        release.wait(timeout=5)
        return original(path, options)

    engine.transcribe = slow_transcribe
    worker = threading.Thread(
        target=manager.transcribe, args=("a.wav", "a.wav", TranscribeOptions())
    )
    worker.start()
    started.wait(timeout=5)
    unloader = threading.Thread(target=manager.unload)
    unloader.start()
    unloader.join(timeout=0.2)
    assert unloader.is_alive() and engine.loaded
    release.set()
    worker.join(timeout=5)
    unloader.join(timeout=5)
    assert manager.log_entries()[0]["status"] == "ok"
    assert engine.loaded is False


class _FakeWhisperModel:
    def __init__(self, error: Exception | None = None, iter_error: Exception | None = None) -> None:
        self.kwargs: dict[str, object] = {}
        self.error = error
        self.iter_error = iter_error

    def transcribe(self, audio_path, **kwargs):
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        info = type("Info", (), {"language": "en", "duration": 1.0})()
        return self._segments(), info

    def _segments(self):
        if self.iter_error is not None:
            raise self.iter_error
        yield from ()


def _engine_with(model: _FakeWhisperModel) -> FasterWhisperEngine:
    engine = FasterWhisperEngine()
    engine._model = model  # type: ignore[assignment]
    return engine


def test_temperature_zero_enables_fallback_schedule():
    model = _FakeWhisperModel()
    _engine_with(model).transcribe("a.wav", TranscribeOptions(temperature=0.0))
    assert model.kwargs["temperature"] == TEMPERATURE_FALLBACK


def test_nonzero_temperature_is_passed_through():
    model = _FakeWhisperModel()
    _engine_with(model).transcribe("a.wav", TranscribeOptions(temperature=0.4))
    assert model.kwargs["temperature"] == 0.4


def test_backend_value_errors_become_invalid_input():
    model = _FakeWhisperModel(ValueError("'xx' is not a valid language code"))
    with pytest.raises(InvalidInputError):
        _engine_with(model).transcribe("a.wav", TranscribeOptions(language="xx"))


def test_decode_failure_during_lazy_iteration_is_invalid_input():
    from av.error import InvalidDataError

    model = _FakeWhisperModel(iter_error=InvalidDataError(1094995529, "Invalid data"))
    with pytest.raises(InvalidInputError):
        _engine_with(model).transcribe("a.wav", TranscribeOptions())


def test_unsupported_container_is_invalid_input():
    from av.error import DemuxerNotFoundError

    model = _FakeWhisperModel(DemuxerNotFoundError(-1128613112, "Demuxer not found"))
    with pytest.raises(InvalidInputError):
        _engine_with(model).transcribe("a.xyz", TranscribeOptions())


def test_server_side_ffmpeg_errors_are_not_invalid_input():
    import av.error

    model = _FakeWhisperModel(av.error.FileNotFoundError(2, "No such file", "a.wav"))
    with pytest.raises(Exception) as info:
        _engine_with(model).transcribe("a.wav", TranscribeOptions())
    assert not isinstance(info.value, InvalidInputError)
