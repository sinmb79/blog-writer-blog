from pathlib import Path


def test_expected_directories_exist():
    root = Path(__file__).resolve().parents[1]
    for rel in ["blogwriter", "bots", "dashboard", "config", "data", "logs", "templates"]:
        assert (root / rel).exists(), f"missing {rel}"


def test_n8n_setup_assets_exist():
    root = Path(__file__).resolve().parents[1]
    expected_files = [
        "setup.sh",
        "setup.bat",
        "n8n-workflows/blog-daily-pipeline.json",
        "n8n-workflows/blog-write-queue.json",
        "n8n-workflows/blog-publish-queue.json",
        "n8n-workflows/blog-weekly-report.json",
        "n8n-workflows/blog-monthly-reminder.json",
    ]
    for rel in expected_files:
        assert (root / rel).exists(), f"missing {rel}"

    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "setup.sh" in readme
    assert "setup.bat" in readme
    assert "http://localhost:5678" in readme
