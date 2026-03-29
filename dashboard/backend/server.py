from __future__ import annotations

from pathlib import Path

from runtime_guard import ensure_project_runtime


ensure_project_runtime("dashboard server", ["fastapi"])

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from dashboard.backend import api_connections, api_content, api_logs, api_overview, api_settings


app = FastAPI(title="Blog Writer Blog Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_overview.router, prefix="/api")
app.include_router(api_content.router, prefix="/api")
app.include_router(api_settings.router, prefix="/api")
app.include_router(api_connections.router, prefix="/api")
app.include_router(api_logs.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "blog-writer-blog"}


FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"status": "frontend not built", "hint": "run npm run build inside dashboard/frontend"}
