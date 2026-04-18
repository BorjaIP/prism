"""CLI entrypoint for Prism."""

from __future__ import annotations

import re
from typing import Optional

import typer

app = typer.Typer(
    name="prism",
    help="Terminal UI for reviewing GitHub PRs.",
    no_args_is_help=True,
)

_GITHUB_PR_URL_RE = re.compile(
    r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)"
)


def _parse_github_url(url: str) -> tuple[str, int] | None:
    """Return (owner/repo, pr_number) if *url* is a GitHub PR URL, else None."""
    m = _GITHUB_PR_URL_RE.match(url.rstrip("/"))
    if m:
        return m.group(1), int(m.group(2))
    return None


@app.command()
def review(
    repo_or_url: str = typer.Argument(
        help="Repository in 'owner/repo' format, or a GitHub PR URL"
    ),
    pr_number: Optional[int] = typer.Argument(
        default=None, help="Pull request number (not needed when passing a URL)"
    ),
) -> None:
    """Open a PR for review in the terminal UI."""
    from prism.app import PRismApp
    from prism.services.github import fetch_pr

    parsed = _parse_github_url(repo_or_url)
    if parsed:
        repo, pr_number = parsed
    else:
        repo = repo_or_url
        if pr_number is None:
            typer.echo(
                "Error: pr_number is required when not passing a GitHub URL.", err=True
            )
            raise typer.Exit(code=1)

    typer.echo(f"Fetching PR #{pr_number} from {repo}...")

    try:
        pr = fetch_pr(repo, pr_number)
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.echo(f"Failed to fetch PR: {e}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Loaded: {pr.title} ({len(pr.files)} files)")

    tui = PRismApp(pr, repo, pr_number)
    tui.run()


if __name__ == "__main__":
    app()
