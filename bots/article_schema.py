"""
article_schema.py
블로그 원고의 섹션 헤더 상수와 품질 검증 로직.
writer_bot(프롬프트 생성)과 article_parser(파싱) 양쪽에서 참조한다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# ─── 섹션 헤더 상수 ─────────────────────────────────────

REQUIRED_SECTIONS: tuple[str, ...] = ("TITLE", "BODY")

ALL_SECTIONS: tuple[str, ...] = (
    "TITLE",
    "META",
    "SLUG",
    "TAGS",
    "CORNER",
    "BODY",
    "KEY_POINTS",
    "COUPANG_KEYWORDS",
    "SOURCES",
    "DISCLAIMER",
)

# ─── 기본 품질 기준 (persona.json 없을 때 fallback) ─────

MIN_BODY_LENGTH = 200
MIN_TITLE_LENGTH = 5
MAX_TITLE_LENGTH = 100
MIN_TAGS = 1
MAX_KEY_POINTS = 3

# ─── 내용 품질 검증용 패턴 ──────────────────────────────

_FORBIDDEN_PHRASES_DEFAULT = [
    "오늘은 ~에 대해 알아보겠습니다",
    "~라고 할 수 있습니다",
    "혁명적인",
    "게임 체인저",
    "충격적인",
    "완벽한 가이드",
]


def _load_persona_config() -> dict:
    """config/persona.json 로드. article_schema는 bots 밖 config에 접근."""
    persona_path = Path(__file__).resolve().parents[1] / "config" / "persona.json"
    if not persona_path.exists():
        return {}
    try:
        return json.loads(persona_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ─── 품질 검증 함수 ─────────────────────────────────────

def validate_article(article: dict, corner: str = "") -> list[str]:
    """
    파싱된 article dict의 품질을 검증한다.
    corner를 지정하면 persona.json의 코너별 기준도 적용.
    Returns: 위반 메시지 리스트 (빈 리스트 = 통과)
    """
    issues: list[str] = []
    persona = _load_persona_config()
    corner_cfg = persona.get("corners", {}).get(corner, {})
    voice = persona.get("voice", {})

    # ── 제목 검증 ──
    title = article.get("title", "")
    title_max = persona.get("writing_rules", {}).get("title", {}).get("max_length", MAX_TITLE_LENGTH)
    if len(title) < MIN_TITLE_LENGTH:
        issues.append(f"title이 너무 짧음 ({len(title)}자 < {MIN_TITLE_LENGTH}자)")
    if len(title) > title_max:
        issues.append(f"title이 너무 김 ({len(title)}자 > {title_max}자)")

    # ── 본문 검증 ──
    body = article.get("body", "")
    body_min = corner_cfg.get("body_min_words", MIN_BODY_LENGTH)
    if len(body) < body_min:
        issues.append(f"body가 너무 짧음 ({len(body)}자 < {body_min}자, 코너: {corner or '기본'})")

    h2_min = corner_cfg.get("h2_min_count", 1)
    h2_count = len(re.findall(r"<h2[\s>]", body, re.IGNORECASE))
    if h2_count < h2_min:
        issues.append(f"<h2> 태그 부족 ({h2_count}개 < {h2_min}개)")

    # ── 태그 검증 ──
    tags = article.get("tags", [])
    if len(tags) < MIN_TAGS:
        issues.append(f"tags가 부족 ({len(tags)}개 < {MIN_TAGS}개)")

    # ── key_points 검증 ──
    key_points = article.get("key_points", [])
    if len(key_points) > MAX_KEY_POINTS:
        issues.append(f"key_points가 초과 ({len(key_points)}개 > {MAX_KEY_POINTS}개)")

    # ── 금지 표현 검증 ──
    forbidden = voice.get("forbidden_phrases", _FORBIDDEN_PHRASES_DEFAULT)
    full_text = f"{title} {body}"
    for phrase in forbidden:
        clean = phrase.replace("~", "")
        if clean and clean in full_text:
            issues.append(f"금지 표현 발견: '{phrase}'")

    # ── META 검증 ──
    meta = article.get("meta", "")
    meta_max = persona.get("writing_rules", {}).get("meta_description", {}).get("max_length", 150)
    if meta and len(meta) > meta_max:
        issues.append(f"meta 설명이 너무 김 ({len(meta)}자 > {meta_max}자)")

    # ── 코드 예제 검증 ──
    body_rules = persona.get("writing_rules", {}).get("body", {})
    if body_rules.get("must_include_code_example", False):
        if "<code>" not in body and "<pre>" not in body:
            issues.append("실행 예제 코드(<pre><code>) 없음")

    # ── 수치 근거 검증 ──
    if body_rules.get("must_include_data_evidence", False):
        has_numbers = bool(re.search(r'\d+[,.]?\d*\s*(개|건|명|%|달러|원|GB|MB|초|분|시간|일|주|월|배)', body))
        if not has_numbers:
            issues.append("구체적 수치 근거 없음 (별 수, 비용, 성능 등)")

    return issues
