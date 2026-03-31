"""
Telegram 대시보드 봇 (bots/telegram_dashboard.py)
BonkBot 스타일 인라인 키보드로 블로그 파이프라인을 제어한다.

기능: 수집, 작성, 발행, 상태, 시나리오, 설정
실행: python scripts/start_dashboard.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
from bots.blog_config import CONFIG_DIR, DATA_DIR, LOG_DIR, load_settings

load_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "telegram_dashboard.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_DASHBOARD_TOKEN", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_IDS = {int(cid) for cid in os.getenv("TELEGRAM_CHAT_ID", "").split(",") if cid.strip()}

# Conversation states
WAITING_TOPIC, WAITING_CORNER, WAITING_SCENARIO_IDEA, WAITING_SCENARIO_FORMAT = range(4)


# ─── 접근 제어 ──────────────────────────────────────────

def authorized(func):
    """CHAT_ID 화이트리스트 데코레이터."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
            await update.effective_message.reply_text("접근 권한이 없습니다.")
            return
        return await func(update, context)
    return wrapper


# ─── 메인 패널 ──────────────────────────────────────────

def main_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📥 수집", callback_data="cmd_collect"),
            InlineKeyboardButton("✍️ 작성", callback_data="cmd_write_menu"),
        ],
        [
            InlineKeyboardButton("📤 발행", callback_data="cmd_publish_menu"),
            InlineKeyboardButton("📋 상태", callback_data="cmd_status"),
        ],
        [
            InlineKeyboardButton("🎬 시나리오", callback_data="cmd_scenario_menu"),
            InlineKeyboardButton("⚙️ 설정", callback_data="cmd_settings"),
        ],
        [
            InlineKeyboardButton("🔄 전체 파이프라인", callback_data="cmd_full_pipeline"),
        ],
    ])


@authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 <b>The 4th Path 대시보드</b>\n\n작업을 선택하세요:",
        reply_markup=main_panel_keyboard(),
        parse_mode="HTML",
    )


@authorized
async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


# ─── 수집 ───────────────────────────────────────────────

@authorized
async def handle_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("⏳ 수집 중...")

    result = await asyncio.to_thread(_run_collect)

    if result["success"]:
        text = (
            f"📥 <b>수집 완료</b>\n"
            f"  통과: {result['collected']}건\n"
            f"  폐기: {result.get('discarded', 0)}건"
        )
    else:
        text = f"❌ 수집 실패: {result.get('error', '')[:200]}"

    await msg.edit_text(text, reply_markup=_back_button(), parse_mode="HTML")


def _run_collect() -> dict:
    try:
        from bots.collector_bot import collect_topics
        result = collect_topics()
        return {"success": True, "collected": result.get("collected", 0), "discarded": result.get("discarded", 0)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 작성 ───────────────────────────────────────────────

@authorized
async def handle_write_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    today = datetime.now().strftime("%Y%m%d")
    topics_dir = DATA_DIR / "topics"
    pending = len(list(topics_dir.glob(f"{today}_*.json"))) if topics_dir.exists() else 0

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📝 미처리 글감 작성 ({pending}건)", callback_data="cmd_write_pending")],
        [InlineKeyboardButton("✏️ 주제 직접 입력", callback_data="cmd_write_topic")],
        [InlineKeyboardButton("◀️ 돌아가기", callback_data="cmd_back")],
    ])
    await query.edit_message_text("✍️ <b>작성 방법 선택</b>", reply_markup=keyboard, parse_mode="HTML")


@authorized
async def handle_write_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("⏳ 미처리 글감 작성 중... (최대 3건)")

    result = await asyncio.to_thread(_run_write_pending)

    if result["success"]:
        text = f"✍️ <b>작성 완료</b>\n  성공: {result['written']}건 / 실패: {result['failed']}건"
    else:
        text = f"❌ 작성 실패: {result.get('error', '')[:200]}"

    await msg.edit_text(text, reply_markup=_back_button(), parse_mode="HTML")


def _run_write_pending() -> dict:
    try:
        from bots.writer_bot import run_pending
        results = run_pending(limit=3)
        ok = sum(1 for r in results if r.get("success"))
        return {"success": True, "written": ok, "failed": len(results) - ok}
    except Exception as e:
        return {"success": False, "error": str(e)}


