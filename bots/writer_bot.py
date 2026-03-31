"""
글쓰기 봇 (bots/writer_bot.py)
역할: topics 폴더의 글감을 읽어 EngineLoader 글쓰기 엔진으로 원고를 생성하고
      data/originals/에 저장하는 독립 실행형 스크립트.

호출:
  python bots/writer_bot.py             — 오늘 날짜 미처리 글감 전부 처리
  python bots/writer_bot.py --topic "..." — 직접 글감 지정 (대화형 사용)
  python bots/writer_bot.py --file path/to/topic.json

대시보드 manual-write 엔드포인트에서도 subprocess로 호출.
"""
import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
from bots.blog_config import CONFIG_DIR, DATA_DIR, LOG_DIR, load_settings

load_settings()

PERSONA_PATH = CONFIG_DIR / "persona.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'writer.log', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ─── 유틸 ────────────────────────────────────────────

def _safe_slug(text: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return slug or datetime.now().strftime('article-%Y%m%d-%H%M%S')


def _load_persona() -> dict:
    """config/persona.json을 로드한다. 없으면 빈 dict."""
    if not PERSONA_PATH.exists():
        return {}
    try:
        return json.loads(PERSONA_PATH.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}


def _build_prompt(topic_data: dict) -> tuple[str, str]:
    topic = topic_data.get('topic', '').strip()
    corner = topic_data.get('corner', '쉬운세상').strip() or '쉬운세상'
    description = topic_data.get('description', '').strip()
    source = topic_data.get('source_url') or topic_data.get('source') or ''
    published_at = topic_data.get('published_at', '')

    persona = _load_persona()
    voice = persona.get('voice', {})
    corner_cfg = persona.get('corners', {}).get(corner, {})
    writing_rules = persona.get('writing_rules', {})
    blog_info = persona.get('blog', {})

    # ── 시스템 프롬프트: 페르소나 + 브랜드 보이스 ──
    principles_text = '\n'.join(f'- {p}' for p in voice.get('principles', []))
    forbidden_text = ', '.join(f'"{f}"' for f in voice.get('forbidden_phrases', []))

    corner_tone = corner_cfg.get('tone', '')
    corner_structure = corner_cfg.get('structure_guide', '')
    corner_must = corner_cfg.get('must_include', [])
    corner_must_text = '\n'.join(f'- {m}' for m in corner_must)
    body_min_words = corner_cfg.get('body_min_words', 600)

    title_rules = writing_rules.get('title', {})
    title_good = '\n'.join(f'  - {e}' for e in title_rules.get('examples_good', []))
    title_bad = '\n'.join(f'  - {e}' for e in title_rules.get('examples_bad', []))

    system = f"""당신은 "{blog_info.get('name', 'The 4th Path')}" 블로그의 전문 에디터다.
태그라인: {blog_info.get('tagline', '')}
대상 독자: {blog_info.get('target_audience', '')}

## 당신의 성격
{voice.get('personality', '')}

## 글쓰기 톤
{voice.get('tone', '')}

## 핵심 원칙
{principles_text}

## 금지 표현
다음 표현은 절대 사용하지 마라: {forbidden_text}

## 이번 코너: [{corner}]
설명: {corner_cfg.get('description', '')}
톤: {corner_tone}
글 구조: {corner_structure}
반드시 포함할 것:
{corner_must_text}

## 제목 규칙
- 최대 {title_rules.get('max_length', 40)}자
- {title_rules.get('style', '')}
- 좋은 예:
{title_good}
- 나쁜 예:
{title_bad}

## 본문 규칙
- 최소 {body_min_words}자
- 문단당 최대 {writing_rules.get('body', {}).get('paragraph_max_sentences', 4)}문장
- {writing_rules.get('body', {}).get('html_format', 'Blogger-ready HTML')}
- SEO: 키워드를 제목과 첫 문단에 포함

## 출력 형식 (절대 규칙)
- 첫 번째 줄은 반드시 ---TITLE--- 이어야 한다.
- 마지막 섹션은 ---DISCLAIMER--- 이다.
- 각 섹션은 ---이름--- 형식이다.
- "확인했습니다", "알겠습니다", "네", "작성하겠습니다" 같은 응답 금지.
- 인사말, 설명, 부연 텍스트 일절 금지. 오직 섹션 헤더와 내용만 출력.
- 이 지시를 어기면 실패로 처리된다."""

    prompt = f"""[중요] 아래 글감으로 완성된 한국어 블로그 원고를 지금 바로 출력하라. 대화하지 마라. 첫 줄은 반드시 ---TITLE--- 이다.

주제: {topic}
코너: {corner}
설명: {description}
출처: {source}
발행시점 참고: {published_at}

출력 형식 (첫 줄부터 이 형식으로 시작하라):

---TITLE---
(제목. 40자 이내. 클릭베이트 금지.)

---META---
(검색 설명 150자 이내. 글의 핵심 가치 한 문장.)

---SLUG---
(영문 소문자 하이픈 slug)

---TAGS---
(쉼표 구분 태그 3-5개)

---CORNER---
{corner}

---BODY---
(Blogger-ready HTML 본문. <h2>로 섹션 구분. 최소 {body_min_words}자.)

---KEY_POINTS---
(핵심 포인트 3줄, 각 줄 앞에 - 붙여라)

---COUPANG_KEYWORDS---
(쿠팡 검색 키워드 2-3개, 쉼표 구분)

---SOURCES---
{source} | 참고 출처 | {published_at}

---DISCLAIMER---
(필요 시 짧은 면책문구. 없으면 빈 줄.)

[다시 한번 강조] 위 형식대로 바로 시작하라. "네", "알겠습니다" 등의 응답을 하면 실패다.

---TITLE---"""
    return system, prompt


# ─── 핵심 로직 ───────────────────────────────────────

def write_article(topic_data: dict, output_path: Path) -> dict:
    """
    topic_data → EngineLoader 호출 → article dict 저장.
    Returns: article dict (저장 완료)
    Raises: RuntimeError — 글 작성 또는 파싱 실패 시
    """
    from bots.engine_loader import EngineLoader, WriterError
    from bots.article_parser import parse_output
    from bots.article_schema import validate_article

    title = topic_data.get('topic', topic_data.get('title', ''))
    logger.info(f"글 작성 시작: {title}")

    system, prompt = _build_prompt(topic_data)
    writer = EngineLoader().get_writer()

    try:
        raw_output = writer.write_with_retry(prompt, system=system).strip()
    except WriterError as exc:
        raise RuntimeError(f'글쓰기 엔진 오류 ({type(exc).__name__}): {exc}') from exc

    # 프롬프트가 ---TITLE---로 끝나므로, 응답이 제목부터 시작할 수 있음
    # ---TITLE--- 가 없으면 앞에 붙여준다
    if raw_output and '---TITLE---' not in raw_output:
        raw_output = '---TITLE---\n' + raw_output

    if not raw_output:
        raise RuntimeError('글쓰기 엔진 응답이 비어 있습니다.')

    article = parse_output(raw_output)
    if not article:
        raise RuntimeError(f'글쓰기 엔진 출력 파싱 실패 (앞 200자): {raw_output[:200]}')

    # 품질 guardrail (blocking 아님, 경고만)
    issues = validate_article(article, corner=topic_data.get('corner', ''))
    if issues:
        for issue in issues:
            logger.warning(f"품질 경고: {issue}")

    article.setdefault('title', title)
    article['slug'] = article.get('slug') or _safe_slug(article['title'])
    article['corner'] = article.get('corner') or topic_data.get('corner', '쉬운세상')
    article['topic'] = topic_data.get('topic', '')
    article['description'] = topic_data.get('description', '')
    article['quality_score'] = topic_data.get('quality_score', 0)
    article['source'] = topic_data.get('source', '')
    article['source_url'] = topic_data.get('source_url') or topic_data.get('source') or ''
    article['published_at'] = topic_data.get('published_at', '')
    article['created_at'] = datetime.now().isoformat()
    article['quality_issues'] = issues

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(article, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    logger.info(f"원고 저장 완료: {output_path.name}")
    return article


def run_pending(limit: int = 3) -> list[dict]:
    """
    data/topics/ 에서 오늘 날짜 미처리 글감을 최대 limit개 처리.
    Returns: 처리 결과 리스트 [{'slug':..., 'success':..., 'error':...}]
    """
    topics_dir = DATA_DIR / 'topics'
    originals_dir = DATA_DIR / 'originals'
    originals_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y%m%d')
    topic_files = sorted(topics_dir.glob(f'{today}_*.json'))

    if not topic_files:
        logger.info("오늘 날짜 글감 없음")
        return []

    results = []
    processed = 0
    for topic_file in topic_files:
        if processed >= limit:
            break
        output_path = originals_dir / topic_file.name
        if output_path.exists():
            logger.debug(f"이미 처리됨: {topic_file.name}")
            continue
        try:
            topic_data = json.loads(topic_file.read_text(encoding='utf-8'))
            article = write_article(topic_data, output_path)
            results.append({'file': topic_file.name, 'slug': article.get('slug', ''), 'success': True})
            processed += 1
        except Exception as e:
            logger.error(f"글 작성 실패 [{topic_file.name}]: {e}")
            results.append({'file': topic_file.name, 'slug': '', 'success': False, 'error': str(e)})

    return results


def run_from_topic(topic: str, corner: str = '쉬운세상') -> dict:
    """
    직접 주제 문자열로 글 작성.
    Returns: article dict
    """
    originals_dir = DATA_DIR / 'originals'
    originals_dir.mkdir(parents=True, exist_ok=True)

    slug = _safe_slug(topic)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug}.json"
    output_path = originals_dir / filename

    topic_data = {
        'topic': topic,
        'corner': corner,
        'description': '',
        'source': '',
        'published_at': datetime.now().isoformat(),
    }
    return write_article(topic_data, output_path)


def run_from_file(file_path: str) -> dict:
    """
    JSON 파일에서 topic_data를 읽어 글 작성.
    """
    originals_dir = DATA_DIR / 'originals'
    originals_dir.mkdir(parents=True, exist_ok=True)

    topic_file = Path(file_path)
    topic_data = json.loads(topic_file.read_text(encoding='utf-8'))
    output_path = originals_dir / topic_file.name
    return write_article(topic_data, output_path)


# ─── CLI 진입점 ──────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='The 4th Path 글쓰기 봇')
    parser.add_argument('--topic', type=str, help='직접 글감 지정')
    parser.add_argument('--corner', type=str, default='쉬운세상', help='코너 지정 (기본: 쉬운세상)')
    parser.add_argument('--file', type=str, help='글감 JSON 파일 경로')
    parser.add_argument('--limit', type=int, default=3, help='최대 처리 글 수 (기본: 3)')
    args = parser.parse_args()

    if args.topic:
        try:
            article = run_from_topic(args.topic, corner=args.corner)
            print(f"[완료] 제목: {article.get('title', '')} | slug: {article.get('slug', '')}")
            sys.exit(0)
        except Exception as e:
            print(f"[오류] {e}", file=sys.stderr)
            sys.exit(1)

    if args.file:
        try:
            article = run_from_file(args.file)
            print(f"[완료] 제목: {article.get('title', '')} | slug: {article.get('slug', '')}")
            sys.exit(0)
        except Exception as e:
            print(f"[오류] {e}", file=sys.stderr)
            sys.exit(1)

    # 기본: 오늘 날짜 미처리 글감 처리
    results = run_pending(limit=args.limit)
    if not results:
        print("[완료] 처리할 글감 없음")
        sys.exit(0)

    ok = sum(1 for r in results if r['success'])
    fail = len(results) - ok
    print(f"[완료] 성공 {ok}건 / 실패 {fail}건")
    for r in results:
        status = '✅' if r['success'] else '❌'
        err = f" ({r.get('error', '')})" if not r['success'] else ''
        print(f"  {status} {r['file']}{err}")

    sys.exit(0 if fail == 0 else 1)


if __name__ == '__main__':
    main()
