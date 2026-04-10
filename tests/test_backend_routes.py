from fastapi.testclient import TestClient

import dashboard.backend.api_automation as api_automation
from dashboard.backend.server import app


def test_backend_exposes_only_blog_api_modules():
    paths = {route.path for route in app.routes}
    assert "/api/content" in paths
    assert "/api/settings" in paths
    assert "/api/logs" in paths
    assert "/api/automation/daily-pipeline" in paths
    assert "/api/automation/write-queue" in paths
    assert "/api/automation/publish-queue" in paths
    assert "/api/automation/weekly-report" in paths
    assert "/api/automation/monthly-reminder" in paths
    assert "/api/analytics" not in paths
    assert "/api/assist/sessions" not in paths


def test_daily_pipeline_route_runs_host_pipeline(monkeypatch):
    client = TestClient(app)
    calls: list[str] = []

    def fake_daily_pipeline():
        calls.append("daily")
        return {"mode": "live", "ok": True}

    monkeypatch.setattr(api_automation, "run_daily_pipeline_job", fake_daily_pipeline)

    response = client.post("/api/automation/daily-pipeline")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "job": "daily-pipeline",
        "result": {"mode": "live", "ok": True},
    }
    assert calls == ["daily"]
