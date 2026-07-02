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
