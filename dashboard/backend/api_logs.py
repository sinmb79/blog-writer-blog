from __future__ import annotations

import re

from fastapi import APIRouter, Query

from bots.blog_config import LOG_DIR, load_settings


load_settings()

router = APIRouter()

LOG_MODULES = {
    "": "All",
    "collector": "Collector",
    "writer": "Writer",
    "publisher": "Publisher",
    "error": "Errors",
}

LOG_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})[,\.]?\d*\s+\[?(\w+)\]?\s+(.*)"
)


def _read_logs(filter_module: str = "", search: str = "", limit: int = 200) -> list[dict]:
    entries: list[dict] = []
    error_only = filter_module == "error"

    for log_file in sorted(LOG_DIR.glob("*.log"), key=lambda item: item.stat().st_mtime, reverse=True):
        module_name = log_file.stem
        if filter_module and not error_only and module_name != filter_module:
            continue
        lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in reversed(lines):
            match = LOG_PATTERN.match(line.strip())
            if not match:
                continue
            level = match.group(2).upper()
            message = match.group(3)
            if error_only and level not in {"ERROR", "CRITICAL", "WARNING"}:
                continue
            if search and search.lower() not in message.lower():
                continue
            entries.append(
                {
                    "time": match.group(1),
                    "level": level,
                    "module": module_name,
                    "message": message[:300],
                }
            )
            if len(entries) >= limit:
                return entries
    return entries


@router.get("/logs")
async def get_logs(
    filter: str = Query(default=""),
    search: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=500),
):
    logs = _read_logs(filter_module=filter, search=search, limit=limit)
    return {"logs": logs, "total": len(logs), "modules": LOG_MODULES}
