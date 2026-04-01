"""
일간 자동화 파이프라인
수집 → 작성 → Telegram 보고 (발행은 수동)

실행: python scripts/daily_pipeline.py
cron: 매일 09:00 KST
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
from bots.blog_config import DATA_DIR, LOG_DIR, load_settings

load_settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'daily_pipeline.log', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def send_telegram(text: str):
    """Telegram 알림 전송."""
    import requests
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not bot_token or not chat_id:
        logger.warning("Telegram 미설정 — 알림 건너뜀")
        return
    try:
        requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Telegram 전송 실패: {e}")


def run_stats_update() -> dict:
    """블로그 통계 기반 boost_keywords.json 갱신 (매주 월요일)."""
    today = datetime.now()
    if today.weekday() != 0:  # 0 = 월요일
        return {'success': True, 'skipped': True, 'reason': '월요일만 실행'}
    try:
        from bots.stats_bot import run as stats_run
        result = stats_run()
        return {'success': True, 'skipped': False, **result}
    except Exception as e:
        logger.error(f"통계 갱신 실패: {e}")
        return {'success': False, 'error': str(e)}


def run_collect() -> dict:
    """글감 수집."""
    try:
        from bots.collector_bot import run as collector_run
        passed = collector_run()
        return {'success': True, 'collected': len(passed) if passed else 0}
    except Exception as e:
        logger.error(f"수집 실패: {e}")
        return {'success': False, 'error': str(e)}


def run_write(limit: int = 3) -> dict:
    """미처리 글감 작성."""
    try:
        from bots.writer_bot import run_pending
        results = run_pending(limit=limit)
        ok = sum(1 for r in results if r.get('success'))
        fail = len(results) - ok
        titles = [r.get('file', '') for r in results if r.get('success')]
        return {'success': True, 'written': ok, 'failed': fail, 'titles': titles}
    except Exception as e:
        logger.error(f"작성 실패: {e}")
        return {'success': False, 'error': str(e)}


def check_pending_review() -> int:
    """수동 검토 대기 글 수."""
    pending_dir = DATA_DIR / 'pending_review'
    return len(list(pending_dir.glob('*_pending.json'))) if pending_dir.exists() else 0


def check_token_expiry() -> str:
    """Google 토큰 만료일 확인."""
    token_path = BASE_DIR / 'token.json'
    if not token_path.exists():
        return "토큰 파일 없음"
    try:
        token = json.loads(token_path.read_text(encoding='utf-8'))
        expiry = token.get('expiry', 'unknown')
        return expiry
    except Exception:
        return "확인 불가"


def main():
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    logger.info(f"=== 일간 파이프라인 시작: {today} ===")

    # 0. 통계 갱신 (매주 월요일)
    stats_result = run_stats_update()
    logger.info(f"통계: {stats_result}")

    # 1. 수집
    collect_result = run_collect()
    logger.info(f"수집: {collect_result}")

    # 2. 작성
    write_result = run_write(limit=3)
    logger.info(f"작성: {write_result}")

    # 3. 상태 확인
    pending_count = check_pending_review()
    token_expiry = check_token_expiry()

    # 4. Telegram 보고
    report_lines = [f"📊 <b>[일간 보고] {today}</b>", ""]

    if collect_result['success']:
        report_lines.append(f"📥 수집: {collect_result['collected']}건")
    else:
        report_lines.append(f"❌ 수집 실패: {collect_result.get('error', '')[:100]}")

    if write_result['success']:
        report_lines.append(f"✍️ 작성: {write_result['written']}건 성공 / {write_result['failed']}건 실패")
    else:
        report_lines.append(f"❌ 작성 실패: {write_result.get('error', '')[:100]}")

    if pending_count > 0:
        report_lines.append(f"⚠️ 수동 검토 대기: {pending_count}건")

    if not stats_result.get('skipped'):
        if stats_result.get('success'):
            report_lines.append(f"📈 통계 갱신: boost 키워드 {stats_result.get('keywords', 0)}개")
        else:
            report_lines.append(f"⚠️ 통계 갱신 실패: {stats_result.get('error','')[:60]}")

    report_lines.append(f"🔑 토큰 만료: {token_expiry}")
    report_lines.append("")
    report_lines.append("발행은 수동으로: <code>python bots/publisher_bot.py</code>")

    report = '\n'.join(report_lines)
    send_telegram(report)
    logger.info(f"=== 일간 파이프라인 완료 ===")


if __name__ == '__main__':
    main()
