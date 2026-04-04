import json
from pathlib import Path


def _article() -> dict:
    return {
        "title": "Platform launch",
        "meta": "Meta description",
        "slug": "platform-launch",
        "tags": ["AI"],
        "corner": "Insights",
        "body": "markdown body",
        "_html_content": "<h1>Platform launch</h1><p>content</p>",
        "sources": [
            {"url": "https://example.com/source-1", "title": "Source 1"},
            {"url": "https://example.com/source-2", "title": "Source 2"},
        ],
        "disclaimer": "",
        "quality_score": 100,
    }


def test_publish_routes_to_wordpress(monkeypatch):
    import bots.publisher_bot as publisher_bot

    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(publisher_bot, "publish_to_blogger", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(
        publisher_bot,
        "wp_publisher_bot",
        type("DummyWp", (), {"publish": staticmethod(lambda article: calls.append(("wordpress", article["title"])) or True)}),
        raising=False,
    )

    assert publisher_bot.publish(_article(), platform="wordpress") is True
    assert calls == [("wordpress", "Platform launch")]


def test_publish_routes_to_all_platforms(monkeypatch):
    import bots.publisher_bot as publisher_bot

    calls: list[str] = []

    monkeypatch.setattr(
        publisher_bot,
        "publish_to_blogger",
        lambda article, html_content, creds: calls.append("blogger") or {"id": "1", "url": "https://blogger.example/post/1"},
    )
    monkeypatch.setattr(publisher_bot, "get_google_credentials", lambda: object())
    monkeypatch.setattr(publisher_bot, "log_published", lambda *args, **kwargs: None)
    monkeypatch.setattr(publisher_bot, "submit_to_search_console", lambda *args, **kwargs: None)
    monkeypatch.setattr(publisher_bot, "send_telegram", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        publisher_bot,
        "wp_publisher_bot",
        type("DummyWp", (), {"publish": staticmethod(lambda article: calls.append("wordpress") or True)}),
        raising=False,
    )
    monkeypatch.setattr(
        publisher_bot,
        "naver_publisher_bot",
        type("DummyNaver", (), {"publish": staticmethod(lambda article: calls.append("naver") or True)}),
        raising=False,
    )

    assert publisher_bot.publish(_article(), platform="all") is True
    assert calls == ["blogger", "wordpress", "naver"]


def test_approve_pending_reuses_requested_platform(monkeypatch, tmp_path: Path):
    import bots.publisher_bot as publisher_bot

    calls: list[tuple[str, str]] = []

    pending_file = tmp_path / "20260405_000000_pending.json"
    article = _article() | {"_publish_platform": "wordpress"}
    pending_file.write_text(json.dumps(article, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        publisher_bot,
        "wp_publisher_bot",
        type("DummyWp", (), {"publish": staticmethod(lambda article: calls.append(("wordpress", article["title"])) or True)}),
        raising=False,
    )
    monkeypatch.setattr(publisher_bot, "publish_to_blogger", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(publisher_bot, "send_telegram", lambda *args, **kwargs: None)

    assert publisher_bot.approve_pending(str(pending_file)) is True
    assert calls == [("wordpress", "Platform launch")]
    assert not pending_file.exists()