@authorized
async def handle_write_topic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✏️ 주제를 입력하세요:")
    return WAITING_TOPIC


@authorized
async def handle_topic_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pending_topic"] = update.message.text
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("쉬운세상", callback_data="corner_쉬운세상"),
            InlineKeyboardButton("숨은보물", callback_data="corner_숨은보물"),
        ],
        [
            InlineKeyboardButton("바이브리포트", callback_data="corner_바이브리포트"),
            InlineKeyboardButton("팩트체크", callback_data="corner_팩트체크"),
        ],
        [InlineKeyboardButton("한컷", callback_data="corner_한컷")],
    ])
    await update.message.reply_text("📂 코너를 선택하세요:", reply_markup=keyboard)
    return WAITING_CORNER


@authorized
async def handle_corner_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    corner = query.data.replace("corner_", "")
    topic = context.user_data.pop("pending_topic", "")

    msg = await query.edit_message_text(f"⏳ 작성 중...\n주제: {topic}\n코너: {corner}")

    result = await asyncio.to_thread(_run_write_topic, topic, corner)

    if result["success"]:
        text = f"✍️ <b>작성 완료</b>\n  제목: {result['title']}\n  코너: {corner}"
    else:
        text = f"❌ 작성 실패: {result.get('error', '')[:200]}"

    await msg.edit_text(text, reply_markup=_back_button(), parse_mode="HTML")
    return ConversationHandler.END


def _run_write_topic(topic: str, corner: str) -> dict:
    try:
        from bots.writer_bot import run_from_topic
        article = run_from_topic(topic, corner=corner)
        return {"success": True, "title": article.get("title", "")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 발행 ───────────────────────────────────────────────

@authorized
async def handle_publish_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pending = _get_pending_list()
    if not pending:
        await query.edit_message_text(
            "📤 발행 대기 글이 없습니다.\n\n원고(`data/originals/`)를 먼저 작성하세요.",
            reply_markup=_back_button(),
        )
        return

    buttons = []
    for i, p in enumerate(pending[:5]):
        title = p.get("title", "?")[:25]
        reason = p.get("pending_reason", "")[:20]
        buttons.append([InlineKeyboardButton(f"✅ {title} ({reason})", callback_data=f"approve_{i}")])

    buttons.append([InlineKeyboardButton("📤 전체 발행 (안전장치 통과분)", callback_data="cmd_publish_all")])
    buttons.append([InlineKeyboardButton("◀️ 돌아가기", callback_data="cmd_back")])

    context.user_data["pending_files"] = [p.get("_filepath", "") for p in pending[:5]]
    await query.edit_message_text(
        f"📤 <b>수동 검토 대기: {len(pending)}건</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML",
    )


@authorized
async def handle_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.replace("approve_", ""))
    filepath = context.user_data.get("pending_files", [])[idx] if idx < len(context.user_data.get("pending_files", [])) else ""

    if not filepath:
        await query.edit_message_text("❌ 파일을 찾을 수 없습니다.", reply_markup=_back_button())
        return

    msg = await query.edit_message_text("⏳ 발행 중...")
    result = await asyncio.to_thread(_run_approve, filepath)

    text = "✅ <b>발행 완료!</b>" if result else "❌ 발행 실패. 로그를 확인하세요."
    await msg.edit_text(text, reply_markup=_back_button(), parse_mode="HTML")


def _run_approve(filepath: str) -> bool:
    try:
        from bots.publisher_bot import approve_pending
        return approve_pending(filepath)
    except Exception:
        return False


@authorized
async def handle_publish_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("⏳ 안전장치 통과 원고 발행 중...")

    result = await asyncio.to_thread(_run_publish_originals)
    text = f"📤 <b>발행 결과</b>\n  성공: {result['ok']}건 / 수동검토: {result['review']}건"
    await msg.edit_text(text, reply_markup=_back_button(), parse_mode="HTML")


