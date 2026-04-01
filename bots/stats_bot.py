"""
stats_bot.py
Search Console + Blogger API에서 블로그 성과 데이터를 가져와
config/boost_keywords.json 을 생성한다.

collector_bot이 이 파일을 읽어 인기 주제 관련 글감에 점수를 가산한다.

실행:
    python bots/stats_bot.py
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from bots.blog_config import CONFIG_DIR, LOG_DIR, load_settings

load_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "stats_bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

BOOST_PATH = CONFIG_DIR / "boost_keywords.json"
BLOG_ID = os.getenv("BLOG_MAIN_ID", "")
SC_SITE = "sc-domain:the4thpath.com"

# 불용어 — 통계적으로 의미 없는 단어
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "to", "for", "is", "it",
    "on", "at", "by", "be", "as", "are", "was", "with", "how", "why",
    "what", "this", "that", "from", "not", "but", "its", "vs", "vs.",
    "review", "reviews", "사용법", "이란", "이란", "이유", "방법", "정리",
    "란", "은", "는", "이", "가", "을", "를", "의", "에", "도",
}


def _get_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token_path = BASE_DIR / "token.json"
    creds = Credentials.from_authorized_user_file(str(token_path))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds


def fetch_search_console(creds, days: int = 90) -> dict:
    """Search Console에서 상위 쿼리/페이지 데이터를 가져온다."""
    from googleapiclient.discovery import build

    sc = build("searchconsole", "v1", credentials=creds)
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    result = {"queries": [], "pages": []}

    # 상위 쿼리 (노출 기준 — 클릭이 아직 적으므로)
    try:
        resp = sc.searchanalytics().query(
            siteUrl=SC_SITE,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": 50,
                "orderBy": [{"fieldName": "impressions", "sortOrder": "DESCENDING"}],
            },
        ).execute()
        result["queries"] = resp.get("rows", [])
        logger.info(f"Search Console 쿼리 {len(result['queries'])}개 로드")
    except Exception as e:
        logger.warning(f"Search Console 쿼리 실패: {e}")

    # 상위 페이지
    try:
        resp = sc.searchanalytics().query(
            siteUrl=SC_SITE,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["page"],
                "rowLimit": 20,
                "orderBy": [{"fieldName": "impressions", "sortOrder": "DESCENDING"}],
            },
        ).execute()
        result["pages"] = resp.get("rows", [])
        logger.info(f"Search Console 페이지 {len(result['pages'])}개 로드")
    except Exception as e:
        logger.warning(f"Search Console 페이지 실패: {e}")

    return result


def fetch_blogger_posts(creds) -> list[dict]:
    """Blogger API에서 발행된 글 목록을 가져온다."""
    from googleapiclient.discovery import build

    service = build("blogger", "v3", credentials=creds)
    posts = []
    try:
        resp = service.posts().list(
            blogId=BLOG_ID,
            maxResults=50,
            status="LIVE",
            view="ADMIN",
            fields="items(id,title,url,labels)",
        ).execute()
        posts = resp.get("items", [])
        logger.info(f"Blogger 포스트 {len(posts)}개 로드")
    except Exception as e:
        logger.warning(f"Blogger API 실패: {e}")
    return posts


def _tokenize(text: str) -> list[str]:
    """텍스트에서 의미 있는 토큰을 추출한다."""
    tokens = re.findall(r"[a-zA-Z가-힣]{2,}", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def build_boost_keywords(sc_data: dict, posts: list[dict]) -> dict:
    """
    수집한 데이터에서 boost_keywords.json 구조를 만든다.

    반환 형식:
    {
        "updated_at": "...",
        "keywords": [
            {"keyword": "paperclip", "weight": 25, "source": "search_console", "impressions": 3158},
            ...
        ]
    }
    """
    keyword_scores: dict[str, dict] = {}

    def _add(kw: str, weight: int, source: str, impressions: float = 0, clicks: float = 0):
        kw = kw.strip().lower()
        if not kw or len(kw) < 2:
            return
        if kw in keyword_scores:
            keyword_scores[kw]["weight"] = max(keyword_scores[kw]["weight"], weight)
            keyword_scores[kw]["impressions"] += impressions
            keyword_scores[kw]["clicks"] += clicks
        else:
            keyword_scores[kw] = {
                "keyword": kw,
                "weight": weight,
                "source": source,
                "impressions": impressions,
                "clicks": clicks,
            }

    # 1. Search Console 쿼리 → 노출/클릭 기반 가중치
    for row in sc_data.get("queries", []):
        query = row["keys"][0]
        impressions = row.get("impressions", 0)
        clicks = row.get("clicks", 0)

        # 노출 구간별 가중치
        if impressions >= 100:
            w = 30
        elif impressions >= 20:
            w = 20
        elif impressions >= 5:
            w = 10
        else:
            w = 5

        # 클릭 있으면 추가 가산
        if clicks >= 3:
            w += 10
        elif clicks >= 1:
            w += 5

        # 쿼리 전체를 키워드로
        _add(query, w, "search_console_query", impressions, clicks)

        # 쿼리에서 토큰 분리해서도 추가
        for token in _tokenize(query):
            _add(token, max(w - 5, 3), "search_console_query", impressions * 0.5)

    # 2. Search Console 상위 페이지 → URL 슬러그에서 키워드 추출
    for row in sc_data.get("pages", []):
        url = row["keys"][0]
        impressions = row.get("impressions", 0)
        if impressions < 5:
            continue
        slug = url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ")
        slug = re.sub(r"\.html$", "", slug)
        for token in _tokenize(slug):
            _add(token, 10, "search_console_page", impressions * 0.3)

    # 3. 기존 인기 글 레이블(코너/태그) → 같은 코너 글감 우선
    corner_counter: Counter = Counter()
    for post in posts:
        labels = post.get("labels", [])
        for label in labels:
            corner_counter[label] += 1

    for label, count in corner_counter.most_common(5):
        w = min(count * 3, 15)
        _add(label, w, "blogger_labels")

    # 정렬 (가중치 내림차순)
    sorted_kws = sorted(keyword_scores.values(), key=lambda x: -x["weight"])

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_period_days": 90,
        "keywords": sorted_kws[:60],  # 상위 60개만
    }


def run() -> dict:
    """stats_bot 메인 실행 함수. boost_keywords.json을 갱신한다."""
    logger.info("=== stats_bot 시작 ===")

    creds = _get_creds()
    sc_data = fetch_search_console(creds)
    posts = fetch_blogger_posts(creds)
    boost = build_boost_keywords(sc_data, posts)

    BOOST_PATH.write_text(json.dumps(boost, ensure_ascii=False, indent=2), encoding="utf-8")
    kw_count = len(boost["keywords"])
    logger.info(f"boost_keywords.json 갱신 완료: {kw_count}개 키워드")

    # 상위 10개 요약 로그
    top10 = boost["keywords"][:10]
    for kw in top10:
        logger.info(f"  [{kw['weight']:>3}점] {kw['keyword']} (노출:{kw.get('impressions',0):.0f})")

    return {"keywords": kw_count, "updated_at": boost["updated_at"]}


if __name__ == "__main__":
    run()
