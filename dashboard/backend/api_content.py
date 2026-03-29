from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bots.blog_config import DATA_DIR, load_settings


load_settings()

router = APIRouter()


class ManualWriteRequest(BaseModel):
    topic: str = ""
    limit: int = 3


def _folder_cards(folder: Path, status: str) -> list[dict]:
    cards: list[dict] = []
    if not folder.exists():
        return cards
    for path in sorted(folder.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        cards.append(
            {
                "id": path.stem,
                "file": str(path),
                "title": data.get("title") or data.get("topic") or path.stem,
                "corner": data.get("corner", ""),
                "source": data.get("source") or data.get("source_url", ""),
                "quality_score": data.get("quality_score", data.get("score", 0)),
                "created_at": data.get("created_at", data.get("published_at", "")),
                "status": status,
                "summary": data.get("summary") or data.get("meta") or data.get("body", "")[:200],
            }
        )
    return cards


def _pending_file(item_id: str) -> Path:
    candidate = DATA_DIR / "pending_review" / f"{item_id}.json"
    if candidate.exists():
        return candidate
    raise HTTPException(status_code=404, detail="Pending review file not found")


@router.get("/content")
async def get_content():
    return {
        "columns": {
            "queue": {"label": "Queue", "cards": _folder_cards(DATA_DIR / "topics", "queue") + _folder_cards(DATA_DIR / "collected", "queue")},
            "writing": {"label": "Drafts", "cards": _folder_cards(DATA_DIR / "originals", "writing")},
            "review": {"label": "Review", "cards": _folder_cards(DATA_DIR / "pending_review", "review")},
            "published": {"label": "Published", "cards": _folder_cards(DATA_DIR / "published", "published")[:20]},
        }
    }


@router.post("/content/{item_id}/approve")
async def approve_content(item_id: str):
    from bots.publisher_bot import approve_pending

    pending_file = _pending_file(item_id)
    success = approve_pending(str(pending_file))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to publish approved item")
    return {"success": True, "message": "Approved and published"}


@router.post("/content/{item_id}/reject")
async def reject_content(item_id: str):
    from bots.publisher_bot import reject_pending

    pending_file = _pending_file(item_id)
    reject_pending(str(pending_file))
    return {"success": True, "message": "Rejected"}


@router.post("/manual-write")
async def manual_write(req: ManualWriteRequest):
    from bots.collector_bot import run as collect_run
    from bots.writer_bot import run_from_topic, run_pending

    results: list[dict] = []
    if req.topic.strip():
        try:
            article = run_from_topic(req.topic.strip())
            results.append({"step": "writer", "success": True, "title": article.get("title", req.topic.strip())})
        except Exception as exc:
            results.append({"step": "writer", "success": False, "error": str(exc)})
        return {"results": results}

    try:
        collected = collect_run()
        results.append({"step": "collector", "success": True, "count": len(collected)})
    except Exception as exc:
        results.append({"step": "collector", "success": False, "error": str(exc)})
        return {"results": results}

    try:
        written = run_pending(limit=req.limit)
        results.append(
            {
                "step": "writer",
                "success": all(item.get("success") for item in written) if written else True,
                "count": sum(1 for item in written if item.get("success")),
            }
        )
    except Exception as exc:
        results.append({"step": "writer", "success": False, "error": str(exc)})

    return {"results": results}
