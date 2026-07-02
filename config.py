"""Runtime configuration, sourced from pyproject.toml with environment overrides."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    default_model: str
    host: str
    port: int
    models_dir: Path


def load_config() -> Config:
    data: dict[str, object] = {}
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            data = tomllib.load(f).get("tool", {}).get("transcribenode", {})

    default_model = os.getenv("TRANSCRIBENODE_MODEL", str(data.get("default-model", "large-v3")))
    host = os.getenv("TRANSCRIBENODE_HOST", str(data.get("host", "127.0.0.1")))
    port = int(os.getenv("TRANSCRIBENODE_PORT", str(data.get("port", 9000))))
    models_dir = ROOT / str(data.get("models-dir", "models"))

    return Config(default_model=default_model, host=host, port=port, models_dir=models_dir)
