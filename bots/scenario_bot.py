"""
시나리오 봇 (bots/scenario_bot.py)
역할: 아이디어 또는 블로그 원고를 받아서 포맷별 시나리오를 생성하고
      data/scenarios/에 저장. media-forge가 소비할 수 있는 JSON 형식으로 출력.

입력 소스:
  1. 직접 아이디어 입력 (--idea "...")
  2. 블로그 원고 파일 (--from-article path/to/original.json)
  3. 대시보드 API 호출

출력 포맷: content_types.json의 media_forge_bridge.handoff_format 준수.
"""
import argparse
import json
import logging
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
from bots.blog_config import CONFIG_DIR, DATA_DIR, LOG_DIR, load_settings

load_settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'scenario.log', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

SCENARIOS_DIR = DATA_DIR / 'scenarios'

# ─── 설정 로드 ──────────────────────────────────────────

def _load_persona() -> dict:
    path = CONFIG_DIR / 'persona.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_content_types() -> dict:
    path = CONFIG_DIR / 'content_types.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}


# ─── 프롬프트 빌드 ──────────────────────────────────────

def _build_scenario_prompt(
    source_text: str,
    source_type: str,
    target_format: str,
    corner: str = '',
) -> tuple[str, str]:
    """
    시나리오 작성용 system/prompt 생성.
    source_text: 아이디어 텍스트 또는 블로그 원고 body
    target_format: short_script | long_script | webtoon_scenario
    """
    persona = _load_persona()
    content_types = _load_content_types()

    scenario_cfg = persona.get('scenario_writing', {})
    format_guide = scenario_cfg.get('format_guides', {}).get(target_format, {})
    format_def = content_types.get('formats', {}).get(target_format, {})
    constraints = format_def.get('constraints', {})

    principles = '\n'.join(f'- {p}' for p in scenario_cfg.get('principles', []))

    system = f"""{scenario_cfg.get('persona', '')}

## 핵심 원칙
{principles}

## 이번 작업: [{format_def.get('name', target_format)}]
{format_guide.get('system_addon', '')}

## 장면 작성 규칙
{format_guide.get('scene_template', '')}

## 제약 조건
{json.dumps(constraints, ensure_ascii=False, indent=2)}

## 출력 형식
반드시 아래 JSON 형식으로만 출력하라. JSON 외의 텍스트(인사말, 설명)는 절대 출력하지 마라.

```json
{{
  "title_ko": "시나리오 제목",
  "summary": "한 줄 요약",
  "scenes": [
    {{
      "seq": 1,
      "desc_ko": "장면 설명 (한국어)",
      "narration": "나레이션 또는 대사 (한국어)",
      "visual_note": "Visual description in English for image/video generation",
      "duration_sec": 5
    }}
  ]
}}
```

주의:
- scenes의 visual_note는 반드시 영어로 작성 (media-forge 프롬프트용)
- narration은 한국어
- duration_sec는 영상 포맷일 때만 포함 (웹툰은 생략 가능)
- JSON만 출력. 마크다운 코드블록(```)도 감싸지 마라."""

    source_label = "블로그 원고" if source_type == "blog_article" else "아이디어"
    corner_info = f"\n코너: {corner}" if corner else ""

    prompt = f"""다음 {source_label}을 [{format_def.get('name', target_format)}] 시나리오로 변환해줘.
{corner_info}

--- 원본 내용 ---
{source_text}
--- 끝 ---

위 내용을 바탕으로 JSON 시나리오를 생성해라."""

    return system, prompt


# ─── JSON 파싱 ──────────────────────────────────────────

def _parse_scenario_json(raw: str) -> dict | None:
    """엔진 출력에서 JSON을 추출한다."""
    raw = raw.strip()

    # 코드블록 감싸기 제거
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if code_block:
        raw = code_block.group(1).strip()

    # 직접 JSON 파싱
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # { ... } 블록 추출
    brace_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    return None


# ─── 핵심 로직 ──────────────────────────────────────────

