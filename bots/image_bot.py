"""
Image helper utilities for unattended publishing flows.

This file intentionally stays small in `blog-writer-blog` and only exposes the
OpenAI image generation path needed by the Naver publisher fallback logic.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
LOG_DIR = BASE_DIR / "logs"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / "image_bot.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)


def _safe_name(topic: str) -> str:
    safe_name = re.sub(r"[^\w가-힣-]+", "_", topic).strip("_")
    return safe_name[:50] or "generated-image"


def generate_image_auto(prompt: str, topic: str) -> str | None:
    """Generate one image with OpenAI Images API and save it locally."""
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is missing; cannot generate image automatically.")
        return None

    try:
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-image-1",
                "prompt": prompt,
                "size": "1024x1024",
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        image_b64 = data["data"][0].get("b64_json")
        image_url = data["data"][0].get("url")

        if image_b64:
            import base64

            image_bytes = base64.b64decode(image_b64)
        elif image_url:
            image_bytes = requests.get(image_url, timeout=60).content
        else:
            logger.error("OpenAI image response did not include image data.")
            return None

        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_safe_name(topic)}.png"
        save_path = IMAGES_DIR / filename
        save_path.write_bytes(image_bytes)
        logger.info("Saved generated image to %s", save_path)
        return str(save_path)
    except Exception as exc:
        logger.error("OpenAI image generation failed: %s", exc)
        return None


__all__ = ["generate_image_auto"]
