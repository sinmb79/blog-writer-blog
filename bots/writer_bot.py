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
    corner_cfg = persona.get('corners', {}).get(corner, {})
    body_min_words = corner_cfg.get('body_min_words', 600)
    corner_tone = corner_cfg.get('tone', '')
    corner_structure = corner_cfg.get('structure_guide', '')
    writing_persona = corner_cfg.get('writing_persona', '')

    # ── 시스템: 최소한으로. ──
    persona_line = f"\n글쓰기 스타일: {writing_persona}" if writing_persona else ""
    system = f"""한국어 블로그 원고 생성기. 대화 금지. ---TITLE---부터 완성 원고만 출력.
코너 [{corner}]: {corner_tone}{persona_line}
{body_min_words}자 이상. HTML(<h2>,<p>,<ul>,<pre><code>). 과장 금지.
필수: 실행 예제 코드(<pre><code>)를 1개 이상 포함. 구체적 수치(별 수, 비용, 성능) 포함. 커뮤니티 반응 언급."""

    prompt = f"""{topic}에 대한 블로그 원고를 써라. 제목과 본문에 "{topic}"을 반드시 포함하라.

{description}

출처: {source}

위 정보를 바탕으로 ---TITLE---부터 시작. "{topic}"을 본문 첫 문단에 명시:

---TITLE---
(40자 이내 제목)

---META---
(150자 이내 검색 설명)

---SLUG---
(영문 slug)

---TAGS---
(태그 3-5개)

---CORNER---
{corner}

---BODY---
(<h2>섹션 제목</h2><p>본문</p> 형식 HTML. 최소 {body_min_words}자.)

---KEY_POINTS---
- 핵심1
- 핵심2
- 핵심3

---COUPANG_KEYWORDS---
(키워드 2-3개)

---SOURCES---
{source} | 출처명 | {published_at}

---DISCLAIMER---

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
