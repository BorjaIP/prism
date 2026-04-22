"""Local review history — tracks PRs opened in Prism."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from prism.models import PRMetadata, PRSummary

HISTORY_PATH = Path.home() / ".config" / "prism" / "history.json"
_MAX_ENTRIES = 50


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _load_raw() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        with open(HISTORY_PATH) as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_to_history(pr: PRMetadata, repo_slug: str) -> None:
    """Record a PR as recently reviewed (called when a PR is opened).

    Keeps the most recent _MAX_ENTRIES entries, newest first.
    """
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    entries = _load_raw()

    # Remove any existing entry for the same PR so we can re-insert at top
    entries = [e for e in entries if not (e.get("repo_slug") == repo_slug and e.get("number") == pr.number)]

    entry = {
        "number": pr.number,
        "title": pr.title,
        "author": pr.author,
        "repo_slug": repo_slug,
        "state": pr.state,
        "base_branch": pr.base_branch,
        "head_branch": pr.head_branch,
        "review_state": pr.review_state,
        "checks_status": pr.checks_status,
        "html_url": pr.html_url,
        "body": pr.body[:500] if pr.body else "",  # truncate to save space
        "opened_at": _now_iso(),
        # updated_at used as sort key — use opened_at if not available
        "updated_at": _now_iso(),
    }
    entries.insert(0, entry)
    entries = entries[:_MAX_ENTRIES]

    with open(HISTORY_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def delete_from_history(repo_slug: str, pr_number: int) -> None:
    """Remove a specific PR entry from the local history file."""
    entries = _load_raw()
    entries = [
        e for e in entries
        if not (e.get("repo_slug") == repo_slug and e.get("number") == pr_number)
    ]
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def load_history() -> list[PRSummary]:
    """Return recently reviewed PRs as PRSummary objects, newest first."""
    entries = _load_raw()
    summaries: list[PRSummary] = []
    for e in entries:
        try:
            summaries.append(
                PRSummary(
                    number=e["number"],
                    title=e["title"],
                    author=e.get("author", "unknown"),
                    repo_slug=e["repo_slug"],
                    state=e.get("state", "open"),
                    base_branch=e.get("base_branch", ""),
                    head_branch=e.get("head_branch", ""),
                    review_state=e.get("review_state"),
                    checks_status=e.get("checks_status"),
                    updated_at=datetime.fromisoformat(e.get("opened_at", e.get("updated_at", _now_iso()))),
                    html_url=e.get("html_url", ""),
                    body=e.get("body", ""),
                    comments=e.get("comments", 0),
                )
            )
        except Exception:
            continue
    return summaries
