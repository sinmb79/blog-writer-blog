from dashboard.backend.server import app


def test_backend_exposes_only_blog_api_modules():
    paths = {route.path for route in app.routes}
    assert "/api/content" in paths
    assert "/api/settings" in paths
    assert "/api/logs" in paths
    assert "/api/analytics" not in paths
    assert "/api/assist/sessions" not in paths
