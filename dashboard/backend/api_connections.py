from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bots.blog_config import ENV_FILE, TOKEN_FILE, load_settings


load_settings()

router = APIRouter()

SERVICES = {
    "openclaw": {
        "name": "OpenClaw",
        "category": "writing",
        "description": "Local OpenClaw CLI writer",
        "env_key": None,
    },
    "claude": {
        "name": "Claude",
        "category": "writing",
        "description": "Anthropic API key",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "gemini": {
        "name": "Gemini",
        "category": "writing",
        "description": "Google Gemini API key",
        "env_key": "GEMINI_API_KEY",
    },
    "blogger": {
        "name": "Blogger",
        "category": "publishing",
        "description": "Blogger blog id plus Google OAuth token",
        "env_key": "BLOG_MAIN_ID",
    },
}


class ConnectionUpdate(BaseModel):
    api_key: str


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) < 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def _write_env_value(key: str, value: str) -> None:
    lines = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(new_lines).strip() + "\n", encoding="utf-8")
    os.environ[key] = value


def _service_status(service_id: str, meta: dict) -> dict:
    if service_id == "openclaw":
        binary = "openclaw.cmd" if os.name == "nt" else "openclaw"
        connected = shutil.which(binary) is not None
        return {**meta, "id": service_id, "connected": connected, "key_masked": ""}

    env_key = meta["env_key"]
    value = os.getenv(env_key, "")
    connected = bool(value)
    if service_id == "blogger":
        connected = bool(value) and TOKEN_FILE.exists()
    return {**meta, "id": service_id, "connected": connected, "key_masked": _mask(value)}


@router.get("/connections")
async def get_connections():
    return {"connections": [_service_status(service_id, meta) for service_id, meta in SERVICES.items()]}


@router.post("/connections/{service_id}/test")
async def test_connection(service_id: str):
    meta = SERVICES.get(service_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown service")

    if service_id == "openclaw":
        binary = "openclaw.cmd" if os.name == "nt" else "openclaw"
        ok = shutil.which(binary) is not None
        return {"success": ok, "message": "OpenClaw CLI detected" if ok else "OpenClaw CLI not found"}

    if service_id == "blogger":
        has_blog_id = bool(os.getenv("BLOG_MAIN_ID", ""))
        has_token = TOKEN_FILE.exists()
        ok = has_blog_id and has_token
        return {"success": ok, "message": "Blogger is ready" if ok else "BLOG_MAIN_ID or token.json is missing"}

    env_key = meta["env_key"]
    ok = bool(os.getenv(env_key, ""))
    return {"success": ok, "message": f"{env_key} is configured" if ok else f"{env_key} is missing"}


@router.put("/connections/{service_id}")
async def update_connection(service_id: str, req: ConnectionUpdate):
    meta = SERVICES.get(service_id)
    if not meta or service_id == "openclaw":
        raise HTTPException(status_code=400, detail="This connection cannot be updated here")

    value = req.api_key.strip()
    if not value:
        raise HTTPException(status_code=400, detail="A value is required")

    _write_env_value(meta["env_key"], value)
    return {"success": True, "message": f"{meta['env_key']} updated"}
