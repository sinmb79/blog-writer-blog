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
