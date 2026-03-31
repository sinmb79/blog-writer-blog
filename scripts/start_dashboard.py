"""
Telegram 대시보드 봇 시작 스크립트.

실행: python scripts/start_dashboard.py
백그라운드: nohup python scripts/start_dashboard.py > logs/dashboard.out 2>&1 &
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from bots.blog_config import load_settings
load_settings()

from bots.telegram_dashboard import create_app, BOT_TOKEN


def main():
    if not BOT_TOKEN:
        print("[오류] TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    print("🚀 The 4th Path Telegram 대시보드 시작...")
    print("   Ctrl+C로 종료")
    app = create_app()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
