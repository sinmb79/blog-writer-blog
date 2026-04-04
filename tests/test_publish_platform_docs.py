import json
from pathlib import Path


def test_platform_runtime_files_and_docs_are_present():
    root = Path(__file__).resolve().parents[1]

    env_example = (root / ".env.example").read_text(encoding="utf-8")
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    platforms = json.loads((root / "config" / "platforms.json").read_text(encoding="utf-8"))
    pytest_ini = (root / "pytest.ini").read_text(encoding="utf-8")

    assert "WP_URL=" in env_example
    assert "WP_APP_PASSWORD=" in env_example
    assert "NAVER_BLOG_ENABLED=" in env_example
    assert "BANANAPRO_API_KEY=" in env_example

    assert "wordpress" in platforms
    assert "naver" in platforms
    assert platforms["blogger"]["enabled"] is True

    assert ".pytest_tmp/" in gitignore
    assert "data/images/*" in gitignore
    assert "--basetemp=.pytest_tmp" in pytest_ini

    assert "WordPress" in readme
    assert "Naver" in readme
    assert "--platform" in readme
