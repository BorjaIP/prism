"""CLI entrypoint for Prism."""

from __future__ import annotations

import os
import re
from typing import Optional

import typer

app = typer.Typer(
    name="prism",
    help="Terminal UI for reviewing GitHub PRs.",
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
def main(
    repo_or_url: Optional[str] = typer.Argument(
        default=None,
        help="GitHub PR URL or 'owner/repo'. Omit to open the PR browser.",
    ),
    pr_number: Optional[int] = typer.Argument(
        default=None, help="PR number (only needed with 'owner/repo' format)."
    ),
) -> None:
    """Open the PR browser, optionally jumping straight to a specific PR."""
    from prism.app import PRismApp

    initial_repo: str | None = None
    initial_number: int | None = None

    if repo_or_url is not None:
        parsed = _parse_github_url(repo_or_url)
        if parsed:
            initial_repo, initial_number = parsed
        else:
            if pr_number is None:
                typer.echo(
                    "Error: pr_number is required when not passing a GitHub URL.", err=True
                )
                raise typer.Exit(code=1)
            initial_repo = repo_or_url
            initial_number = pr_number

    tui = PRismApp(initial_repo=initial_repo, initial_pr_number=initial_number)
    tui.run()
    # Force-exit: background GitHub/network threads are non-daemon and would
    # otherwise keep the process alive after the TUI closes.
    os._exit(0)


if __name__ == "__main__":
    app()
