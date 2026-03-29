from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bots.blog_config import CONFIG_DIR, load_settings


load_settings()

router = APIRouter()
CONFIG_PATH = CONFIG_DIR / "engine.json"
WRITING_OPTIONS = [
    {"value": "openclaw", "label": "OpenClaw"},
    {"value": "claude", "label": "Claude"},
    {"value": "gemini", "label": "Gemini"},
]


class SettingsUpdate(BaseModel):
    writing_provider: str


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


@router.get("/settings")
async def get_settings():
    config = _load_config()
    return {
        "settings": {"writing_provider": config.get("writing", {}).get("provider", "openclaw")},
        "options": {"writing": WRITING_OPTIONS},
    }


@router.put("/settings")
async def update_settings(req: SettingsUpdate):
    if req.writing_provider not in {option["value"] for option in WRITING_OPTIONS}:
        raise HTTPException(status_code=400, detail="Unsupported writing provider")

    config = _load_config() or {}
    writing_cfg = config.setdefault("writing", {})
    writing_cfg["provider"] = req.writing_provider
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "message": "Settings updated"}
