from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
TOKEN_FILE = PROJECT_ROOT / "token.json"

DATA_FOLDERS = (
    "topics",
    "collected",
    "originals",
    "pending_review",
    "published",
    "discarded",
    "scenarios",
)


def ensure_runtime_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    for folder in DATA_FOLDERS:
        (DATA_DIR / folder).mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    ensure_runtime_dirs()
    load_dotenv(ENV_FILE)
    return {
        "project_root": PROJECT_ROOT,
        "env_file": str(ENV_FILE),
        "config_dir": CONFIG_DIR,
        "data_dir": DATA_DIR,
        "log_dir": LOG_DIR,
        "token_file": TOKEN_FILE,
    }


def load_json(path: Path, default: dict | list | None = None):
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {} if default is None else default


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
