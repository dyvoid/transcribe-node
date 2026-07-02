import pytest
from stubs import StubEngine

from engine import EngineManager, TranscribeOptions


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


def test_unload_resets_state():
    manager, _ = make_manager()
    manager.load("small", "cpu", "int8")
    status = manager.unload()
    assert manager.is_loaded is False
    assert status["state"] == "idle"
    assert status["model"] is None
