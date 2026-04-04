"""
발행봇 (publisher_bot.py)
역할: AI가 작성한 글을 Blogger에 자동 발행
- 마크다운 → HTML 변환
- 목차 자동 생성
- AdSense 플레이스홀더 삽입
- Schema.org Article JSON-LD
- 안전장치 (팩트체크/위험 키워드/출처 부족 → 수동 검토)
- Blogger API v3 발행
- Search Console URL 제출
- Telegram 알림
"""
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import markdown
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
from bots.blog_config import CONFIG_DIR, DATA_DIR, LOG_DIR, TOKEN_FILE, load_settings

load_settings()

TOKEN_PATH = TOKEN_FILE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'publisher.log', encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
BLOG_MAIN_ID = os.getenv('BLOG_MAIN_ID', '')

SCOPES = [
    'https://www.googleapis.com/auth/blogger',
    'https://www.googleapis.com/auth/webmasters',
]

wp_publisher_bot = None
naver_publisher_bot = None


def load_config(filename: str) -> dict:
    with open(CONFIG_DIR / filename, 'r', encoding='utf-8') as f:
        return json.load(f)


# ─── Google 인증 ─────────────────────────────────────

def get_google_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
    if not creds or not creds.valid:
        raise RuntimeError("Google 인증 실패. scripts/get_token.py 를 먼저 실행하세요.")
    return creds


# ─── 안전장치 ─────────────────────────────────────────

def check_safety(article: dict, safety_cfg: dict) -> tuple[bool, str]:
    """
    수동 검토가 필요한지 판단.
    Returns: (needs_review, reason)
    """
    corner = article.get('corner', '')
    body = article.get('body', '')
    sources = article.get('sources', [])
    quality_score = article.get('quality_score', 100)

    # 팩트체크 코너는 무조건 수동 검토
    manual_corners = safety_cfg.get('always_manual_review', ['팩트체크'])
    if corner in manual_corners:
        return True, f'코너 "{corner}" 는 항상 수동 검토 필요'

    # 위험 키워드 감지
    all_keywords = (
        safety_cfg.get('crypto_keywords', []) +
        safety_cfg.get('criticism_keywords', []) +
        safety_cfg.get('investment_keywords', []) +
        safety_cfg.get('legal_keywords', [])
    )
    for kw in all_keywords:
        if kw in body:
            return True, f'위험 키워드 감지: "{kw}"'

    # 출처 2개 미만
    min_sources = safety_cfg.get('min_sources_required', 2)
    if len(sources) < min_sources:
        return True, f'출처 {len(sources)}개 — {min_sources}개 이상 필요'

    # 품질 점수 미달
    min_score = safety_cfg.get('min_quality_score_for_auto', 75)
    if quality_score < min_score:
        return True, f'품질 점수 {quality_score}점 (자동 발행 최소: {min_score}점)'

    return False, ''


# ─── Persona 로드 ────────────────────────────────────