def generate_scenario(
    source_text: str,
    source_type: str,
    target_format: str,
    corner: str = '',
    source_ref: str = '',
    tags: list | None = None,
) -> dict:
    """
    시나리오를 생성하고 data/scenarios/에 저장한다.
    Returns: 저장된 시나리오 dict (media-forge handoff 형식)
    Raises: RuntimeError
    """
    from bots.engine_loader import EngineLoader, WriterError

    logger.info(f"시나리오 생성 시작: format={target_format}, source={source_type}")

    system, prompt = _build_scenario_prompt(source_text, source_type, target_format, corner)
    writer = EngineLoader().get_writer()

    try:
        raw_output = writer.write_with_retry(prompt, system=system).strip()
    except WriterError as exc:
        raise RuntimeError(f'시나리오 엔진 오류 ({type(exc).__name__}): {exc}') from exc

    if not raw_output:
        raise RuntimeError('시나리오 엔진 응답이 비어 있음')

    scenario_data = _parse_scenario_json(raw_output)
    if not scenario_data or 'scenes' not in scenario_data:
        raise RuntimeError(f'시나리오 JSON 파싱 실패 (앞 300자): {raw_output[:300]}')

    # media-forge handoff 형식으로 래핑
    content_types = _load_content_types()
    format_def = content_types.get('formats', {}).get(target_format, {})
    media_forge_defaults = format_def.get('media_forge', {}).get('defaults', {})

    request_id = str(uuid.uuid4())
    handoff = {
        'request_id': request_id,
        'source_type': source_type,
        'source_ref': source_ref,
        'format': target_format,
        'title_ko': scenario_data.get('title_ko', ''),
        'summary': scenario_data.get('summary', ''),
        'scenes': scenario_data.get('scenes', []),
        'media_forge_options': media_forge_defaults,
        'metadata': {
            'corner': corner,
            'tags': tags or [],
            'created_at': datetime.now().isoformat(),
        },
    }

    # 저장
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{target_format}_{request_id[:8]}.json"
    output_path = SCENARIOS_DIR / filename
    output_path.write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    logger.info(f"시나리오 저장: {filename} (scenes: {len(handoff['scenes'])})")
    return handoff


def generate_from_article(article_path: str, target_format: str) -> dict:
    """블로그 원고 JSON에서 시나리오 생성."""
    path = Path(article_path)
    article = json.loads(path.read_text(encoding='utf-8'))

    source_text = article.get('body', '')
    if article.get('title'):
        source_text = f"제목: {article['title']}\n\n{source_text}"
    if article.get('key_points'):
        kp = '\n'.join(f'- {p}' for p in article['key_points'])
        source_text += f"\n\n핵심 포인트:\n{kp}"

    return generate_scenario(
        source_text=source_text,
        source_type='blog_article',
        target_format=target_format,
        corner=article.get('corner', ''),
        source_ref=str(path),
        tags=article.get('tags', []),
    )


def generate_from_idea(idea: str, target_format: str, corner: str = '') -> dict:
    """직접 입력한 아이디어에서 시나리오 생성."""
    return generate_scenario(
        source_text=idea,
        source_type='idea',
        target_format=target_format,
        corner=corner,
    )


# ─── CLI ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='The 4th Path 시나리오 봇')
    parser.add_argument('--idea', type=str, help='직접 아이디어 입력')
    parser.add_argument('--from-article', type=str, help='블로그 원고 JSON 경로')
    parser.add_argument(
        '--format', type=str, default='short_script',
        choices=['short_script', 'long_script', 'webtoon_scenario'],
        help='시나리오 포맷 (기본: short_script)',
    )
    parser.add_argument('--corner', type=str, default='', help='코너 지정')
    args = parser.parse_args()

    if not args.idea and not args.from_article:
        parser.error('--idea 또는 --from-article 중 하나를 지정하세요.')

    try:
        if args.from_article:
            result = generate_from_article(args.from_article, args.format)
        else:
            result = generate_from_idea(args.idea, args.format, corner=args.corner)

        print(f"[완료] {result['title_ko']} | scenes: {len(result['scenes'])} | id: {result['request_id'][:8]}")
        sys.exit(0)
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