def _run_publish_originals() -> dict:
    from bots.publisher_bot import publish
    originals_dir = DATA_DIR / "originals"
    ok, review = 0, 0
    for f in sorted(originals_dir.glob("*.json"))[-5:]:
        try:
            article = json.loads(f.read_text(encoding="utf-8"))
            if publish(article):
                ok += 1
            else:
                review += 1
        except Exception:
            review += 1
    return {"ok": ok, "review": review}


def _get_pending_list() -> list:
    try:
        from bots.publisher_bot import get_pending_list
        return get_pending_list()
    except Exception:
        return []


# ─── 상태 ───────────────────────────────────────────────

@authorized
async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    status = await asyncio.to_thread(_get_status)
    text = (
        f"📋 <b>시스템 상태</b>\n\n"
        f"📥 글감: {status['topics']}건\n"
        f"✍️ 원고: {status['originals']}건\n"
        f"⏳ 검토 대기: {status['pending']}건\n"
        f"📰 발행 완료: {status['published']}건\n"
        f"🎬 시나리오: {status['scenarios']}건\n"
        f"\n❌ 오늘 에러: {status['errors']}건\n"
        f"🔑 토큰 만료: {status['token_expiry']}"
    )
    await query.edit_message_text(text, reply_markup=_back_button(), parse_mode="HTML")


def _get_status() -> dict:
    counts = {}
    for folder in ["topics", "originals", "pending_review", "published", "scenarios"]:
        p = DATA_DIR / folder
        counts[folder.replace("pending_review", "pending")] = len(list(p.glob("*.json"))) if p.exists() else 0

    # 오늘 에러 수
    errors = 0
    for log_name in ["writer.log", "publisher.log", "collector.log"]:
        log_path = LOG_DIR / log_name
        if log_path.exists():
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]:
                    if today in line and "[ERROR]" in line:
                        errors += 1
            except Exception:
                pass

    # 토큰
    token_expiry = "확인 불가"
    token_path = BASE_DIR / "token.json"
    if token_path.exists():
        try:
            token_expiry = json.loads(token_path.read_text(encoding="utf-8")).get("expiry", "?")
        except Exception:
            pass

    return {
        "topics": counts.get("topics", 0),
        "originals": counts.get("originals", 0),
        "pending": counts.get("pending", 0),
        "published": counts.get("published", 0),
        "scenarios": counts.get("scenarios", 0),
        "errors": errors,
        "token_expiry": token_expiry,
    }


# ─── 시나리오 ───────────────────────────────────────────

@authorized
async def handle_scenario_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 숏폼 (30-60초)", callback_data="scenario_short_script"),
            InlineKeyboardButton("🎥 롱폼 (3-10분)", callback_data="scenario_long_script"),
        ],
        [InlineKeyboardButton("📖 웹툰 (4-8컷)", callback_data="scenario_webtoon_scenario")],
        [InlineKeyboardButton("◀️ 돌아가기", callback_data="cmd_back")],
    ])
    await query.edit_message_text("🎬 <b>시나리오 포맷 선택</b>", reply_markup=keyboard, parse_mode="HTML")


@authorized
async def handle_scenario_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fmt = query.data.replace("scenario_", "")
    context.user_data["scenario_format"] = fmt
    await query.edit_message_text(f"💡 아이디어를 입력하세요 (포맷: {fmt}):")
    return WAITING_SCENARIO_IDEA


@authorized
async def handle_scenario_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idea = update.message.text
    fmt = context.user_data.pop("scenario_format", "short_script")

    msg = await update.message.reply_text(f"⏳ 시나리오 생성 중...\n포맷: {fmt}")

    result = await asyncio.to_thread(_run_scenario, idea, fmt)

    if result["success"]:
        text = (
            f"🎬 <b>시나리오 완료</b>\n"
            f"  제목: {result['title']}\n"
            f"  장면: {result['scenes']}개\n"
            f"  파일: <code>{result['file']}</code>"
        )
    else:
        text = f"❌ 시나리오 실패: {result.get('error', '')[:200]}"

    await msg.edit_text(text, reply_markup=_back_button(), parse_mode="HTML")
    return ConversationHandler.END


