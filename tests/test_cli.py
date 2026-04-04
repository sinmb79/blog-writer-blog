from click.testing import CliRunner

from blogwriter.cli import app


def test_cli_exposes_blog_only_commands():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "write" in result.output
    assert "publish" in result.output
    assert "status" in result.output
    assert "shorts" not in result.output
    assert "distribute" not in result.output


def test_publish_command_accepts_platform_option(monkeypatch, tmp_path):
    draft = tmp_path / "draft.json"
    draft.write_text(
        '{"title":"CLI publish","body":"content","sources":[{"url":"https://example.com/1"},{"url":"https://example.com/2"}],"quality_score":100}',
        encoding="utf-8",
    )

    import bots.publisher_bot as publisher_bot

    calls = []
    monkeypatch.setattr(publisher_bot, "publish", lambda article, platform="blogger": calls.append((article["title"], platform)) or True)

    result = CliRunner().invoke(app, ["publish", "--file", str(draft), "--platform", "wordpress"])

    assert result.exit_code == 0
    assert calls == [("CLI publish", "wordpress")]
