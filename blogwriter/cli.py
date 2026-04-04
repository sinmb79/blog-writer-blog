"""
Standalone blog-only CLI.
"""
from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from bots.blog_config import DATA_DIR, PROJECT_ROOT, load_settings
from bots.engine_loader import EngineLoader


load_settings()

console = Console()


def _json_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(folder.glob("*.json"))


@click.group()
def app():
    """Blog Writer Blog CLI."""


@app.command()
def collect():
    """Collect candidate topics."""
    from bots.collector_bot import run

    results = run()
    console.print(f"[green]Collected[/green] {len(results)} candidate topics")


@app.command()
@click.argument("topic", required=False)
@click.option("--publish-now", is_flag=True, help="Publish the generated article immediately.")
@click.option(
    "--platform",
    type=click.Choice(["blogger", "wordpress", "both", "naver", "all"], case_sensitive=False),
    default="blogger",
    show_default=True,
    help="Publishing target(s) when --publish-now is used.",
)
def write(topic: str | None, publish_now: bool, platform: str):
    """Generate articles from a topic or from queued items."""
    from bots.publisher_bot import publish
    from bots.writer_bot import run_from_topic, run_pending

    if topic:
        article = run_from_topic(topic)
        console.print(f"[green]Draft created[/green] {article.get('title', topic)}")
        if publish_now:
            published = publish(article, platform=platform)
            console.print("[green]Published[/green]" if published else "[yellow]Queued for review[/yellow]")
        return

    results = run_pending()
    ok = sum(1 for item in results if item.get("success"))
    console.print(f"[green]Generated[/green] {ok} article(s)")


@app.command()
@click.option("--file", "file_path", type=click.Path(exists=True, path_type=Path), help="Publish one article JSON file.")
@click.option(
    "--platform",
    type=click.Choice(["blogger", "wordpress", "both", "naver", "all"], case_sensitive=False),
    default="blogger",
    show_default=True,
    help="Publishing target(s).",
)
def publish(file_path: Path | None, platform: str):
    """Publish article drafts to the selected platform(s)."""
    from bots.publisher_bot import publish as publish_article

    draft_files = [file_path] if file_path else _json_files(DATA_DIR / "originals")
    if not draft_files:
        console.print("[yellow]No draft files found.[/yellow]")
        return

    published = 0
    for draft in draft_files:
        article = json.loads(draft.read_text(encoding="utf-8"))
        if publish_article(article, platform=platform):
            published += 1

    console.print(f"[green]Published[/green] {published} article(s)")


@app.group()
def review():
    """Manage pending review items."""


@review.command("list")
def review_list():
    from bots.publisher_bot import get_pending_list

    items = get_pending_list()
    table = Table(title="Pending Review")
    table.add_column("File")
    table.add_column("Title")
    table.add_column("Reason")
    for item in items:
        table.add_row(
            Path(item.get("_filepath", "")).name,
            item.get("title", ""),
            item.get("pending_reason", ""),
        )
    console.print(table)


@review.command("approve")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
def review_approve(file_path: Path):
    from bots.publisher_bot import approve_pending

    ok = approve_pending(str(file_path))
    console.print("[green]Approved and published[/green]" if ok else "[red]Approve failed[/red]")


@review.command("reject")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
def review_reject(file_path: Path):
    from bots.publisher_bot import reject_pending

    reject_pending(str(file_path))
    console.print("[yellow]Rejected[/yellow]")


@app.command()
def status():
    """Show blog pipeline status."""
    table = Table(title="Blog Status")
    table.add_column("Area")
    table.add_column("Count", justify="right")

    for label, folder in (
        ("Topics", DATA_DIR / "topics"),
        ("Collected", DATA_DIR / "collected"),
        ("Drafts", DATA_DIR / "originals"),
        ("Pending Review", DATA_DIR / "pending_review"),
        ("Published", DATA_DIR / "published"),
    ):
        table.add_row(label, str(len(_json_files(folder))))

    table.add_row("Writing Provider", str(EngineLoader().get_config("writing", "provider") or "openclaw"))
    console.print(table)


@app.command()
def doctor():
    """Show runtime prerequisites."""
    from os import environ

    table = Table(title="Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    checks = [
        (".env", (PROJECT_ROOT / ".env").exists(), str(PROJECT_ROOT / ".env")),
        ("engine.json", (PROJECT_ROOT / "config" / "engine.json").exists(), "config/engine.json"),
        ("BLOG_MAIN_ID", bool(environ.get("BLOG_MAIN_ID")), "Blogger blog id"),
        ("token.json", (PROJECT_ROOT / "token.json").exists(), "Google OAuth token"),
    ]
    for name, ok, detail in checks:
        table.add_row(name, "OK" if ok else "Missing", detail)
    console.print(table)


@app.group()
def config():
    """Inspect configuration."""


@config.command("show")
def config_show():
    loader = EngineLoader()
    console.print_json(json.dumps({"writing": loader.get_config("writing")}, ensure_ascii=False))


@app.command()
def server():
    """Show how to start the dashboard server."""
    console.print(
        f"Run with: [bold]{click.format_filename(PROJECT_ROOT / 'dashboard' / 'backend' / 'server.py')}[/bold]\n"
        "Example: python -m uvicorn dashboard.backend.server:app --port 8080 --reload"
    )


if __name__ == "__main__":
    app()
