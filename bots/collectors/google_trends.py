"""Google Trends RSS 수집기 (Short-Trend-Radar 포팅, 동기식)"""
from __future__ import annotations

import logging
import re
import urllib.request
from datetime import datetime, timezone

import feedparser

logger = logging.getLogger(__name__)

RSS_ENDPOINT = "https://trends.google.com/trending/rss?geo={region}"

DEFAULT_REGIONS = ["KR", "US"]
MAX_ITEMS = 15  # per region


def _parse_compact_number(text: str) -> int:
    """'1.2M+', '34K' 등 → int"""
    if not text:
        return 0
    text = text.strip().replace(",", "").replace("+", "")
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


def _fetch_rss(region: str) -> list[dict]:
    url = RSS_ENDPOINT.format(region=region.upper())
    items = []
    try:
        # feedparser 직접 파싱 (urllib 통해 content 가져오기)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; blog-writer-bot/0.1)"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read()
        feed = feedparser.parse(content)
        entries = feed.entries[:MAX_ITEMS]
        for idx, entry in enumerate(entries, start=1):
            title = str(entry.get("title", "")).strip()
            if not title:
                continue
            link = str(entry.get("link", f"https://trends.google.com/trending/rss?geo={region.upper()}"))
            # ht_approx_traffic: feedparser namespaced field
            traffic_raw = (
                getattr(entry, "ht_approx_traffic", "")
                or entry.get("ht_approx_traffic", "")
            )
            approx_traffic = _parse_compact_number(re.sub(r"[^0-9KMBkmb.,+]", "", str(traffic_raw)))
            news_title = (
                getattr(entry, "ht_news_item_title", "")
                or entry.get("ht_news_item_title", "")
                or entry.get("summary", "")
                or ""
            )
            trend_score = round(max(10.0, min(100.0, (approx_traffic or 100) / 20.0)), 1)
            items.append({
                "topic": title,
                "description": str(news_title).strip()[:400] or f"Google Trends {region.upper()}: {title}",
                "source": "google_trends",
                "source_url": link,
                "published_at": datetime.now(timezone.utc).isoformat(),
                "search_demand_score": 16,
                "topic_type": "trending",
                "extra": {
                    "rank": idx,
                    "region": region.upper(),
                    "approx_traffic": approx_traffic,
                    "trend_score": trend_score,
                },
            })
    except Exception as e:
        logger.warning(f"Google Trends RSS {region} 수집 실패: {e}")
    return items


def collect(regions: list[str] | None = None) -> list[dict]:
    """Google Trends RSS 수집. 기본: KR + US"""
    if regions is None:
        regions = DEFAULT_REGIONS

    results = []
    for region in regions:
        items = _fetch_rss(region)
        results.extend(items)
        logger.info(f"Google Trends {region}: {len(items)}개 수집")

    # 중복 제거 (topic 기준)
    seen: set[str] = set()
    unique = []
    for item in results:
        key = item["topic"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
