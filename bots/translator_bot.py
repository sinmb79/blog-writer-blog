"""
translator_bot.py
Korean article dict → English article dict
Uses blog-writer agent to rewrite the article in English using the same
---TITLE--- format, then parses the output with article_parser.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_persona_en(corner: str) -> str:
    """Load writing_persona_en for the given corner from persona.json."""
    persona_path = Path(__file__).resolve().parents[1] / "config" / "persona.json"
    try:
        persona = json.loads(persona_path.read_text(encoding="utf-8"))
        return persona.get("corners", {}).get(corner, {}).get("writing_persona_en", "")
    except (json.JSONDecodeError, OSError):
        return ""


def translate_article(article: dict) -> dict:
    """
    Rewrite a Korean article dict in English using the blog-writer agent.
    Returns a new dict with English content; slug gets '-en' suffix.
    Raises RuntimeError on engine failure.
    """
    from bots.engine_loader import EngineLoader, WriterError
    from bots.article_parser import parse_output

    title_ko = article.get('title', '')
    meta_ko = article.get('meta', '')
    corner = article.get('corner', '쉬운세상')
    kp_ko = '\n'.join(f'- {k}' for k in article.get('key_points', []))
    sources = article.get('sources', [])
    source_line = sources[0].get('url', '') if sources else ''
    published_at = article.get('published_at', '')
    slug_base = re.sub(r'-en$', '', article.get('slug', 'article'))

    writing_persona_en = _load_persona_en(corner)
    persona_line = f"\nWriting style: {writing_persona_en}" if writing_persona_en else ""

    system = (
        f"English tech blog writer. No conversation.{persona_line} "
        "Output only the completed article starting from ---TITLE---."
    )

    prompt = f"""Write an English tech blog article about: {title_ko}

Topic summary: {meta_ko}
Key points to cover:
{kp_ko}
Source: {source_line}

Write a full English article (600+ chars, HTML with <h2><p><ul><pre><code>).
Include: code example, data/numbers, community reaction.

---TITLE---
(English title under 60 chars)

---META---
(English meta, under 150 chars)

---SLUG---
{slug_base}-en

---TAGS---
(3-5 English tags)

---CORNER---
{corner}

---BODY---
(Full HTML article)

---KEY_POINTS---
- point 1
- point 2
- point 3

---COUPANG_KEYWORDS---
(2-3 keywords)

---SOURCES---
{source_line} | Source | {published_at}

---DISCLAIMER---

---TITLE---"""

    writer = EngineLoader().get_writer()

    try:
        logger.info(f"영문 재작성 시작: {title_ko}")
        raw = writer.write_with_retry(prompt, system=system).strip()

        if raw and '---TITLE---' not in raw:
            raw = '---TITLE---\n' + raw

        if not raw:
            raise RuntimeError('blog-writer 빈 응답')

        en_article = parse_output(raw)
        if not en_article:
            raise RuntimeError(f'파싱 실패 (앞 200자): {raw[:200]}')

        # Preserve non-content fields from original
        en_article['slug'] = en_article.get('slug') or f"{slug_base}-en"
        en_article['corner'] = corner
        en_article['lang'] = 'en'
        en_article['original_title'] = title_ko
        en_article['topic'] = article.get('topic', '')
        en_article['source'] = article.get('source', '')
        en_article['source_url'] = article.get('source_url', '')
        en_article['published_at'] = article.get('published_at', '')
        en_article['sources'] = sources
        en_article['quality_score'] = article.get('quality_score', 0)

        logger.info(f"영문 재작성 완료: {en_article.get('title', '')}")
        return en_article

    except WriterError as e:
        raise RuntimeError(f"영문 재작성 엔진 오류: {e}") from e
