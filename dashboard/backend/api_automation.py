from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from bots.blog_config import DATA_DIR, load_settings


load_settings()

router = APIRouter()


class WriteQueueRequest(BaseModel):
    limit: int = Field(default=3, ge=1, le=20)


def run_daily_pipeline_job() -> dict:
    from scripts.daily_pipeline import main

    main()
    return {"status": "completed"}


def run_write_queue_job(limit: int) -> dict:
    from bots.writer_bot import run_pending

    results = run_pending(limit=limit)
    return {
        "processed": len(results),
        "succeeded": sum(1 for item in results if item.get("success")),
        "failed": sum(1 for item in results if not item.get("success")),
        "results": results,
    }


def run_publish_queue_job() -> dict:
    from bots.publisher_bot import publish as publish_article

    draft_files = sorted((DATA_DIR / "originals").glob("*.json"))
    published = 0
    queued_for_review = 0
    failed = 0
    results: list[dict] = []

    for draft_file in draft_files:
        try:
            article = json.loads(draft_file.read_text(encoding="utf-8"))
            ok = publish_article(article)
            if ok:
                published += 1
            else:
                queued_for_review += 1
            results.append(
                {
                    "file": draft_file.name,
                    "success": ok,
                    "title": article.get("title", ""),
                }
            )
        except Exception as exc:
            failed += 1
            results.append({"file": draft_file.name, "success": False, "error": str(exc)})

    return {
        "processed": len(draft_files),
        "published": published,
        "queued_for_review": queued_for_review,
        "failed": failed,
        "results": results,
    }


def run_weekly_report_job() -> dict:
    from scripts.weekly_report import main

    main()
    return {"status": "completed"}


def run_monthly_reminder_job() -> dict:
    from scripts.monthly_reminder import main

    main()
    return {"status": "completed"}


def run_collect_topics_job() -> dict:
    """트렌드 수집 전용 — Trend Radar n8n 워크플로우에서 호출"""
    import glob as _glob
    from bots.collector_bot import run as collector_run

    before_count = len(list((DATA_DIR / "topics").glob("*.json"))) if (DATA_DIR / "topics").exists() else 0
    collector_run()
    after_count = len(list((DATA_DIR / "topics").glob("*.json"))) if (DATA_DIR / "topics").exists() else 0
    new_topics = after_count - before_count

    # 최근 저장된 토픽 최대 10개 반환
    topic_files = sorted((DATA_DIR / "topics").glob("*.json"), reverse=True)[:10] if (DATA_DIR / "topics").exists() else []
    top_topics = []
    for tf in topic_files:
        try:
            data = json.loads(tf.read_text(encoding="utf-8"))
            top_topics.append({
                "topic": data.get("topic", ""),
                "source": data.get("source", ""),
                "quality_score": data.get("quality_score", 0),
                "corner": data.get("corner", ""),
            })
        except Exception:
            pass

    return {
        "status": "completed",
        "new_topics": new_topics,
        "total_topics": after_count,
        "top_topics": top_topics,
    }


@router.post("/automation/collect-topics")
async def run_collect_topics():
    return {"success": True, "job": "collect-topics", "result": run_collect_topics_job()}


@router.post("/automation/daily-pipeline")
async def run_daily_pipeline():
    return {"success": True, "job": "daily-pipeline", "result": run_daily_pipeline_job()}


@router.post("/automation/write-queue")
async def run_write_queue(req: WriteQueueRequest):
    return {
        "success": True,
        "job": "write-queue",
        "result": run_write_queue_job(limit=req.limit),
    }


@router.post("/automation/publish-queue")
async def run_publish_queue():
    return {"success": True, "job": "publish-queue", "result": run_publish_queue_job()}


@router.post("/automation/weekly-report")
async def run_weekly_report():
    return {"success": True, "job": "weekly-report", "result": run_weekly_report_job()}


@router.post("/automation/monthly-reminder")
async def run_monthly_reminder():
    return {
        "success": True,
        "job": "monthly-reminder",
        "result": run_monthly_reminder_job(),
    }
