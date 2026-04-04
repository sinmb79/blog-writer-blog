"""
Naver Blog publisher for unattended automation.

This module uses a persistent Chrome profile so the account can be logged in
once manually and then reused for later automated publishing runs.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from bots import image_bot, publisher_bot


load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
LOG_DIR = BASE_DIR / "logs"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / "naver_publisher.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

NAVER_BLOG_ENABLED = os.getenv("NAVER_BLOG_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
NAVER_BLOG_URL = os.getenv("NAVER_BLOG_URL", "").rstrip("/")
NAVER_BLOG_NEW_POST_URL = os.getenv("NAVER_BLOG_NEW_POST_URL", "").strip()
NAVER_CHROME_PROFILE_DIR = os.getenv("NAVER_CHROME_PROFILE_DIR", "").strip()
NAVER_PUBLISH_RETRY_COUNT = int(os.getenv("NAVER_PUBLISH_RETRY_COUNT", "3"))

BANANAPRO_API_URL = os.getenv("BANANAPRO_API_URL", "").strip()
BANANAPRO_API_KEY = os.getenv("BANANAPRO_API_KEY", "").strip()
BANANAPRO_MODEL = os.getenv("BANANAPRO_MODEL", "banana-pro-image").strip()

send_telegram = publisher_bot.send_telegram
_sleep = time.sleep


def _ensure_credentials() -> bool:
    if not NAVER_BLOG_ENABLED:
        logger.error("NAVER_BLOG_ENABLED is false. Naver publishing is disabled.")
        return False
    required = {
        "NAVER_BLOG_URL": NAVER_BLOG_URL,
        "NAVER_BLOG_NEW_POST_URL": NAVER_BLOG_NEW_POST_URL,
        "NAVER_CHROME_PROFILE_DIR": NAVER_CHROME_PROFILE_DIR,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        logger.error("Missing Naver settings: %s", ", ".join(missing))
        return False
    return True


def _build_image_prompt(article: dict[str, Any]) -> str:
    prompt_parts = [
        article.get("title", ""),
        article.get("meta", ""),
        article.get("corner", ""),
    ]
    prompt = " ".join(part.strip() for part in prompt_parts if part and str(part).strip())
    return prompt or "Korean blog cover image"


def _save_image_bytes(image_bytes: bytes, stem: str) -> str:
    safe_stem = "".join(ch if ch.isalnum() else "-" for ch in stem.lower()).strip("-") or "naver-cover"
    path = IMAGES_DIR / f"{safe_stem[:60]}.png"
    path.write_bytes(image_bytes)
    return str(path)


def _generate_bananapro_image(article: dict[str, Any]) -> str | None:
    if not (BANANAPRO_API_KEY and BANANAPRO_API_URL):
        return None

    payload = {
        "model": BANANAPRO_MODEL,
        "prompt": _build_image_prompt(article),
        "size": "1024x1024",
    }
    headers = {
        "Authorization": f"Bearer {BANANAPRO_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(BANANAPRO_API_URL, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()

    image_url = data.get("image_url") or data.get("url")
    image_b64 = data.get("image_base64")
    if image_url:
        image_bytes = requests.get(image_url, timeout=60).content
        return _save_image_bytes(image_bytes, article.get("title", "naver-cover"))
    if image_b64:
        return _save_image_bytes(base64.b64decode(image_b64), article.get("title", "naver-cover"))
    return None


def _generate_openai_image(article: dict[str, Any]) -> str | None:
    prompt = _build_image_prompt(article)
    return image_bot.generate_image_auto(prompt, article.get("title", "naver-cover"))


def _resolve_representative_image(article: dict[str, Any]) -> str | None:
    for key in ("featured_image_path", "image_path"):
        value = article.get(key)
        if value and Path(value).exists():
            return str(value)

    generated = _generate_bananapro_image(article)
    if generated:
        return generated

    return _generate_openai_image(article)


def _require_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Playwright is required for Naver publishing. Install it and run 'playwright install chromium'."
        ) from exc
    return sync_playwright


def _open_persistent_page():
    sync_playwright = _require_playwright()
    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=NAVER_CHROME_PROFILE_DIR,
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    return playwright, context, page


def _is_logged_in(page) -> bool:
    page.goto(NAVER_BLOG_URL, wait_until="domcontentloaded")
    current_url = page.url.lower()
    return "nidlogin" not in current_url and "login" not in current_url


def _dismiss_optional_popups(page) -> None:
    for label in ("Later", "Close", "Dismiss", "Cancel", "Not now", "닫기", "취소", "나중에"):
        try:
            page.get_by_role("button", name=label).click(timeout=1000)
        except Exception:
            continue


def _open_editor(page) -> None:
    page.goto(NAVER_BLOG_NEW_POST_URL, wait_until="domcontentloaded")
    _dismiss_optional_popups(page)


def _upload_top_image(page, image_path: str) -> None:
    file_inputs = page.locator("input[type='file']")
    if file_inputs.count():
        file_inputs.first.set_input_files(image_path)
        return

    for label in ("사진", "이미지", "Photo", "Image"):
        try:
            page.get_by_role("button", name=label).click(timeout=1500)
            file_inputs = page.locator("input[type='file']")
            if file_inputs.count():
                file_inputs.first.set_input_files(image_path)
                return
        except Exception:
            continue

    raise RuntimeError("Could not find a file input for the Naver editor image upload.")


def _html_to_editor_text(article: dict[str, Any]) -> str:
    html = article.get("_html_content")
    if not html:
        body_html, toc_html = publisher_bot.prepare_body_html(article)
        html = publisher_bot.build_full_html(article, body_html, toc_html)

    soup = BeautifulSoup(html, "html.parser")
    blocks = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(" ", strip=True)
        if text:
            blocks.append(text)
    return "\n\n".join(blocks)


def _fill_title(page, title: str) -> None:
    selectors = [
        "textarea",
        "input[placeholder*='제목']",
        "div[contenteditable='true']",
    ]
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count():
            locator.first.click()
            locator.first.fill("")
            locator.first.type(title)
            return
    raise RuntimeError("Could not find a title field in the Naver editor.")


def _fill_body(page, body_text: str) -> None:
    locator = page.locator("div[contenteditable='true']")
    if not locator.count():
        raise RuntimeError("Could not find a body editor in the Naver editor.")

    target = locator.last
    target.click()
    page.keyboard.type(body_text)


def _publish_and_get_url(page) -> str:
    for label in ("Publish", "발행", "게시"):
        try:
            page.get_by_role("button", name=label).click(timeout=2000)
            break
        except Exception:
            continue

    _dismiss_optional_popups(page)
    page.wait_for_load_state("networkidle", timeout=20000)
    current_url = page.url
    if not current_url or "postwrite" in current_url.lower():
        raise RuntimeError("Naver publish did not navigate to a published post URL.")
    return current_url


def _publish_once(article: dict[str, Any]) -> str:
    image_path = _resolve_representative_image(article)
    if not image_path:
        raise RuntimeError("Representative image could not be prepared.")

    playwright = context = None
    try:
        playwright, context, page = _open_persistent_page()
        if not _is_logged_in(page):
            raise RuntimeError("Naver login is required for the saved profile.")
        _open_editor(page)
        _upload_top_image(page, image_path)
        _fill_title(page, article.get("title", ""))
        _fill_body(page, _html_to_editor_text(article))
        return _publish_and_get_url(page)
    finally:
        if context is not None:
            context.close()
        if playwright is not None:
            playwright.stop()


def publish(article: dict[str, Any]) -> bool:
    logger.info("Naver publish attempt: %s", article.get("title", ""))

    if not _ensure_credentials():
        return False

    safety_cfg = publisher_bot.load_config("safety_keywords.json")
    needs_review, review_reason = publisher_bot.check_safety(article, safety_cfg)
    if needs_review:
        logger.warning("Pending manual review for Naver publish: %s", review_reason)
        publisher_bot.save_pending_review(article, review_reason)
        publisher_bot.send_pending_review_alert(article, review_reason)
        return False

    last_error = None
    for attempt in range(1, max(NAVER_PUBLISH_RETRY_COUNT, 1) + 1):
        try:
            post_url = _publish_once(article)
            publisher_bot.log_published(
                article,
                {
                    "id": post_url.rstrip("/").split("/")[-1],
                    "url": post_url,
                },
            )
            send_telegram(
                f"📝 <b>Naver published</b>\n\n"
                f"📌 <b>{article.get('title', '')}</b>\n"
                f"URL: {post_url}"
            )
            logger.info("Naver publish complete: %s", post_url)
            return True
        except Exception as exc:
            last_error = exc
            logger.warning("Naver publish attempt %s/%s failed: %s", attempt, NAVER_PUBLISH_RETRY_COUNT, exc)
            if attempt < NAVER_PUBLISH_RETRY_COUNT:
                _sleep(attempt)

    send_telegram(f"Naver publish failed: {article.get('title', '')}\nReason: {last_error}")
    logger.error("Naver publish failed after retries: %s", last_error)
    return False


__all__ = ["publish"]
