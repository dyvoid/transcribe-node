"""Runtime configuration.

Resolution order for each setting (highest priority first):
1. A real environment variable
2. A value in a local `.env` file (see `.env.example`)
3. The `[tool.transcribenode]` table in `pyproject.toml`
4. A built-in default
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    default_model: str
    host: str
    port: int
    models_dir: Path


def _resolve_models_dir(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_config() -> Config:
    # Load .env without overriding real environment variables (env wins).
    # utf-8-sig transparently strips a UTF-8 BOM if present; some Windows editors
    # save .env with a BOM, which would otherwise corrupt the first key.
    load_dotenv(ROOT / ".env", encoding="utf-8-sig")

    data: dict[str, object] = {}
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            data = tomllib.load(f).get("tool", {}).get("transcribenode", {})

    default_model = os.getenv("TRANSCRIBENODE_MODEL", str(data.get("default-model", "large-v3")))
    host = os.getenv("TRANSCRIBENODE_HOST", str(data.get("host", "127.0.0.1")))
    port = int(os.getenv("TRANSCRIBENODE_PORT", str(data.get("port", 9000))))
    models_dir = _resolve_models_dir(
        os.getenv("TRANSCRIBENODE_MODELS_DIR", str(data.get("models-dir", "models")))
    )

    return Config(default_model=default_model, host=host, port=port, models_dir=models_dir)
