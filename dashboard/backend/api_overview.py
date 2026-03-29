from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter

from bots.blog_config import DATA_DIR, LOG_DIR, load_settings


load_settings()

router = APIRouter()

PIPELINE_STEPS = (
    ("collector", "Collect"),
    ("writer", "Write"),
    ("review", "Review"),
    ("publisher", "Publish"),
)


def _load_json_files(folder: Path) -> list[dict]:
    records: list[dict] = []
    if not folder.exists():
        return records
    for path in sorted(folder.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return records


def _published_counts() -> dict:
    records = _load_json_files(DATA_DIR / "published")
    today = date.today()
    week_start = today.toordinal() - today.weekday()
    today_count = 0
    week_count = 0
    for record in records:
        published_at = record.get("published_at", "")
        if not published_at:
            continue
        try:
            published_date = datetime.fromisoformat(published_at[:19]).date()
        except ValueError:
            continue
        if published_date == today:
            today_count += 1
        if published_date.toordinal() >= week_start:
            week_count += 1
    return {
        "today": today_count,
        "this_week": week_count,
        "total": len(records),
        "pending_review": len(list((DATA_DIR / "pending_review").glob("*.json"))),
        "drafts": len(list((DATA_DIR / "originals").glob("*.json"))),
    }


def _latest_log_time(path: Path) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
    for line in reversed(lines):
        match = pattern.search(line)
        if match:
            return match.group(1)[11:16]
    return ""


def _pipeline() -> list[dict]:
    review_count = len(list((DATA_DIR / "pending_review").glob("*.json")))
    published_count = len(list((DATA_DIR / "published").glob("*.json")))
    steps = []
    for step_id, label in PIPELINE_STEPS:
        done_at = _latest_log_time(LOG_DIR / f"{step_id}.log")
        if step_id == "review":
            status = "running" if review_count else "waiting"
        elif step_id == "publisher":
            status = "done" if published_count else "waiting"
        else:
            status = "done" if done_at else "waiting"
        steps.append({"id": step_id, "name": label, "status": status, "done_at": done_at})
    return steps


def _activity_logs(limit: int = 20) -> list[dict]:
    entries: list[dict] = []
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})[,\.]?\d*\s+\[?(\w+)\]?\s+(.*)")
    for log_file in sorted(LOG_DIR.glob("*.log"), key=lambda item: item.stat().st_mtime, reverse=True):
        lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in reversed(lines):
            match = pattern.match(line.strip())
            if not match:
                continue
            entries.append(
                {
                    "time": match.group(1)[11:16],
                    "level": match.group(2).upper(),
                    "module": log_file.stem,
                    "message": match.group(3)[:140],
                }
            )
            if len(entries) >= limit:
                return entries
    return entries


@router.get("/overview")
async def get_overview():
    return {"kpi": _published_counts()}


@router.get("/pipeline")
async def get_pipeline():
    return {"steps": _pipeline()}


@router.get("/activity")
async def get_activity():
    return {"logs": _activity_logs()}