def _load_persona() -> dict:
    persona_path = CONFIG_DIR / "persona.json"
    if not persona_path.exists():
        return {}
    try:
        return json.loads(persona_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ─── HTML 변환 ─────────────────────────────────────────

def markdown_to_html(md_text: str) -> tuple[str, str]:
    """마크다운 → HTML 변환 (목차 extension 포함)"""
    md = markdown.Markdown(
        extensions=['toc', 'tables', 'fenced_code', 'attr_list'],
        extension_configs={
            'toc': {
                'title': '목차',
                'toc_depth': '2-3',
            }
        }
    )
    html = md.convert(md_text)
    toc = md.toc  # 목차 HTML
    return html, toc


def _is_html(text: str) -> bool:
    """텍스트가 이미 HTML인지 판별 (writer_bot은 HTML로 출력)"""
    return bool(re.search(r'<(h[1-6]|p|div|ul|ol|blockquote)[\s>]', text, re.IGNORECASE))


def _extract_toc_from_html(html: str) -> str:
    """이미 HTML인 본문에서 h2 태그 기반 목차를 생성"""
    soup = BeautifulSoup(html, 'html.parser')
    h2_tags = soup.find_all('h2')
    if not h2_tags:
        return ''

    toc_items = []
    for i, h2 in enumerate(h2_tags):
        anchor = f'section-{i}'
        h2['id'] = anchor
        text = h2.get_text(strip=True)
        toc_items.append(f'<li><a href="#{anchor}">{text}</a></li>')

    toc_html = f'<ul>{"".join(toc_items)}</ul>'
    return toc_html


def prepare_body_html(article: dict) -> tuple[str, str]:
    """
    article body를 Blogger용 HTML로 변환.
    writer_bot이 이미 HTML로 출력하면 그대로 사용, 마크다운이면 변환.
    Returns: (body_html, toc_html)
    """
    body = article.get('body', '')
    if _is_html(body):
        toc_html = _extract_toc_from_html(body)
        return body, toc_html
    else:
        return markdown_to_html(body)


def insert_adsense_placeholders(html: str) -> str:
    """두 번째 H2 뒤와 결론 섹션 앞에 AdSense 플레이스홀더 삽입"""
    persona = _load_persona()
    adsense_cfg = persona.get('blogger', {}).get('adsense', {})
    if not adsense_cfg.get('enabled', True):
        return html

    AD_SLOT_1 = '\n<!-- AD_SLOT_1 -->\n'
    AD_SLOT_2 = '\n<!-- AD_SLOT_2 -->\n'

    soup = BeautifulSoup(html, 'html.parser')
    h2_tags = soup.find_all('h2')

    slot_index = adsense_cfg.get('slot_after_h2_index', 2)
    if len(h2_tags) >= slot_index:
        target_h2 = h2_tags[slot_index - 1]
        ad_tag = BeautifulSoup(AD_SLOT_1, 'html.parser')
        target_h2.insert_after(ad_tag)

    if adsense_cfg.get('slot_before_conclusion', True):
        for h2 in soup.find_all('h2'):
            if any(kw in h2.get_text() for kw in ['결론', '마무리', '정리', '요약', 'conclusion']):
                ad_tag2 = BeautifulSoup(AD_SLOT_2, 'html.parser')
                h2.insert_before(ad_tag2)
                break

    return str(soup)


def build_json_ld(article: dict) -> str:
    """Schema.org Article JSON-LD 생성 (persona.json 기반)"""
    persona = _load_persona()
    blogger_cfg = persona.get('blogger', {})
    blog_url = blogger_cfg.get('blog_url', '')

    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article.get('title', ''),
        "description": article.get('meta', ''),
        "datePublished": datetime.now(timezone.utc).isoformat(),
        "dateModified": datetime.now(timezone.utc).isoformat(),
        "author": {
            "@type": "Organization",
            "name": blogger_cfg.get('author_name', 'The 4th Path')
        },
        "publisher": {
            "@type": "Organization",
            "name": blogger_cfg.get('publisher_name', '22B Labs'),
            "logo": {
                "@type": "ImageObject",
                "url": blogger_cfg.get('logo_url', '')
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": blog_url
        },
        "inLanguage": "ko",
        "keywords": ', '.join(article.get('tags', [])),
        "articleSection": article.get('corner', ''),
    }
    return f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'


def _build_key_points_html(article: dict) -> str:
    """핵심 포인트 3줄 요약 섹션 HTML"""
    key_points = article.get('key_points', [])
    if not key_points:
        return ''

    persona = _load_persona()
    section_cfg = persona.get('blogger', {}).get('html_sections', {}).get('key_points', {})
    if not section_cfg.get('enabled', True):
        return ''

    title = section_cfg.get('title', '3줄 요약')
    items = ''.join(f'<li>{point}</li>' for point in key_points)
    return (
        f'<div class="key-points" '
        f'style="background:#f8f9fa;border-left:4px solid #c8a84e;'
        f'padding:16px 20px;margin:20px 0;border-radius:4px;">\n'
        f'<strong>{title}</strong>\n'
        f'<ul style="margin:8px 0 0 0;padding-left:20px;">{items}</ul>\n'
        f'</div>'
    )


def _build_sources_html(article: dict) -> str:
    """출처 섹션 HTML"""
    sources = article.get('sources', [])
    if not sources:
        return ''

    persona = _load_persona()
    section_cfg = persona.get('blogger', {}).get('html_sections', {}).get('sources', {})
    if not section_cfg.get('enabled', True):
        return ''

    title = section_cfg.get('title', '참고 자료')
    items = []
    for src in sources:
        url = src.get('url', '')
        src_title = src.get('title', url)
        date = src.get('date', '')
        if url:
            link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{src_title}</a>'
        else:
            link = src_title
        date_str = f' ({date})' if date else ''
        items.append(f'<li>{link}{date_str}</li>')

    return (
        f'<div class="sources" style="margin-top:32px;padding-top:16px;border-top:1px solid #eee;">\n'
        f'<h3 style="font-size:1em;color:#666;">{title}</h3>\n'
        f'<ul style="font-size:0.9em;color:#888;">{"".join(items)}</ul>\n'
        f'</div>'
    )


def _build_disclaimer_html(article: dict) -> str:
    """면책 문구 HTML"""
    persona = _load_persona()
    section_cfg = persona.get('blogger', {}).get('html_sections', {}).get('disclaimer', {})
    if not section_cfg.get('enabled', True):
        return ''

    text = article.get('disclaimer', '').strip()
    if not text:
        text = section_cfg.get('default_text', '')
    if not text:
        return ''

    return (
        f'<div class="disclaimer" '
        f'style="margin-top:24px;padding:12px 16px;background:#fafafa;'
        f'border-radius:4px;font-size:0.85em;color:#999;line-height:1.6;">\n'
        f'{text}\n'
        f'</div>'
    )


def build_full_html(article: dict, body_html: str, toc_html: str) -> str:
    """
    최종 Blogger 발행용 HTML 조합:
    JSON-LD → 3줄 요약 → 목차 → 본문(+AdSense) → 출처 → 면책 문구
    """
    persona = _load_persona()
    sections_cfg = persona.get('blogger', {}).get('html_sections', {})

    json_ld = build_json_ld(article)
    key_points_html = _build_key_points_html(article)
    sources_html = _build_sources_html(article)
    disclaimer_html = _build_disclaimer_html(article)

    body_html = insert_adsense_placeholders(body_html)

    html_parts = [json_ld]

    # 3줄 요약 (본문 전)
    if key_points_html:
        html_parts.append(key_points_html)

    # 목차 (본문 전)
    toc_cfg = sections_cfg.get('toc', {})
    if toc_html and toc_cfg.get('enabled', True):
        toc_title = toc_cfg.get('title', '목차')
        html_parts.append(
            f'<details class="toc-wrapper" style="margin:20px 0;padding:12px 16px;'
            f'background:#fafafa;border-radius:4px;">\n'
            f'<summary style="cursor:pointer;font-weight:bold;">{toc_title}</summary>\n'
            f'{toc_html}\n'
            f'</details>'
        )

    # 본문
    html_parts.append(body_html)

    # 출처 (본문 후)
    if sources_html:
        html_parts.append(sources_html)

    # 면책 문구
    if disclaimer_html:
        html_parts.append(disclaimer_html)

    return '\n\n'.join(html_parts)


# ─── Blogger API ──────────────────────────────────────

def _build_labels(article: dict) -> list[str]:
    """persona.json label_strategy에 따라 Blogger 라벨 생성"""
    persona = _load_persona()
    label_cfg = persona.get('blogger', {}).get('label_strategy', {})
    max_labels = label_cfg.get('max_labels', 10)

    labels = []

    # 1순위: 코너 (primary label)
    corner = article.get('corner', '')
    if corner:
        labels.append(corner)

    # 2순위: 태그
    tags = article.get('tags', [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',')]
    labels.extend(tags)

    # 중복 제거 + 빈 문자열 제거 + 개수 제한
    seen = set()
    unique = []
    for label in labels:
        if label and label not in seen:
            seen.add(label)
            unique.append(label)
    return unique[:max_labels]


def publish_to_blogger(article: dict, html_content: str, creds: Credentials) -> dict:
    """Blogger API v3로 글 발행"""
    service = build('blogger', 'v3', credentials=creds)
    blog_id = BLOG_MAIN_ID

    labels = _build_labels(article)

    body = {
        'title': article.get('title', ''),
        'content': html_content,
        'labels': labels,
    }

    result = service.posts().insert(
        blogId=blog_id,
        body=body,
        isDraft=False,
    ).execute()

    return result


def submit_to_search_console(url: str, creds: Credentials):
    """Google Search Console URL 색인 요청"""
    try:
        service = build('searchconsole', 'v1', credentials=creds)
        # URL Inspection API (실제 indexing 요청)
        # 참고: 일반적으로 Blogger sitemap이 자동 제출되므로 보조 수단
        logger.info(f"Search Console 제출: {url}")
        # indexing API는 별도 서비스 계정 필요. 여기서는 로그만 남김.
        # 실제 색인 촉진은 Blogger 내장 sitemap에 의존
    except Exception as e:
        logger.warning(f"Search Console 제출 실패: {e}")


# ─── Telegram ────────────────────────────────────────

def send_telegram(text: str, parse_mode: str = 'HTML'):
    """Telegram 메시지 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram 설정 없음 — 알림 건너뜀")
        return
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': parse_mode,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Telegram 전송 실패: {e}")


def send_pending_review_alert(article: dict, reason: str):
    """수동 검토 대기 알림 (Telegram)"""
    title = article.get('title', '(제목 없음)')
    corner = article.get('corner', '')
    preview = article.get('body', '')[:300].replace('<', '&lt;').replace('>', '&gt;')
    msg = (
        f"🔍 <b>[수동 검토 필요]</b>\n\n"
        f"📌 <b>{title}</b>\n"
        f"코너: {corner}\n"
        f"사유: {reason}\n\n"
        f"미리보기:\n{preview}...\n\n"
        f"명령: <code>승인</code> 또는 <code>거부</code>"
    )
    send_telegram(msg)


# ─── 발행 이력 ───────────────────────────────────────

def log_published(article: dict, post_result: dict):
    """발행 이력 저장"""
    published_dir = DATA_DIR / 'published'
    published_dir.mkdir(exist_ok=True)
    record = {
        'title': article.get('title', ''),
        'corner': article.get('corner', ''),
        'url': post_result.get('url', ''),
        'post_id': post_result.get('id', ''),
        'published_at': datetime.now(timezone.utc).isoformat(),
        'quality_score': article.get('quality_score', 0),
        'tags': article.get('tags', []),
        'sources': article.get('sources', []),
    }
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{record['post_id']}.json"
    with open(published_dir / filename, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return record


def save_pending_review(article: dict, reason: str):
    """수동 검토 대기 글 저장"""
    pending_dir = DATA_DIR / 'pending_review'
    pending_dir.mkdir(exist_ok=True)
    record = {**article, 'pending_reason': reason, 'created_at': datetime.now().isoformat()}
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_pending.json"
    with open(pending_dir / filename, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return pending_dir / filename


def load_pending_review_file(filepath: str) -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def _resolve_publish_targets(platform: str) -> list[str]:
    normalized = (platform or 'blogger').strip().lower()
    mapping = {
        'blogger': ['blogger'],
        'wordpress': ['wordpress'],
        'both': ['blogger', 'wordpress'],
        'naver': ['naver'],
        'all': ['blogger', 'wordpress', 'naver'],
    }
    return mapping.get(normalized, ['blogger'])


def _load_platform_publishers() -> None:
    global wp_publisher_bot, naver_publisher_bot

    if wp_publisher_bot is None:
        from bots import wp_publisher_bot as wp_publisher_module

        wp_publisher_bot = wp_publisher_module

    if naver_publisher_bot is None:
        from bots import naver_publisher_bot as naver_publisher_module

        naver_publisher_bot = naver_publisher_module


def _prepare_full_html(article: dict) -> str:
    if article.get('_html_content'):
        return article['_html_content']

    body_html, toc_html = prepare_body_html(article)
    return build_full_html(article, body_html, toc_html)


def _publish_to_blogger_primary(article: dict, html_content: str, publish_english_version: bool = True) -> bool:
    try:
        creds = get_google_credentials()
    except RuntimeError as e:
        logger.error(str(e))
        return False

    try:
        post_result = publish_to_blogger(article, html_content, creds)
        post_url = post_result.get('url', '')
        logger.info(f"발행 완료: {post_url}")
    except Exception as e:
        logger.error(f"Blogger 발행 실패: {e}")
        return False

    if post_url:
        submit_to_search_console(post_url, creds)

    log_published(article, post_result)

    title = article.get('title', '')
    corner = article.get('corner', '')
    send_telegram(
        f"✅ <b>발행 완료!</b>\n\n"
        f"📌 <b>{title}</b>\n"
        f"코너: {corner}\n"
        f"URL: {post_url}"
    )

    if publish_english_version:
        publish_english(article, creds)

    return True


# ─── 메인 발행 함수 ──────────────────────────────────

def publish_english(article: dict, creds: Credentials) -> bool:
    """
    Korean article → translate → publish to same blog with -en slug.
    Non-blocking: logs errors but does not raise.
    """
    if article.get('lang') == 'en':
        return False  # already English, skip
    try:
        from bots.translator_bot import translate_article
        en_article = translate_article(article)
        body_html, toc_html = prepare_body_html(en_article)
        full_html = build_full_html(en_article, body_html, toc_html)
        post_result = publish_to_blogger(en_article, full_html, creds)
        post_url = post_result.get('url', '')
        log_published(en_article, post_result)
        logger.info(f"영문 발행 완료: {post_url}")
        send_telegram(
            f"🇺🇸 <b>[EN] 영문 발행 완료!</b>\n\n"
            f"📌 <b>{en_article.get('title', '')}</b>\n"
            f"URL: {post_url}"
        )
        return True
    except Exception as e:
        logger.error(f"영문 발행 실패: {e}")
        return False


def publish(article: dict, platform: str = 'blogger', skip_safety: bool = False) -> bool:
    """
    article: OpenClaw blog-writer가 출력한 파싱된 글 dict
    {
        title, meta, slug, tags, corner, body (markdown),
        coupang_keywords, sources, disclaimer, quality_score
    }
    Returns: True(발행 성공) / False(수동 검토 대기)
    """
    normalized_platform = (article.get('_publish_platform') or platform or 'blogger').strip().lower()
    logger.info(f"발행 시도: {article.get('title', '')} [{normalized_platform}]")

    if not skip_safety:
        safety_cfg = load_config('safety_keywords.json')
        needs_review, review_reason = check_safety(article, safety_cfg)
        if needs_review:
            logger.warning(f"수동 검토 대기: {review_reason}")
            queued_article = {**article, '_publish_platform': normalized_platform}
            save_pending_review(queued_article, review_reason)
            send_pending_review_alert(queued_article, review_reason)
            return False

    routed_article = dict(article)
    routed_article['_publish_platform'] = normalized_platform
    routed_article.setdefault('_html_content', _prepare_full_html(routed_article))

    results: list[bool] = []
    for target in _resolve_publish_targets(normalized_platform):
        if target == 'blogger':
            results.append(
                _publish_to_blogger_primary(
                    routed_article,
                    routed_article['_html_content'],
                    publish_english_version=(normalized_platform == 'blogger'),
                )
            )
            continue

        _load_platform_publishers()
        if target == 'wordpress':
            results.append(bool(wp_publisher_bot.publish(routed_article)))
        elif target == 'naver':
            results.append(bool(naver_publisher_bot.publish(routed_article)))

    return bool(results) and all(results)


def approve_pending(filepath: str) -> bool:
    """수동 검토 대기 글 승인 후 발행"""
    try:
        article = load_pending_review_file(filepath)
        platform = article.pop('_publish_platform', 'blogger')
        article.pop('pending_reason', None)
        article.pop('created_at', None)

        success = publish(article, platform=platform, skip_safety=True)
        if not success:
            return False

        Path(filepath).unlink(missing_ok=True)
        send_telegram(
            f"✅ <b>[수동 승인] 발행 완료!</b>\n\n"
            f"📌 {article.get('title', '')}\n"
            f"Platform: {platform}"
        )
        logger.info(f"수동 승인 발행 완료: {filepath} [{platform}]")
        return True
    except Exception as e:
        logger.error(f"승인 발행 실패: {e}")
        return False


def reject_pending(filepath: str):
    """수동 검토 대기 글 거부 (파일 삭제)"""
    try:
        article = load_pending_review_file(filepath)
        Path(filepath).unlink(missing_ok=True)
        send_telegram(f"🗑 <b>[거부]</b> {article.get('title', '')} — 폐기됨")
        logger.info(f"수동 검토 거부: {filepath}")
    except Exception as e:
        logger.error(f"거부 처리 실패: {e}")


def get_pending_list() -> list[dict]:
    """수동 검토 대기 목록 반환"""
    pending_dir = DATA_DIR / 'pending_review'
    pending_dir.mkdir(exist_ok=True)
    result = []
    for f in sorted(pending_dir.glob('*_pending.json')):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            data['_filepath'] = str(f)
            result.append(data)
        except Exception:
            pass
    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='The 4th Path 발행봇')
    parser.add_argument('--file', type=str, help='발행할 원고 JSON 파일 경로')
    parser.add_argument('--dry-run', action='store_true', help='실제 발행 없이 HTML 변환만 확인')
    parser.add_argument('--latest', action='store_true', help='data/originals/ 최신 파일 발행')
    args = parser.parse_args()

    if args.file:
        # 특정 파일 발행
        article_path = Path(args.file)
        if not article_path.exists():
            print(f"[오류] 파일을 찾을 수 없습니다: {args.file}", file=sys.stderr)
            sys.exit(1)
        article = json.loads(article_path.read_text(encoding='utf-8'))
        print(f"발행 대상: {article.get('title', '?')} ({article_path.name})")

    elif args.latest:
        # 최신 원고 발행
        originals = sorted((DATA_DIR / 'originals').glob('*.json'))
        if not originals:
            print("[오류] data/originals/에 원고가 없습니다.", file=sys.stderr)
            sys.exit(1)
        article_path = originals[-1]
        article = json.loads(article_path.read_text(encoding='utf-8'))
        print(f"최신 원고: {article.get('title', '?')} ({article_path.name})")

    else:
        print("사용법:")
        print("  python bots/publisher_bot.py --file data/originals/파일.json")
        print("  python bots/publisher_bot.py --latest")
        print("  python bots/publisher_bot.py --latest --dry-run")
        sys.exit(0)

    if args.dry_run:
        body_html, toc_html = prepare_body_html(article)
        full_html = build_full_html(article, body_html, toc_html)
        print(f"\n[DRY RUN] HTML 생성 완료 ({len(full_html)}자)")
        print(f"  제목: {article.get('title', '')}")
        print(f"  코너: {article.get('corner', '')}")
        print(f"  라벨: {_build_labels(article)}")
        print(f"  HTML 미리보기 (처음 300자):")
        print(f"  {full_html[:300]}")
        sys.exit(0)

    result = publish(article)
    if result:
        print(f"[성공] 발행 완료: {article.get('title', '')}")
    else:
        print(f"[검토대기] 수동 검토로 이동: {article.get('title', '')}")
    sys.exit(0 if result else 1)
