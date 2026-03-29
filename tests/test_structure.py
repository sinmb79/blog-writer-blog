from pathlib import Path


def test_expected_directories_exist():
    root = Path(__file__).resolve().parents[1]
    for rel in ["blogwriter", "bots", "dashboard", "config", "data", "logs", "templates"]:
        assert (root / rel).exists(), f"missing {rel}"
