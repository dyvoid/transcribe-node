import pytest
from fastapi.testclient import TestClient
from stubs import StubEngine

import main
from engine import EngineManager


@pytest.fixture
def client():
    # Swap in a stub-backed manager so endpoints work without a real model.
    main.manager = EngineManager(StubEngine(), "models")
    return TestClient(main.app)


def _upload():
    return {"file": ("clip.wav", b"fake-bytes", "audio/wav")}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_system_shape(client):
    body = client.get("/system").json()
    for key in ("device", "compute_type", "available_memory_gb", "recommended_model"):
        assert key in body


def test_models_lists_catalog(client):
    data = client.get("/v1/models").json()["data"]
    assert {m["id"] for m in data} >= {"large-v3", "small"}


def test_transcribe_requires_loaded_model(client):
    res = client.post("/v1/audio/transcriptions", files=_upload())
    assert res.status_code == 409


def test_load_then_transcribe_json(client):
    assert client.post("/engine/load", json={"model": "small"}).json()["state"] == "loaded"
    res = client.post("/v1/audio/transcriptions", files=_upload())
    assert res.json() == {"text": "hello world"}


def test_response_format_text(client):
    client.post("/engine/load", json={"model": "small"})
    res = client.post("/v1/audio/transcriptions", files=_upload(), data={"response_format": "text"})
    assert res.text == "hello world"


def test_response_format_srt(client):
    client.post("/engine/load", json={"model": "small"})
    res = client.post("/v1/audio/transcriptions", files=_upload(), data={"response_format": "srt"})
    assert "00:00:00,000 --> 00:00:01,000" in res.text
    assert "hello world" in res.text


def test_verbose_json_has_segments(client):
    client.post("/engine/load", json={"model": "small"})
    res = client.post(
        "/v1/audio/transcriptions", files=_upload(), data={"response_format": "verbose_json"}
    )
    body = res.json()
    assert body["language"] == "en"
    assert body["segments"][0]["text"] == "hello world"


def test_bad_response_format_rejected(client):
    client.post("/engine/load", json={"model": "small"})
    res = client.post("/v1/audio/transcriptions", files=_upload(), data={"response_format": "yaml"})
    assert res.status_code == 400


def test_translations_use_translate_task(client):
    client.post("/engine/load", json={"model": "small"})
    res = client.post(
        "/v1/audio/translations", files=_upload(), data={"response_format": "verbose_json"}
    )
    assert res.json()["task"] == "translate"


def test_log_records_request(client):
    client.post("/engine/load", json={"model": "small"})
    client.post("/v1/audio/transcriptions", files=_upload())
    entries = client.get("/engine/log").json()["entries"]
    assert entries[0]["filename"] == "clip.wav"
    assert entries[0]["status"] == "ok"


def test_anti_repetition_defaults_applied(client):
    main.manager = EngineManager(StubEngine(), "models")
    client.post("/engine/load", json={"model": "small"})
    client.post("/v1/audio/transcriptions", files=_upload())
    opts = main.manager._engine.calls[0][1]
    assert opts.vad_filter is True
    assert opts.condition_on_previous_text is False


def test_anti_repetition_can_be_overridden(client):
    main.manager = EngineManager(StubEngine(), "models")
    client.post("/engine/load", json={"model": "small"})
    client.post(
        "/v1/audio/transcriptions",
        files=_upload(),
        data={"vad_filter": "false", "condition_on_previous_text": "true"},
    )
    opts = main.manager._engine.calls[0][1]
    assert opts.vad_filter is False
    assert opts.condition_on_previous_text is True


def _loaded_client_engine(client) -> StubEngine:
    client.post("/engine/load", json={"model": "small"})
    engine = main.manager._engine
    assert isinstance(engine, StubEngine)
    return engine


def test_word_granularity_plain_field(client):
    engine = _loaded_client_engine(client)
    client.post(
        "/v1/audio/transcriptions", files=_upload(), data={"timestamp_granularities": "word"}
    )
    assert engine.calls[0][1].word_timestamps is True


def test_word_granularity_openai_sdk_bracket_field(client):
    # The OpenAI Python SDK serializes arrays in multipart as `name[]`.
    engine = _loaded_client_engine(client)
    client.post(
        "/v1/audio/transcriptions",
        files=_upload(),
        data={"timestamp_granularities[]": ["word", "segment"]},
    )
    assert engine.calls[0][1].word_timestamps is True


def test_invalid_input_maps_to_400(client):
    engine = _loaded_client_engine(client)
    engine.transcribe_error = ValueError("'xx' is not a valid language code")
    res = client.post("/v1/audio/transcriptions", files=_upload(), data={"language": "xx"})
    assert res.status_code == 400
    assert "not a valid language code" in res.json()["detail"]


def test_engine_failure_maps_to_json_500(client):
    engine = _loaded_client_engine(client)
    engine.raise_on_transcribe = True
    res = client.post("/v1/audio/transcriptions", files=_upload())
    assert res.status_code == 500
    assert res.json()["detail"] == "Transcription failed: boom"


def test_upload_reaches_engine_intact(client):
    engine = _loaded_client_engine(client)
    seen: list[bytes] = []
    original = engine.transcribe

    def capture(path, options):
        with open(path, "rb") as f:
            seen.append(f.read())
        return original(path, options)

    engine.transcribe = capture
    client.post("/v1/audio/transcriptions", files=_upload())
    assert seen == [b"fake-bytes"]


def test_unload_endpoint(client):
    _loaded_client_engine(client)
    assert client.post("/engine/unload").json()["state"] == "idle"


def test_static_dir_is_project_relative():
    from config import ROOT

    assert main.STATIC_DIR == ROOT / "static"
