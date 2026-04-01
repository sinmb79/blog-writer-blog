"""
오늘 발행된 한국어 글들을 영문으로 일괄 발행.
일회성 스크립트.
"""
import json
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from bots.blog_config import DATA_DIR, load_settings
load_settings()

from bots.publisher_bot import (
    get_google_credentials,
    prepare_body_html,
    build_full_html,
    publish_to_blogger,
    log_published,
    send_telegram,
)
from bots.translator_bot import translate_article

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

# 오늘 발행된 한국어 원고 파일
originals = sorted(Path(DATA_DIR / 'originals').glob('20260401_*.json'))

creds = get_google_credentials()

for path in originals:
    article = json.loads(path.read_text(encoding='utf-8'))
    title = article.get('title', '')

    if article.get('lang') == 'en':
        logger.info(f"건너뜀 (이미 영문): {title}")
        continue

    logger.info(f"번역 시작: {title}")
    try:
        en_article = translate_article(article)
        body_html, toc_html = prepare_body_html(en_article)
        full_html = build_full_html(en_article, body_html, toc_html)
        post_result = publish_to_blogger(en_article, full_html, creds)
        post_url = post_result.get('url', '')
        log_published(en_article, post_result)
        logger.info(f"  영문 발행 완료: {post_url}")
        send_telegram(
            f"🇺🇸 <b>[EN] 영문 발행 완료!</b>\n\n"
            f"📌 <b>{en_article.get('title', '')}</b>\n"
            f"URL: {post_url}"
        )
        time.sleep(6)  # rate limit 방지
    except Exception as e:
        logger.error(f"  실패 [{title}]: {e}")
        time.sleep(3)