def _run_scenario(idea: str, fmt: str) -> dict:
    try:
        from bots.scenario_bot import generate_from_idea
        result = generate_from_idea(idea, fmt)
        return {
            "success": True,
            "title": result.get("title_ko", ""),
            "scenes": len(result.get("scenes", [])),
            "file": result.get("request_id", "")[:8],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 설정 ───────────────────────────────────────────────

@authorized
async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # engine.json 읽기
    engine_path = CONFIG_DIR / "engine.json"
    provider = "?"
    if engine_path.exists():
        try:
            cfg = json.loads(engine_path.read_text(encoding="utf-8"))
            provider = cfg.get("writing", {}).get("provider", "?")
        except Exception:
            pass

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 전체 파이프라인 실행", callback_data="cmd_full_pipeline")],
        [InlineKeyboardButton("◀️ 돌아가기", callback_data="cmd_back")],
    ])

    text = (
        f"⚙️ <b>설정</b>\n\n"
        f"글쓰기 엔진: {provider}\n"
        f"프로젝트: {BASE_DIR}\n"
    )
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


# ─── 전체 파이프라인 ────────────────────────────────────

@authorized
async def handle_full_pipeline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("🔄 전체 파이프라인 실행 중...\n(수집 → 작성)")

    result = await asyncio.to_thread(_run_full_pipeline)

    lines = ["🔄 <b>파이프라인 결과</b>\n"]
    if result["collect"]["success"]:
        lines.append(f"📥 수집: {result['collect']['collected']}건")
    else:
        lines.append(f"❌ 수집 실패: {result['collect'].get('error', '')[:100]}")

    if result["write"]["success"]:
        lines.append(f"✍️ 작성: {result['write']['written']}건 성공 / {result['write']['failed']}건 실패")
    else:
        lines.append(f"❌ 작성 실패: {result['write'].get('error', '')[:100]}")

    await msg.edit_text("\n".join(lines), reply_markup=_back_button(), parse_mode="HTML")


def _run_full_pipeline() -> dict:
    collect_result = _run_collect()
    write_result = _run_write_pending()
    return {"collect": collect_result, "write": write_result}


# ─── 공통 ───────────────────────────────────────────────

def _back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ 메인 메뉴", callback_data="cmd_back")]])


@authorized
async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📊 <b>The 4th Path 대시보드</b>\n\n작업을 선택하세요:",
        reply_markup=main_panel_keyboard(),
        parse_mode="HTML",
    )


# ─── 앱 구성 ────────────────────────────────────────────

def create_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    # 주제 입력 대화
    write_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_write_topic_start, pattern="^cmd_write_topic$")],
        states={
            WAITING_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic_received)],
            WAITING_CORNER: [CallbackQueryHandler(handle_corner_selected, pattern="^corner_")],
        },
        fallbacks=[CommandHandler("panel", cmd_panel)],
    )

    # 시나리오 대화
    scenario_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_scenario_format, pattern="^scenario_")],
        states={
            WAITING_SCENARIO_IDEA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_scenario_idea)],
        },
        fallbacks=[CommandHandler("panel", cmd_panel)],
    )

    # 명령
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("panel", cmd_panel))

    # 대화형 핸들러 (먼저 등록)
    app.add_handler(write_conv)
    app.add_handler(scenario_conv)

    # 콜백 핸들러
    app.add_handler(CallbackQueryHandler(handle_collect, pattern="^cmd_collect$"))
    app.add_handler(CallbackQueryHandler(handle_write_menu, pattern="^cmd_write_menu$"))
    app.add_handler(CallbackQueryHandler(handle_write_pending, pattern="^cmd_write_pending$"))
    app.add_handler(CallbackQueryHandler(handle_publish_menu, pattern="^cmd_publish_menu$"))
    app.add_handler(CallbackQueryHandler(handle_publish_all, pattern="^cmd_publish_all$"))
    app.add_handler(CallbackQueryHandler(handle_approve, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(handle_status, pattern="^cmd_status$"))
    app.add_handler(CallbackQueryHandler(handle_scenario_menu, pattern="^cmd_scenario_menu$"))
    app.add_handler(CallbackQueryHandler(handle_settings, pattern="^cmd_settings$"))
    app.add_handler(CallbackQueryHandler(handle_full_pipeline, pattern="^cmd_full_pipeline$"))
    app.add_handler(CallbackQueryHandler(handle_back, pattern="^cmd_back$"))

    return app
