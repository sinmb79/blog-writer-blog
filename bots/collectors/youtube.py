"""YouTube 트렌딩 수집기

우선순위:
1. YouTube Data API v3 (YOUTUBE_API_KEY 환경변수 필요)
2. API 키 없으면 빈 리스트 반환 (경고 로그)

YouTube 트렌딩 HTML 스크래핑은 2024년 이후 로그인 장벽으로 차단됨.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

TRENDING_API = "https://www.googleapis.com/youtube/v3/videos"

REGION_LANG = {"KR": "ko", "US": "en"}
MAX_ITEMS = 15


def _parse_compact_number(text: str) -> int:
    """'1.2M', '34K' 등 → int"""
    if not text:
        return 0
    text = text.strip().replace(",", "")
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if text.upper().endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _fetch_trending_api(api_key: str, region: str) -> list[dict]:
    """YouTube Data API v3 — chart=mostPopular"""
    params = urllib.parse.urlencode({
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region.upper(),
        "hl": REGION_LANG.get(region.upper(), "en"),
        "maxResults": MAX_ITEMS,
        "key": api_key,
    })
    url = f"{TRENDING_API}?{params}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "blog-writer-bot/0.1"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))

    items = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        video_id = item.get("id", "")
        title = snippet.get("title", "").strip()
        if not title or not video_id:
            continue
        views = int(stats.get("viewCount", 0) or 0)
        channel = snippet.get("channelTitle", "")
        pub_at = snippet.get("publishedAt", datetime.now(timezone.utc).isoformat())
        items.append({
            "topic": title,
            "description": snippet.get("description", "")[:400] or f"YouTube 트렌딩: {title}",
            "source": "youtube",
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "published_at": pub_at,
            "search_demand_score": 18,
            "topic_type": "trending",
            "extra": {
                "channel": channel,
                "views": views,
                "region": region.upper(),
            },
        })
    return items


def collect(regions: list[str] | None = None) -> list[dict]:
    """YouTube 트렌딩 수집. 기본: KR + US

    YOUTUBE_API_KEY 환경변수가 설정된 경우에만 동작.
    미설정 시 빈 리스트 반환 (다른 수집기로 대체됨).
    """
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        logger.info("YouTube 수집 스킵 — YOUTUBE_API_KEY 미설정 (Reddit/Google Trends로 대체)")
        return []

    if regions is None:
        regions = ["KR", "US"]

    results = []
    for region in regions:
        try:
            items = _fetch_trending_api(api_key, region)
            results.extend(items)
            logger.info(f"YouTube {region}: {len(items)}개 수집")
        except Exception as e:
            logger.warning(f"YouTube {region} 수집 실패: {e}")

    # 중복 제거 (URL 기준)
    seen: set[str] = set()
    unique = []
    for item in results:
        if item["source_url"] not in seen:
            seen.add(item["source_url"])
            unique.append(item)
    return unique
