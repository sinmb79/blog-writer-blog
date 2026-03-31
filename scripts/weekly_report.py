"""
주간 자동화 리포트
발행 현황, 품질 경고, 디스크 사용, 토큰 상태를 Telegram으로 보고.

실행: python scripts/weekly_report.py
cron: 매주 월요일 09:30 KST
"""
import glob
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
from bots.blog_config import DATA_DIR, LOG_DIR, load_settings

load_settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'weekly_report.log', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def send_telegram(text: str):
    import requests
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not bot_token or not chat_id:
        return
    try:
        requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Telegram 전송 실패: {e}")


def get_published_stats() -> dict:
    """이번 주 발행 현황."""
    published_dir = DATA_DIR / 'published'
    if not published_dir.exists():
        return {'total': 0, 'corners': {}}

    week_ago = datetime.now() - timedelta(days=7)
    corners = {}
    total = 0

    for f in published_dir.glob('*.json'):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            pub_date = data.get('published_at', '')
            if pub_date and datetime.fromisoformat(pub_date.replace('Z', '+00:00')) > week_ago:
                total += 1
                c = data.get('corner', '미분류')
                corners[c] = corners.get(c, 0) + 1
        except Exception:
            pass

    return {'total': total, 'corners': corners}


def get_quality_warnings() -> list:
    """최근 7일 품질 경고."""
    originals_dir = DATA_DIR / 'originals'
    if not originals_dir.exists():
        return []

    warnings = []
    week_ago = datetime.now() - timedelta(days=7)

    for f in sorted(originals_dir.glob('*.json'))[-20:]:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            created = data.get('created_at', '')
            issues = data.get('quality_issues', [])
            if issues and created:
                title = data.get('title', '?')[:25]
                warnings.append(f"{title}: {', '.join(issues[:2])}")
        except Exception:
            pass

    return warnings[-5:]  # 최근 5개만


def get_disk_usage() -> dict:
    """디스크 사용량."""
    sizes = {}
    for folder in ['topics', 'originals', 'published', 'pending_review', 'discarded', 'scenarios']:
        p = DATA_DIR / folder
        if p.exists():
            total = sum(f.stat().st_size for f in p.glob('*') if f.is_file())
            sizes[folder] = total
    log_size = sum(f.stat().st_size for f in LOG_DIR.glob('*') if f.is_file()) if LOG_DIR.exists() else 0
    sizes['logs'] = log_size
    return sizes


def get_error_count() -> dict:
    """이번 주 에러 수."""
    errors = {}
    for log_name in ['writer.log', 'publisher.log', 'collector.log', 'daily_pipeline.log']:
        log_path = LOG_DIR / log_name
        if not log_path.exists():
            continue
        count = 0
        try:
            for line in log_path.read_text(encoding='utf-8', errors='replace').splitlines()[-500:]:
                if '[ERROR]' in line:
                    count += 1
        except Exception:
            pass
        if count > 0:
            errors[log_name] = count
    return errors


def format_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val}B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.0f}KB"
    else:
        return f"{bytes_val / (1024 * 1024):.1f}MB"


def main():
    today = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"=== 주간 리포트 생성: {today} ===")

    stats = get_published_stats()
    warnings = get_quality_warnings()
    disk = get_disk_usage()
    errors = get_error_count()

    lines = [f"📋 <b>[주간 리포트] {today}</b>", ""]

    # 발행 현황
    lines.append(f"📰 <b>이번 주 발행: {stats['total']}건</b>")
    if stats['corners']:
        for c, n in sorted(stats['corners'].items(), key=lambda x: -x[1]):
            lines.append(f"  · {c}: {n}건")
    lines.append("")

    # 품질 경고
    if warnings:
        lines.append(f"⚠️ <b>품질 경고 ({len(warnings)}건)</b>")
        for w in warnings:
            lines.append(f"  · {w}")
        lines.append("")

    # 에러
    if errors:
        lines.append("❌ <b>에러 발생</b>")
        for log, count in errors.items():
            lines.append(f"  · {log}: {count}건")
        lines.append("")

    # 디스크
    lines.append("💾 <b>디스크</b>")
    for folder, size in sorted(disk.items(), key=lambda x: -x[1]):
        lines.append(f"  · {folder}: {format_size(size)}")
    lines.append("")

    # 토큰
    token_path = BASE_DIR / 'token.json'
    if token_path.exists():
        try:
            expiry = json.loads(token_path.read_text(encoding='utf-8')).get('expiry', '?')
            lines.append(f"🔑 토큰 만료: {expiry}")
        except Exception:
            lines.append("🔑 토큰 상태: 확인 불가")

    report = '\n'.join(lines)
    send_telegram(report)
    logger.info("주간 리포트 전송 완료")


if __name__ == '__main__':
    main()
