"""GitHub API service for fetching PR data."""

from __future__ import annotations

import os

from github import Github
from github.PullRequest import PullRequest

from prism.models import PRComment, PRFile, PRMetadata, PRReview, PRSummary


def _get_client() -> Github:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable is required. "
            "Create one at https://github.com/settings/tokens"
        )
    return Github(token)


def _issue_to_summary(issue) -> PRSummary | None:
    """Convert a search Issue to a PRSummary using only data already on the object.

    Deliberately avoids any extra API calls (no as_pull_request, get_reviews,
    get_combined_status) so that listing is fast regardless of result count.
    """
    try:
        repo_full_name = issue.repository.full_name
        pr_part = issue.pull_request  # PullRequestPart — always present on PR issues
        state = "merged" if (pr_part and pr_part.merged_at) else issue.state
        return PRSummary(
            number=issue.number,
            title=issue.title,
            author=issue.user.login if issue.user else "unknown",
            repo_slug=repo_full_name,
            state=state,
            base_branch="",
            head_branch="",
            review_state=None,
            checks_status=None,
            updated_at=issue.updated_at,
            html_url=issue.html_url,
            body=issue.body or "",
            comments=issue.comments,
        )
    except Exception:
        return None


def fetch_my_prs(state: str = "open") -> list[PRSummary]:
    """Fetch pull requests authored by the authenticated user (single search call)."""
    client = _get_client()
    results = client.search_issues(f"is:pr is:{state} author:@me sort:updated-desc")
    return [s for issue in results if (s := _issue_to_summary(issue)) is not None]


def fetch_review_requested() -> list[PRSummary]:
    """Fetch open PRs where the authenticated user is requested as reviewer (single search call)."""
    client = _get_client()
    results = client.search_issues("is:pr is:open review-requested:@me sort:updated-desc")
    return [s for issue in results if (s := _issue_to_summary(issue)) is not None]


def fetch_pr(repo_slug: str, pr_number: int) -> PRMetadata:
    """Fetch PR metadata and file list from GitHub.

    Args:
        repo_slug: Repository in 'owner/repo' format.
        pr_number: Pull request number.
    """
    client = _get_client()
    repo = client.get_repo(repo_slug)
    pr: PullRequest = repo.get_pull(pr_number)

    files = [
        PRFile(
            filename=f.filename,
            status=f.status,
            additions=f.additions,
            deletions=f.deletions,
            patch=f.patch or "",
            sha=f.sha,
        )
        for f in pr.get_files()
    ]

    review_comments = [
        PRComment(
            id=c.id,
            body=c.body,
            author=c.user.login if c.user else "unknown",
            created_at=c.created_at,
            path=c.path,
            line=c.line or c.original_line,
            in_reply_to_id=getattr(c, "in_reply_to_id", None),
            diff_hunk=c.diff_hunk,
            html_url=c.html_url,
        )
        for c in pr.get_review_comments()
    ]

    state = "merged" if pr.merged else pr.state

    checks_status: str | None = None
    try:
        combined = repo.get_commit(pr.head.sha).get_combined_status()
        checks_status = combined.state  # "success" | "failure" | "pending" | "error"
    except Exception:
        pass

    return PRMetadata(
        number=pr.number,
        title=pr.title,
        author=pr.user.login if pr.user else "unknown",
        state=state,
        base_branch=pr.base.ref,
        head_branch=pr.head.ref,
        files=files,
        body=pr.body or "",
        html_url=pr.html_url,
        head_sha=pr.head.sha,
        review_comments=review_comments,
        checks_status=checks_status,
    )


def post_comment(
    repo_slug: str,
    pr_number: int,
    commit_id: str,
    path: str,
    line: int,
    body: str,
) -> PRComment:
    """Post an inline review comment to a PR file at a specific line.

    Args:
        repo_slug: Repository in 'owner/repo' format.
        pr_number: Pull request number.
        commit_id: PR head commit SHA (pr.head.sha).
        path: File path relative to repo root.
        line: Right-side (new file) line number within the diff.
        body: Comment text.

    Raises:
        GithubException: On GitHub API errors (e.g. 422 if line not in diff).
        RuntimeError: If GITHUB_TOKEN is missing.
    """
    client = _get_client()
    repo = client.get_repo(repo_slug)
    pr = repo.get_pull(pr_number)
    comment = pr.create_review_comment(
        body=body,
        commit_id=commit_id,
        path=path,
        line=line,
    )
    return PRComment(
        id=comment.id,
        body=comment.body,
        author=comment.user.login if comment.user else "unknown",
        created_at=comment.created_at,
        path=comment.path,
        line=comment.line or line,
        in_reply_to_id=getattr(comment, "in_reply_to_id", None),
        diff_hunk=comment.diff_hunk,
        html_url=comment.html_url,
    )


