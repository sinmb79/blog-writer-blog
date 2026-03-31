"""
월간 리마인더
수동 점검이 필요한 항목을 Telegram으로 알림.

실행: python scripts/monthly_reminder.py
cron: 매월 1일 10:00 KST
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
from bots.blog_config import LOG_DIR, load_settings

load_settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'monthly_reminder.log', encoding='utf-8'),
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


def main():
    month = datetime.now().strftime('%Y-%m')

    checklist = f"""🗓 <b>[월간 점검 리마인더] {month}</b>

<b>config/persona.json</b>
☐ 코너별 톤 가이드가 실제 발행 글과 맞는지
☐ 금지 표현 목록 업데이트
☐ 제목 좋은/나쁜 예시 업데이트

<b>config/sources.json</b>
☐ RSS 피드 URL 유효성 확인
☐ X 키워드 시대 반영
☐ 신규 소스 추가 검토

<b>config/quality_rules.json</b>
☐ min_score(60) 적절한지
☐ 한국 관련성 키워드 업데이트

<b>config/safety_keywords.json</b>
☐ 위험 키워드 추가 필요한지
☐ auto_publish 점수(75) 조정

<b>에이전트 instructions.md</b>
☐ blog-writer few-shot 예시 → 최근 성공 원고로 교체
☐ mediaforge 스킬 실제 사용 현황 확인

<b>MEMORY.md 정리</b>
☐ ~/.openclaw/workspace/MEMORY.md
☐ mediaforge/MEMORY.md

<b>의존성</b>
☐ pip list --outdated (blog-writer-blog)
☐ npm outdated (mediaforge)

<b>로그 정리</b>
☐ 30일+ 로그 삭제: find logs/ -mtime +30 -delete"""

    send_telegram(checklist)
    logger.info("월간 리마인더 전송 완료")


if __name__ == '__main__':
    main()
