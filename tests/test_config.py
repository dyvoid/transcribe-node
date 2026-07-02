from config import load_config


def test_defaults_from_pyproject():
    cfg = load_config()
    assert cfg.default_model == "large-v3"
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9000
    assert cfg.models_dir.name == "models"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("TRANSCRIBENODE_MODEL", "medium")
    monkeypatch.setenv("TRANSCRIBENODE_PORT", "8123")
    monkeypatch.setenv("TRANSCRIBENODE_HOST", "0.0.0.0")
    cfg = load_config()
    assert cfg.default_model == "medium"
    assert cfg.port == 8123
    assert cfg.host == "0.0.0.0"


def test_models_dir_relative_is_under_root(monkeypatch):
    monkeypatch.setenv("TRANSCRIBENODE_MODELS_DIR", "cache/models")
    cfg = load_config()
    assert cfg.models_dir.is_absolute()
    assert cfg.models_dir.name == "models"


def test_models_dir_absolute_is_used_as_is(monkeypatch, tmp_path):
    monkeypatch.setenv("TRANSCRIBENODE_MODELS_DIR", str(tmp_path))
    cfg = load_config()
    assert cfg.models_dir == tmp_path


def test_env_file_with_utf8_bom_is_parsed(monkeypatch, tmp_path):
    # Some Windows editors save .env as UTF-8-with-BOM. The BOM must not corrupt
    # the first key (TRANSCRIBENODE_PORT here).
    monkeypatch.delenv("TRANSCRIBENODE_PORT", raising=False)
    monkeypatch.setattr("config.ROOT", tmp_path)
    (tmp_path / ".env").write_bytes(b"\xef\xbb\xbfTRANSCRIBENODE_PORT=8137\n")
    cfg = load_config()
    assert cfg.port == 8137
