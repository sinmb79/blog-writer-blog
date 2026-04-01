"""
Telegram 대시보드 봇 (bots/telegram_dashboard.py)
BonkBot 스타일 인라인 키보드로 블로그+미디어 파이프라인을 제어한다.

실행: python scripts/start_dashboard.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
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
(
    WAITING_TOPIC, WAITING_CORNER,
    WAITING_SCENARIO_IDEA, WAITING_SCENARIO_FORMAT,
    WAITING_MF_IMAGE_PROMPT, WAITING_MF_VIDEO_DESC, WAITING_MF_TTS_TEXT,
    WAITING_MF_INGEST_PATH,
) = range(8)

MEDIAFORGE_DIR = Path(os.getenv("MEDIAFORGE_DIR", r"C:\Users\sinmb\workspace\mediaforge"))


# ═══════════════════════════════════════════════════════════
#  접근 제어
# ═══════════════════════════════════════════════════════════

def authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
            await update.effective_message.reply_text("Access denied.")
            return
        return await func(update, context)
    return wrapper


def _back(target: str = "cmd_back") -> InlineKeyboardMarkup:
    label = "main" if target == "cmd_back" else target.replace("cmd_", "")
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"<< {label}", callback_data=target)]])


# ═══════════════════════════════════════════════════════════
#  메인 패널
# ═══════════════════════════════════════════════════════════

def main_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("-- Blog --", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("Collect", callback_data="cmd_collect"),
            InlineKeyboardButton("Write", callback_data="cmd_write_menu"),
            InlineKeyboardButton("Publish", callback_data="cmd_publish_menu"),
        ],
        [
            InlineKeyboardButton("-- Content --", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("Scenario", callback_data="cmd_scenario_menu"),
            InlineKeyboardButton("Articles", callback_data="cmd_articles"),
            InlineKeyboardButton("Scenarios", callback_data="cmd_scenario_list"),
        ],
        [
            InlineKeyboardButton("-- Media (Forge) --", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("Doctor", callback_data="cmd_mf_doctor"),
            InlineKeyboardButton("Characters", callback_data="cmd_mf_characters"),
            InlineKeyboardButton("Ingest", callback_data="cmd_mf_ingest"),
        ],
        [
            InlineKeyboardButton("Image", callback_data="cmd_mf_image"),
            InlineKeyboardButton("Video", callback_data="cmd_mf_video"),
            InlineKeyboardButton("TTS", callback_data="cmd_mf_tts"),
        ],
        [
            InlineKeyboardButton("-- System --", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("Status", callback_data="cmd_status"),
            InlineKeyboardButton("Agents", callback_data="cmd_agents"),
            InlineKeyboardButton("Logs", callback_data="cmd_logs"),
        ],
        [
            InlineKeyboardButton("Cron", callback_data="cmd_cron"),
            InlineKeyboardButton("Disk", callback_data="cmd_disk"),
            InlineKeyboardButton("Settings", callback_data="cmd_settings"),
        ],
        [
            InlineKeyboardButton(">> Full Pipeline <<", callback_data="cmd_full_pipeline"),
        ],
    ])


MAIN_HEADER = "<b>The 4th Path Dashboard</b>\n"


@authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MAIN_HEADER, reply_markup=main_panel_keyboard(), parse_mode="HTML")


@authorized
async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


@authorized
async def handle_noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


@authorized
async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(MAIN_HEADER, reply_markup=main_panel_keyboard(), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════
#  수집 (Collect)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("Collecting topics...")
    result = await asyncio.to_thread(_run_collect)
    if result["success"]:
        text = f"<b>Collect Done</b>\n  Pass: {result['collected']}\n  Discard: {result.get('discarded', 0)}"
    else:
        text = f"Collect FAILED: {result.get('error', '')[:200]}"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")


def _run_collect() -> dict:
    try:
        from bots.collector_bot import run as collector_run
        passed = collector_run()
        return {"success": True, "collected": len(passed) if passed else 0}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#  작성 (Write)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_write_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    today = datetime.now().strftime("%Y%m%d")
    topics_dir = DATA_DIR / "topics"
    n = len(list(topics_dir.glob(f"{today}_*.json"))) if topics_dir.exists() else 0

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Batch Write ({n} pending)", callback_data="cmd_write_pending")],
        [InlineKeyboardButton("Direct Topic Input", callback_data="cmd_write_topic")],
        [InlineKeyboardButton("<< main", callback_data="cmd_back")],
    ])
    await query.edit_message_text("<b>Write</b>", reply_markup=kb, parse_mode="HTML")


@authorized
async def handle_write_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("Writing pending topics (max 3)...")
    result = await asyncio.to_thread(_run_write_pending)
    if result["success"]:
        text = f"<b>Write Done</b>\n  OK: {result['written']} / Fail: {result['failed']}"
    else:
        text = f"Write FAILED: {result.get('error', '')[:200]}"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")


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
    await query.edit_message_text("Type your topic:")
    return WAITING_TOPIC


@authorized
async def handle_topic_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pending_topic"] = update.message.text
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(c, callback_data=f"corner_{c}") for c in ["쉬운세상", "숨은보물"]],
        [InlineKeyboardButton(c, callback_data=f"corner_{c}") for c in ["바이브리포트", "팩트체크"]],
        [InlineKeyboardButton("한컷", callback_data="corner_한컷")],
    ])
    await update.message.reply_text("Select corner:", reply_markup=kb)
    return WAITING_CORNER


@authorized
async def handle_corner_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    corner = query.data.replace("corner_", "")
    topic = context.user_data.pop("pending_topic", "")
    msg = await query.edit_message_text(f"Writing...\n{topic} [{corner}]")
    result = await asyncio.to_thread(_run_write_topic, topic, corner)
    if result["success"]:
        text = f"<b>Write Done</b>\n  Title: {result['title']}\n  Corner: {corner}"
    else:
        text = f"Write FAILED: {result.get('error', '')[:200]}"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")
    return ConversationHandler.END


def _run_write_topic(topic: str, corner: str) -> dict:
    try:
        from bots.writer_bot import run_from_topic
        a = run_from_topic(topic, corner=corner)
        return {"success": True, "title": a.get("title", "")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════
#  발행 (Publish)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_publish_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pending = _get_pending_list()

    buttons = []
    for i, p in enumerate(pending[:5]):
        t = p.get("title", "?")[:25]
        r = p.get("pending_reason", "")[:15]
        buttons.append([InlineKeyboardButton(f"[OK] {t} ({r})", callback_data=f"approve_{i}")])

    if pending:
        buttons.append([InlineKeyboardButton("Reject All", callback_data="cmd_reject_all")])

    buttons.append([InlineKeyboardButton("Auto-Publish (safe only)", callback_data="cmd_publish_all")])
    buttons.append([InlineKeyboardButton("<< main", callback_data="cmd_back")])

    context.user_data["pending_files"] = [p.get("_filepath", "") for p in pending[:5]]
    count_text = f"{len(pending)} pending" if pending else "No pending"
    await query.edit_message_text(f"<b>Publish</b> ({count_text})", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@authorized
async def handle_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.replace("approve_", ""))
    files = context.user_data.get("pending_files", [])
    filepath = files[idx] if idx < len(files) else ""
    if not filepath:
        await query.edit_message_text("File not found.", reply_markup=_back())
        return
    msg = await query.edit_message_text("Publishing...")
    ok = await asyncio.to_thread(_run_approve, filepath)
    await msg.edit_text("<b>Published!</b>" if ok else "Publish FAILED.", reply_markup=_back(), parse_mode="HTML")


@authorized
async def handle_reject_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    files = context.user_data.get("pending_files", [])
    for fp in files:
        try:
            from bots.publisher_bot import reject_pending
            await asyncio.to_thread(reject_pending, fp)
        except Exception:
            pass
    await query.edit_message_text(f"Rejected {len(files)} articles.", reply_markup=_back())


@authorized
async def handle_publish_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("Auto-publishing safe originals...")
    result = await asyncio.to_thread(_run_publish_originals)
    await msg.edit_text(f"<b>Publish Result</b>\n  OK: {result['ok']} / Review: {result['review']}", reply_markup=_back(), parse_mode="HTML")


def _run_approve(fp: str) -> bool:
    try:
        from bots.publisher_bot import approve_pending
        return approve_pending(fp)
    except Exception:
        return False


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


# ═══════════════════════════════════════════════════════════
#  원고 목록 (Articles)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_articles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    originals = sorted((DATA_DIR / "originals").glob("*.json"), reverse=True)[:8]
    lines = ["<b>Recent Articles</b>\n"]
    for f in originals:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            title = d.get("title", "?")[:30]
            corner = d.get("corner", "")
            issues = d.get("quality_issues", [])
            flag = " !!" if issues else ""
            lines.append(f"  [{corner}] {title}{flag}")
        except Exception:
            lines.append(f"  {f.name}")

    if not originals:
        lines.append("  (none)")

    await query.edit_message_text("\n".join(lines), reply_markup=_back(), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════
#  시나리오 (Scenario)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_scenario_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Short (30-60s)", callback_data="scenario_short_script"),
            InlineKeyboardButton("Long (3-10m)", callback_data="scenario_long_script"),
        ],
        [InlineKeyboardButton("Webtoon (4-8 panels)", callback_data="scenario_webtoon_scenario")],
        [InlineKeyboardButton("<< main", callback_data="cmd_back")],
    ])
    await query.edit_message_text("<b>Scenario</b>\nSelect format:", reply_markup=kb, parse_mode="HTML")


@authorized
async def handle_scenario_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fmt = query.data.replace("scenario_", "")
    context.user_data["scenario_format"] = fmt
    await query.edit_message_text(f"Type your idea ({fmt}):")
    return WAITING_SCENARIO_IDEA


@authorized
async def handle_scenario_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idea = update.message.text
    fmt = context.user_data.pop("scenario_format", "short_script")
    msg = await update.message.reply_text(f"Generating scenario [{fmt}]...")
    result = await asyncio.to_thread(_run_scenario, idea, fmt)
    if result["success"]:
        text = f"<b>Scenario Done</b>\n  Title: {result['title']}\n  Scenes: {result['scenes']}\n  ID: <code>{result['file']}</code>"
    else:
        text = f"Scenario FAILED: {result.get('error', '')[:200]}"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")
    return ConversationHandler.END


def _run_scenario(idea: str, fmt: str) -> dict:
    try:
        from bots.scenario_bot import generate_from_idea
        r = generate_from_idea(idea, fmt)
        return {"success": True, "title": r.get("title_ko", ""), "scenes": len(r.get("scenes", [])), "file": r.get("request_id", "")[:8]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@authorized
async def handle_scenario_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    scenarios = sorted((DATA_DIR / "scenarios").glob("*.json"), reverse=True)[:8]
    lines = ["<b>Recent Scenarios</b>\n"]
    for f in scenarios:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            title = d.get("title_ko", "?")[:25]
            fmt = d.get("format", "?")
            scenes = len(d.get("scenes", []))
            lines.append(f"  [{fmt}] {title} ({scenes} scenes)")
        except Exception:
            lines.append(f"  {f.name}")
    if not scenarios:
        lines.append("  (none)")
    await query.edit_message_text("\n".join(lines), reply_markup=_back(), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════
#  상태 (Status)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    s = await asyncio.to_thread(_get_status)

    text = (
        f"<b>System Status</b>\n\n"
        f"<b>Pipeline</b>\n"
        f"  Topics: {s['topics']}\n"
        f"  Originals: {s['originals']}\n"
        f"  Pending Review: {s['pending']}\n"
        f"  Published: {s['published']}\n"
        f"  Scenarios: {s['scenarios']}\n\n"
        f"<b>Health</b>\n"
        f"  Errors (today): {s['errors']}\n"
        f"  Token expiry: {s['token_expiry']}\n"
        f"  Published (7d): {s['published_7d']}"
    )
    await query.edit_message_text(text, reply_markup=_back(), parse_mode="HTML")


def _get_status() -> dict:
    counts = {}
    for folder in ["topics", "originals", "pending_review", "published", "scenarios"]:
        p = DATA_DIR / folder
        counts[folder] = len(list(p.glob("*.json"))) if p.exists() else 0

    errors = 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    for log_name in ["writer.log", "publisher.log", "collector.log"]:
        lp = LOG_DIR / log_name
        if lp.exists():
            try:
                for line in lp.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]:
                    if today_str in line and "[ERROR]" in line:
                        errors += 1
            except Exception:
                pass

    # published in last 7 days
    pub_7d = 0
    week_ago = datetime.now() - timedelta(days=7)
    pub_dir = DATA_DIR / "published"
    if pub_dir.exists():
        for f in pub_dir.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                pa = d.get("published_at", "")
                if pa and datetime.fromisoformat(pa.replace("Z", "+00:00")) > week_ago:
                    pub_7d += 1
            except Exception:
                pass

    token_expiry = "N/A"
    tp = BASE_DIR / "token.json"
    if tp.exists():
        try:
            token_expiry = json.loads(tp.read_text(encoding="utf-8")).get("expiry", "?")
        except Exception:
            pass

    return {
        "topics": counts.get("topics", 0),
        "originals": counts.get("originals", 0),
        "pending": counts.get("pending_review", 0),
        "published": counts.get("published", 0),
        "scenarios": counts.get("scenarios", 0),
        "errors": errors,
        "token_expiry": token_expiry,
        "published_7d": pub_7d,
    }


# ═══════════════════════════════════════════════════════════
#  에이전트 (Agents)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    result = await asyncio.to_thread(_get_agents)
    lines = ["<b>Agents</b>\n"]
    for a in result:
        emoji = a.get("emoji", "")
        name = a.get("name", a["id"])
        default = " [DEFAULT]" if a.get("default") else ""
        lines.append(f"  {emoji} {name} ({a['id']}){default}")
    await query.edit_message_text("\n".join(lines), reply_markup=_back(), parse_mode="HTML")


def _get_agents() -> list:
    try:
        out = subprocess.run(
            ["openclaw", "agents", "list", "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        )
        agents = json.loads(out.stdout)
        return [
            {"id": a["id"], "name": a.get("identityName", a["id"]), "emoji": a.get("identityEmoji", ""), "default": a.get("isDefault", False)}
            for a in agents
        ]
    except Exception:
        return [{"id": "error", "name": "Failed to list agents", "emoji": "", "default": False}]


# ═══════════════════════════════════════════════════════════
#  로그 (Logs)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Writer", callback_data="log_writer"),
            InlineKeyboardButton("Publisher", callback_data="log_publisher"),
            InlineKeyboardButton("Collector", callback_data="log_collector"),
        ],
        [
            InlineKeyboardButton("Dashboard", callback_data="log_dashboard"),
            InlineKeyboardButton("Pipeline", callback_data="log_pipeline"),
            InlineKeyboardButton("Scenario", callback_data="log_scenario"),
        ],
        [
            InlineKeyboardButton("Errors Only", callback_data="log_errors"),
        ],
        [InlineKeyboardButton("<< main", callback_data="cmd_back")],
    ])
    await query.edit_message_text("<b>Logs</b>\nSelect module:", reply_markup=kb, parse_mode="HTML")


@authorized
async def handle_log_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    module = query.data.replace("log_", "")

    if module == "errors":
        lines = ["<b>Recent Errors (all modules)</b>\n"]
        for log_name in ["writer.log", "publisher.log", "collector.log", "daily_pipeline.log", "scenario.log"]:
            lp = LOG_DIR / log_name
            if not lp.exists():
                continue
            try:
                for line in lp.read_text(encoding="utf-8", errors="replace").splitlines()[-100:]:
                    if "[ERROR]" in line:
                        lines.append(f"<code>{line[:80]}</code>")
            except Exception:
                pass
        if len(lines) == 1:
            lines.append("  No errors found.")
        text = "\n".join(lines[:20])  # max 20 lines
    else:
        log_map = {
            "writer": "writer.log", "publisher": "publisher.log",
            "collector": "collector.log", "dashboard": "telegram_dashboard.log",
            "pipeline": "daily_pipeline.log", "scenario": "scenario.log",
        }
        lp = LOG_DIR / log_map.get(module, f"{module}.log")
        if lp.exists():
            tail = lp.read_text(encoding="utf-8", errors="replace").splitlines()[-15:]
            body = "\n".join(f"<code>{l[:80]}</code>" for l in tail)
            text = f"<b>{module}.log</b> (last 15)\n\n{body}"
        else:
            text = f"{module}.log not found."

    await query.edit_message_text(text, reply_markup=_back("cmd_logs"), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════
#  Cron
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_cron(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    jobs = await asyncio.to_thread(_get_cron_jobs)

    buttons = []
    for j in jobs:
        status = "ON" if j["enabled"] else "OFF"
        action = "cron_disable" if j["enabled"] else "cron_enable"
        buttons.append([
            InlineKeyboardButton(f"{'*' if j['enabled'] else 'x'} {j['name']}", callback_data="noop"),
            InlineKeyboardButton(f"[{status}]", callback_data=f"{action}_{j['id'][:8]}"),
            InlineKeyboardButton("[RUN]", callback_data=f"cron_run_{j['id'][:8]}"),
        ])

    buttons.append([InlineKeyboardButton("<< main", callback_data="cmd_back")])

    lines = ["<b>Cron Jobs</b>\n"]
    for j in jobs:
        s = "ON" if j["enabled"] else "OFF"
        lines.append(f"  [{s}] {j['name']} — {j['schedule']}")

    context.user_data["cron_jobs"] = {j["id"][:8]: j["id"] for j in jobs}
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@authorized
async def handle_cron_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, short_id = query.data.rsplit("_", 1)
    full_id = context.user_data.get("cron_jobs", {}).get(short_id, "")
    if not full_id:
        await query.edit_message_text("Job not found.", reply_markup=_back("cmd_cron"))
        return

    cmd = "enable" if "enable" in action else "disable"
    await asyncio.to_thread(_cron_command, cmd, full_id)
    # refresh
    await handle_cron(update, context)


@authorized
async def handle_cron_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    short_id = query.data.replace("cron_run_", "")
    full_id = context.user_data.get("cron_jobs", {}).get(short_id, "")
    if not full_id:
        await query.edit_message_text("Job not found.", reply_markup=_back("cmd_cron"))
        return
    msg = await query.edit_message_text("Running cron job...")
    await asyncio.to_thread(_cron_command, "run", full_id)
    await msg.edit_text("Cron job triggered.", reply_markup=_back("cmd_cron"))


def _get_cron_jobs() -> list:
    try:
        out = subprocess.run(
            ["openclaw", "cron", "list", "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
        )
        raw = json.loads(out.stdout)
        if isinstance(raw, list):
            jobs = raw
        else:
            jobs = raw.get("jobs", [])
        return [
            {
                "id": j.get("id", ""),
                "name": j.get("name", j.get("id", "?")[:12]),
                "enabled": j.get("enabled", True),
                "schedule": j.get("schedule", {}).get("expr", "?"),
            }
            for j in jobs
        ]
    except Exception:
        return []


def _cron_command(cmd: str, job_id: str):
    try:
        subprocess.run(
            ["openclaw", "cron", cmd, job_id],
            capture_output=True, text=True, encoding="utf-8", timeout=15,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  디스크 (Disk)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_disk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    info = await asyncio.to_thread(_get_disk_info)
    lines = ["<b>Disk Usage</b>\n"]
    for name, size in info:
        lines.append(f"  {name}: {size}")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Clean Old Logs (30d+)", callback_data="cmd_clean_logs")],
        [InlineKeyboardButton("<< main", callback_data="cmd_back")],
    ])
    await query.edit_message_text("\n".join(lines), reply_markup=kb, parse_mode="HTML")


@authorized
async def handle_clean_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    count = await asyncio.to_thread(_clean_old_logs)
    await query.edit_message_text(f"Cleaned {count} old log entries.", reply_markup=_back("cmd_disk"))


def _get_disk_info() -> list:
    result = []
    for folder in ["topics", "originals", "published", "pending_review", "discarded", "scenarios"]:
        p = DATA_DIR / folder
        if p.exists():
            total = sum(f.stat().st_size for f in p.glob("*") if f.is_file())
            result.append((f"data/{folder}", _fmt_size(total)))
    if LOG_DIR.exists():
        total = sum(f.stat().st_size for f in LOG_DIR.glob("*") if f.is_file())
        result.append(("logs/", _fmt_size(total)))
    return result


def _fmt_size(b: int) -> str:
    if b < 1024: return f"{b}B"
    if b < 1024 * 1024: return f"{b // 1024}KB"
    return f"{b / (1024 * 1024):.1f}MB"


def _clean_old_logs() -> int:
    count = 0
    if LOG_DIR.exists():
        cutoff = datetime.now() - timedelta(days=30)
        for f in LOG_DIR.glob("*.log"):
            try:
                if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink()
                    count += 1
            except Exception:
                pass
    return count


# ═══════════════════════════════════════════════════════════
#  설정 (Settings)
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    engine_path = CONFIG_DIR / "engine.json"
    provider, agent_name = "?", "?"
    if engine_path.exists():
        try:
            cfg = json.loads(engine_path.read_text(encoding="utf-8"))
            provider = cfg.get("writing", {}).get("provider", "?")
            agent_name = cfg.get("writing", {}).get("options", {}).get(provider, {}).get("agent_name", "?")
        except Exception:
            pass

    persona_path = CONFIG_DIR / "persona.json"
    corners = []
    if persona_path.exists():
        try:
            p = json.loads(persona_path.read_text(encoding="utf-8"))
            corners = list(p.get("corners", {}).keys())
        except Exception:
            pass

    text = (
        f"<b>Settings</b>\n\n"
        f"Engine: {provider}\n"
        f"Agent: {agent_name}\n"
        f"Corners: {', '.join(corners)}\n"
        f"Project: {BASE_DIR}"
    )
    await query.edit_message_text(text, reply_markup=_back(), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════
#  MediaForge
# ═══════════════════════════════════════════════════════════

def _run_mf_cmd(*args: str) -> str:
    """mediaforge CLI 실행. 결과 텍스트 반환."""
    try:
        cmd = ["npm", "run", "engine", "--"] + list(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, cwd=str(MEDIAFORGE_DIR),
        )
        return result.stdout.strip() or result.stderr.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "TIMEOUT (120s)"
    except Exception as e:
        return f"ERROR: {e}"


@authorized
async def handle_mf_doctor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("Checking MediaForge backends...")
    output = await asyncio.to_thread(_run_mf_cmd, "doctor", "--json")
    # 요약 추출
    try:
        doc = json.loads(output)
        lines = ["<b>MediaForge Doctor</b>\n"]
        for name, info in doc.items():
            if isinstance(info, dict):
                ok = info.get("ok", info.get("available", False))
                lines.append(f"  {'OK' if ok else 'XX'} {name}")
            else:
                lines.append(f"  {name}: {info}")
        text = "\n".join(lines)
    except Exception:
        text = f"<b>MediaForge Doctor</b>\n\n<code>{output[:800]}</code>"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")


@authorized
async def handle_mf_characters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("Loading characters...")
    output = await asyncio.to_thread(_run_mf_cmd, "scenario", "character", "list", "--json")
    try:
        chars = json.loads(output)
        if not chars:
            text = "<b>Characters</b>\n\n  (none registered)"
        else:
            lines = ["<b>Characters</b>\n"]
            for c in (chars if isinstance(chars, list) else []):
                lines.append(f"  {c.get('name', '?')} ({c.get('type', '?')})")
            text = "\n".join(lines)
    except Exception:
        text = f"<b>Characters</b>\n\n<code>{output[:600]}</code>"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")


@authorized
async def handle_mf_ingest_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # 시나리오 파일 목록
    scenarios = sorted((DATA_DIR / "scenarios").glob("*.json"), reverse=True)[:6]
    if not scenarios:
        await query.edit_message_text("No scenarios found.", reply_markup=_back())
        return
    buttons = []
    for i, f in enumerate(scenarios):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            label = d.get("title_ko", f.name)[:30]
        except Exception:
            label = f.name[:30]
        buttons.append([InlineKeyboardButton(label, callback_data=f"mf_ingest_{i}")])
    buttons.append([InlineKeyboardButton("<< main", callback_data="cmd_back")])
    context.user_data["mf_scenario_files"] = [str(f) for f in scenarios]
    await query.edit_message_text("<b>Ingest Scenario</b>\nSelect:", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@authorized
async def handle_mf_ingest_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.replace("mf_ingest_", ""))
    files = context.user_data.get("mf_scenario_files", [])
    fpath = files[idx] if idx < len(files) else ""
    if not fpath:
        await query.edit_message_text("File not found.", reply_markup=_back())
        return
    msg = await query.edit_message_text(f"Ingesting scenario...\n{Path(fpath).name}")
    output = await asyncio.to_thread(_run_mf_cmd, "scenario", "ingest", fpath, "--simulate", "--json")
    text = f"<b>Ingest Result</b>\n\n<code>{output[:1000]}</code>"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")


@authorized
async def handle_mf_image_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Type English image prompt:")
    return WAITING_MF_IMAGE_PROMPT


@authorized
async def handle_mf_image_go(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    msg = await update.message.reply_text(f"Generating image...\n{prompt[:50]}")
    output = await asyncio.to_thread(
        _run_mf_cmd, "forge", "image", "generate",
        "--prompt", prompt, "--model", "sdxl", "--resolution", "1k", "--json",
    )
    try:
        data = json.loads(output)
        paths = data.get("output_paths", [])
        text = f"<b>Image Done</b>\n  Files: {len(paths)}\n  Path: <code>{paths[0] if paths else '?'}</code>"
    except Exception:
        text = f"<b>Image Result</b>\n\n<code>{output[:600]}</code>"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")
    return ConversationHandler.END


@authorized
async def handle_mf_video_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Type scene description (Korean):")
    return WAITING_MF_VIDEO_DESC


@authorized
async def handle_mf_video_go(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text
    msg = await update.message.reply_text(f"Generating video...\n{desc[:50]}")
    output = await asyncio.to_thread(
        _run_mf_cmd, "forge", "video", "from-text",
        "--desc", desc, "--model", "wan22", "--quality", "draft", "--json",
    )
    try:
        data = json.loads(output)
        text = f"<b>Video Done</b>\n  Path: <code>{data.get('output_path', '?')}</code>"
    except Exception:
        text = f"<b>Video Result</b>\n\n<code>{output[:600]}</code>"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")
    return ConversationHandler.END


@authorized
async def handle_mf_tts_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Type narration text (Korean):")
    return WAITING_MF_TTS_TEXT


@authorized
async def handle_mf_tts_go(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_input = update.message.text
    msg = await update.message.reply_text(f"Generating TTS...\n{text_input[:50]}")
    output = await asyncio.to_thread(
        _run_mf_cmd, "forge", "audio", "tts",
        "--text", text_input, "--lang", "ko", "--json",
    )
    try:
        data = json.loads(output)
        text = f"<b>TTS Done</b>\n  Path: <code>{data.get('output_path', '?')}</code>"
    except Exception:
        text = f"<b>TTS Result</b>\n\n<code>{output[:600]}</code>"
    await msg.edit_text(text, reply_markup=_back(), parse_mode="HTML")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
#  전체 파이프라인
# ═══════════════════════════════════════════════════════════

@authorized
async def handle_full_pipeline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.edit_message_text("Running full pipeline (collect + write)...")
    result = await asyncio.to_thread(_run_full_pipeline)
    lines = ["<b>Pipeline Result</b>\n"]
    c = result["collect"]
    w = result["write"]
    lines.append(f"Collect: {'OK ' + str(c.get('collected', 0)) if c['success'] else 'FAIL'}")
    lines.append(f"Write: {'OK ' + str(w.get('written', 0)) + '/' + str(w.get('failed', 0)) if w['success'] else 'FAIL'}")
    await msg.edit_text("\n".join(lines), reply_markup=_back(), parse_mode="HTML")


def _run_full_pipeline() -> dict:
    return {"collect": _run_collect(), "write": _run_write_pending()}


# ═══════════════════════════════════════════════════════════
#  앱 구성
# ═══════════════════════════════════════════════════════════

def create_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handlers
    write_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_write_topic_start, pattern="^cmd_write_topic$")],
        states={
            WAITING_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic_received)],
            WAITING_CORNER: [CallbackQueryHandler(handle_corner_selected, pattern="^corner_")],
        },
        fallbacks=[CommandHandler("panel", cmd_panel)],
        per_message=False,
    )
    scenario_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_scenario_format, pattern="^scenario_")],
        states={
            WAITING_SCENARIO_IDEA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_scenario_idea)],
        },
        fallbacks=[CommandHandler("panel", cmd_panel)],
        per_message=False,
    )

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("panel", cmd_panel))

    # MediaForge conversations
    mf_image_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_mf_image_start, pattern="^cmd_mf_image$")],
        states={WAITING_MF_IMAGE_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mf_image_go)]},
        fallbacks=[CommandHandler("panel", cmd_panel)],
        per_message=False,
    )
    mf_video_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_mf_video_start, pattern="^cmd_mf_video$")],
        states={WAITING_MF_VIDEO_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mf_video_go)]},
        fallbacks=[CommandHandler("panel", cmd_panel)],
        per_message=False,
    )
    mf_tts_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_mf_tts_start, pattern="^cmd_mf_tts$")],
        states={WAITING_MF_TTS_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mf_tts_go)]},
        fallbacks=[CommandHandler("panel", cmd_panel)],
        per_message=False,
    )

    # Conversations (register first)
    app.add_handler(write_conv)
    app.add_handler(scenario_conv)
    app.add_handler(mf_image_conv)
    app.add_handler(mf_video_conv)
    app.add_handler(mf_tts_conv)

    # Callbacks
    callbacks = {
        "noop": handle_noop,
        "cmd_collect": handle_collect,
        "cmd_write_menu": handle_write_menu,
        "cmd_write_pending": handle_write_pending,
        "cmd_publish_menu": handle_publish_menu,
        "cmd_publish_all": handle_publish_all,
        "cmd_reject_all": handle_reject_all,
        "cmd_status": handle_status,
        "cmd_agents": handle_agents,
        "cmd_logs": handle_logs,
        "cmd_cron": handle_cron,
        "cmd_disk": handle_disk,
        "cmd_clean_logs": handle_clean_logs,
        "cmd_settings": handle_settings,
        "cmd_articles": handle_articles,
        "cmd_scenario_menu": handle_scenario_menu,
        "cmd_scenario_list": handle_scenario_list,
        "cmd_full_pipeline": handle_full_pipeline,
        "cmd_mf_doctor": handle_mf_doctor,
        "cmd_mf_characters": handle_mf_characters,
        "cmd_mf_ingest": handle_mf_ingest_start,
        "cmd_back": handle_back,
    }
    for pattern, handler in callbacks.items():
        app.add_handler(CallbackQueryHandler(handler, pattern=f"^{pattern}$"))

    # Dynamic callbacks
    app.add_handler(CallbackQueryHandler(handle_approve, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(handle_log_view, pattern="^log_"))
    app.add_handler(CallbackQueryHandler(handle_cron_toggle, pattern="^cron_(enable|disable)_"))
    app.add_handler(CallbackQueryHandler(handle_cron_run, pattern="^cron_run_"))
    app.add_handler(CallbackQueryHandler(handle_mf_ingest_run, pattern="^mf_ingest_"))

    return app
