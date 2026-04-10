"""Reddit Hot 수집기 (Short-Trend-Radar 포팅, 동기식)"""
from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = [
    "artificial",
    "MachineLearning",
    "singularity",
    "ChatGPT",
    "technology",
    "programming",
]

SORT = "hot"
MAX_ITEMS = 10  # per subreddit → deduped after
USER_AGENT = "blog-writer-bot/0.1"


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _parse_listing(subreddit: str, payload: dict) -> list[dict]:
    items = []
    children = payload.get("data", {}).get("children", [])
    for child in children:
        data = child.get("data", {})
        title = data.get("title", "").strip()
        permalink = data.get("permalink", "")
        if not title or not permalink:
            continue
        description = (
            data.get("selftext", "")
            or data.get("url_overridden_by_dest", "")
            or ""
        )
        ups = data.get("ups", 0)
        num_comments = data.get("num_comments", 0)
        created_utc = data.get("created_utc")
        pub_at = (
            datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
            if created_utc
            else datetime.now(timezone.utc).isoformat()
        )
        items.append({
            "topic": title,
            "description": description[:500] if description else f"r/{subreddit} — {title}",
            "source": "reddit",
            "source_url": f"https://www.reddit.com{permalink}",
            "published_at": pub_at,
            "search_demand_score": 14,
            "topic_type": "trending",
            "extra": {
                "subreddit": subreddit,
                "ups": ups,
                "comments": num_comments,
            },
        })
    return items


def collect(subreddits: list[str] | None = None) -> list[dict]:
    """Reddit Hot 수집. 기본: DEFAULT_SUBREDDITS"""
    if subreddits is None:
        subreddits = DEFAULT_SUBREDDITS

    results = []
    for subreddit in subreddits:
        url = f"https://www.reddit.com/r/{subreddit}/{SORT}.json?limit={MAX_ITEMS}"
        try:
            payload = _fetch_json(url)
            items = _parse_listing(subreddit, payload)
            results.extend(items)
            logger.info(f"Reddit r/{subreddit}: {len(items)}개 수집")
        except Exception as e:
            logger.warning(f"Reddit r/{subreddit} 수집 실패: {e}")

    # 중복 제거 (URL 기준)
    seen: set[str] = set()
    unique = []
    for item in results:
        if item["source_url"] not in seen:
            seen.add(item["source_url"])
            unique.append(item)
    return unique