def post_reply(
    repo_slug: str,
    pr_number: int,
    comment_id: int,
    body: str,
) -> PRComment:
    """Post an in-thread reply to an existing review comment.

    Args:
        repo_slug: Repository in 'owner/repo' format.
        pr_number: Pull request number.
        comment_id: ID of the parent comment to reply to.
        body: Reply text.

    Raises:
        GithubException: On GitHub API errors.
        RuntimeError: If GITHUB_TOKEN is missing.
    """
    client = _get_client()
    repo = client.get_repo(repo_slug)
    pr = repo.get_pull(pr_number)
    comment = pr.create_review_comment_reply(comment_id, body)
    return PRComment(
        id=comment.id,
        body=comment.body,
        author=comment.user.login if comment.user else "unknown",
        created_at=comment.created_at,
        path=comment.path,
        line=comment.line or 0,
        in_reply_to_id=getattr(comment, "in_reply_to_id", comment_id),
        diff_hunk=comment.diff_hunk,
        html_url=comment.html_url,
    )


def submit_review(
    repo_slug: str,
    pr_number: int,
    event: str,
    body: str = "",
) -> None:
    """Submit a PR review via the GitHub API.

    Args:
        repo_slug: Repository in 'owner/repo' format.
        pr_number: Pull request number.
        event: Review event — "APPROVE" or "REQUEST_CHANGES".
        body: Optional review message (required for REQUEST_CHANGES).

    Raises:
        GithubException: On GitHub API errors.
        RuntimeError: If GITHUB_TOKEN is missing.
    """
    client = _get_client()
    repo = client.get_repo(repo_slug)
    pr = repo.get_pull(pr_number)
    pr.create_review(body=body, event=event)


def fetch_comments(repo_slug: str, pr_number: int) -> list[PRComment]:
    """Fetch all inline review comments for the PR.

    Args:
        repo_slug: Repository in 'owner/repo' format.
        pr_number: Pull request number.
    """
    client = _get_client()
    repo = client.get_repo(repo_slug)
    pr = repo.get_pull(pr_number)

    return [
        PRComment(
            id=c.id,
            body=c.body,
            author=c.user.login if c.user else "unknown",
            created_at=c.created_at,
            path=c.path,
            line=c.line or c.original_line,
            in_reply_to_id=getattr(c, "in_reply_to_id", None),
            diff_hunk=c.diff_hunk,
            html_url=c.html_url,
        )
        for c in pr.get_comments()
    ]


def fetch_reviews(repo_slug: str, pr_number: int) -> list[PRReview]:
    """Fetch review summaries (APPROVED, CHANGES_REQUESTED, etc.).

    Args:
        repo_slug: Repository in 'owner/repo' format.
        pr_number: Pull request number.
    """
    client = _get_client()
    repo = client.get_repo(repo_slug)
    pr = repo.get_pull(pr_number)

    return [
        PRReview(
            id=r.id,
            body=r.body or "",
            author=r.user.login if r.user else "unknown",
            state=r.state,
            submitted_at=r.submitted_at,
            html_url=r.html_url,
        )
        for r in pr.get_reviews()
    ]


def group_comments_by_file(
    comments: list[PRComment],
) -> dict[str, list[PRComment]]:
    """Return inline comments grouped by file path, preserving thread order.

    Root comments (in_reply_to_id is None) are sorted by line then created_at.
    Replies are interleaved after their root comment.

    Args:
        comments: Flat list of PRComment objects.
    """
    grouped: dict[str, list[PRComment]] = {}

    for comment in comments:
        if comment.path is None:
            continue
        grouped.setdefault(comment.path, []).append(comment)

    for path in grouped:
        roots = [c for c in grouped[path] if c.in_reply_to_id is None]
        roots.sort(key=lambda c: (c.line or 0, c.created_at))

        replies_by_root: dict[int, list[PRComment]] = {}
        for c in grouped[path]:
            if c.in_reply_to_id is not None:
                replies_by_root.setdefault(c.in_reply_to_id, []).append(c)

        ordered: list[PRComment] = []
        for root in roots:
            ordered.append(root)
            for reply in sorted(
                replies_by_root.get(root.id, []), key=lambda c: c.created_at
            ):
                ordered.append(reply)

        grouped[path] = ordered

    return grouped
