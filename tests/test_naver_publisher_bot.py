from pathlib import Path


def test_resolve_representative_image_prefers_existing_file(monkeypatch):
    import bots.naver_publisher_bot as naver_publisher_bot

    image_path = Path("data/images/test_naver_cover.png")
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"image")

    banana_calls = []
    openai_calls = []

    monkeypatch.setattr(
        naver_publisher_bot,
        "_generate_bananapro_image",
        lambda article: banana_calls.append(article["title"]) or None,
    )
    monkeypatch.setattr(
        naver_publisher_bot,
        "_generate_openai_image",
        lambda article: openai_calls.append(article["title"]) or None,
    )

    try:
        article = {"title": "Naver launch", "image_path": str(image_path)}

        assert naver_publisher_bot._resolve_representative_image(article) == str(image_path)
        assert banana_calls == []
        assert openai_calls == []
    finally:
        image_path.unlink(missing_ok=True)


def test_resolve_representative_image_falls_back_from_bananapro_to_openai(monkeypatch):
    import bots.naver_publisher_bot as naver_publisher_bot

    banana_calls = []
    openai_calls = []

    monkeypatch.setattr(naver_publisher_bot, "BANANAPRO_API_KEY", "banana-key")
    monkeypatch.setattr(naver_publisher_bot, "BANANAPRO_API_URL", "https://banana.example/api")
    monkeypatch.setattr(
        naver_publisher_bot,
        "_generate_bananapro_image",
        lambda article: banana_calls.append(article["title"]) or None,
    )
    monkeypatch.setattr(
        naver_publisher_bot,
        "_generate_openai_image",
        lambda article: openai_calls.append(article["title"]) or "generated/openai.png",
    )

    article = {"title": "Naver launch"}

    assert naver_publisher_bot._resolve_representative_image(article) == "generated/openai.png"
    assert banana_calls == ["Naver launch"]
    assert openai_calls == ["Naver launch"]


def test_publish_retries_transient_failures_then_succeeds(monkeypatch):
    import bots.naver_publisher_bot as naver_publisher_bot

    attempts = {"count": 0}
    alerts = []

    monkeypatch.setattr(naver_publisher_bot, "_ensure_credentials", lambda: True)
    monkeypatch.setattr(naver_publisher_bot, "_sleep", lambda seconds: None)
    monkeypatch.setattr(naver_publisher_bot, "send_telegram", lambda message, *args, **kwargs: alerts.append(message))

    def fake_publish_once(article):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary editor failure")
        return "https://blog.naver.com/example/1"

    monkeypatch.setattr(naver_publisher_bot, "_publish_once", fake_publish_once)

    article = {
        "title": "Naver launch",
        "sources": [
            {"url": "https://example.com/1", "title": "Source 1"},
            {"url": "https://example.com/2", "title": "Source 2"},
        ],
        "quality_score": 100,
    }

    assert naver_publisher_bot.publish(article) is True
    assert attempts["count"] == 3
    assert all("failed" not in alert.lower() for alert in alerts)


def test_publish_alerts_when_retries_are_exhausted(monkeypatch):
    import bots.naver_publisher_bot as naver_publisher_bot

    alerts = []

    monkeypatch.setattr(naver_publisher_bot, "_ensure_credentials", lambda: True)
    monkeypatch.setattr(naver_publisher_bot, "_sleep", lambda seconds: None)
    monkeypatch.setattr(naver_publisher_bot, "send_telegram", lambda message, *args, **kwargs: alerts.append(message))
    monkeypatch.setattr(
        naver_publisher_bot,
        "_publish_once",
        lambda article: (_ for _ in ()).throw(RuntimeError("still failing")),
    )

    article = {
        "title": "Naver launch",
        "sources": [
            {"url": "https://example.com/1", "title": "Source 1"},
            {"url": "https://example.com/2", "title": "Source 2"},
        ],
        "quality_score": 100,
    }

    assert naver_publisher_bot.publish(article) is False
    assert alerts
    assert "Naver publish failed" in alerts[-1]
