from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path

import diskcache
from github import Github
from github.PullRequest import PullRequest

from prism.constants import PR_LIST_CACHE_TTL, PRISM_CACHE_DIR
from prism.models import PRComment, PRFile, PRMetadata, PRReview, PRSummary

_CACHE_KEY_REVIEW_REQUESTED = "github:review_requested"


def _pr_cache_key(repo_slug: str, pr_number: int) -> str:
    return f"github:pr:{repo_slug}:{pr_number}"


def _ts_key(key: str) -> str:
    """Companion key that stores the unix timestamp of when a cache entry was written."""
    return f"{key}:ts"


class GithubService:
    """Wrapper around the GitHub API for all PR-related operations."""

    def __init__(self, token: str | None = None, cache_dir: Path | None = None) -> None:
        resolved = token or os.environ.get("GITHUB_TOKEN", "")
        if not resolved:
            raise RuntimeError(
                "GITHUB_TOKEN environment variable is required. "
                "Create one at https://github.com/settings/tokens"
            )
        self._client = Github(resolved)
        self._cache = diskcache.Cache(cache_dir or PRISM_CACHE_DIR)

    # ── Cache helpers ─────────────────────────────────────────────────────────

    def _cache_set(self, key: str, value: object) -> None:
        """Store *value* under *key* with TTL, plus a companion timestamp entry."""
        self._cache.set(key, value, expire=PR_LIST_CACHE_TTL)
        self._cache.set(_ts_key(key), time.time())  # no expire — survives for age check

    def _cached_at(self, key: str) -> datetime | None:
        """Return when *key* was last written to cache, or None if unknown."""
        ts = self._cache.get(_ts_key(key))
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=UTC)

    def pr_cached_at(self, repo_slug: str, pr_number: int) -> datetime | None:
        """Return when the given PR was last cached, or None."""
        return self._cached_at(_pr_cache_key(repo_slug, pr_number))

    def review_requested_cached_at(self) -> datetime | None:
        """Return when the review-requested list was last cached, or None."""
        return self._cached_at(_CACHE_KEY_REVIEW_REQUESTED)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
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

    # ── Read operations ───────────────────────────────────────────────────────

    def fetch_my_prs(self, state: str = "open") -> list[PRSummary]:
        """Fetch pull requests authored by the authenticated user (single search call)."""
        results = self._client.search_issues(f"is:pr is:{state} author:@me sort:updated-desc")
        return [s for issue in results if (s := self._issue_to_summary(issue)) is not None]

    def fetch_review_requested(self, *, force_refresh: bool = False) -> list[PRSummary]:
        """Fetch open PRs where the authenticated user is requested as reviewer.

        Results are cached locally for PR_LIST_CACHE_TTL seconds so repeated
        tab switches don't hit the GitHub search API every time.
        Pass force_refresh=True to bypass the cache (e.g. on manual 'r' refresh).
        """
        if not force_refresh and _CACHE_KEY_REVIEW_REQUESTED in self._cache:
            cached = self._cache[_CACHE_KEY_REVIEW_REQUESTED]
            if isinstance(cached, list):
                return cached
        results = self._client.search_issues("is:pr is:open review-requested:@me sort:updated-desc")
        summaries = [s for issue in results if (s := self._issue_to_summary(issue)) is not None]
        self._cache_set(_CACHE_KEY_REVIEW_REQUESTED, summaries)
        return summaries

    def fetch_pr(
        self, repo_slug: str, pr_number: int, *, force_refresh: bool = False
    ) -> PRMetadata:
        """Fetch PR metadata and file list from GitHub.

        Results are cached locally for PR_LIST_CACHE_TTL seconds. The diff
        content is stable between commits, so a short TTL is enough to avoid
        redundant fetches while still surfacing newly pushed commits on refresh.
        Pass force_refresh=True to bypass the cache (used by the 'r' keybinding).

        Args:
            repo_slug: Repository in 'owner/repo' format.
            pr_number: Pull request number.
        """
        key = _pr_cache_key(repo_slug, pr_number)
        if not force_refresh and key in self._cache:
            cached = self._cache[key]
            if isinstance(cached, PRMetadata):
                return cached

        repo = self._client.get_repo(repo_slug)
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

        result = PRMetadata(
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
        self._cache_set(key, result)
        return result

    def fetch_comments(self, repo_slug: str, pr_number: int) -> list[PRComment]:
        """Fetch all inline review comments for the PR."""
        repo = self._client.get_repo(repo_slug)
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

    def fetch_reviews(self, repo_slug: str, pr_number: int) -> list[PRReview]:
        """Fetch review summaries (APPROVED, CHANGES_REQUESTED, etc.)."""
        repo = self._client.get_repo(repo_slug)
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

    # ── Write operations ──────────────────────────────────────────────────────

    def post_comment(
        self,
        repo_slug: str,
        pr_number: int,
        commit_id: str,
        path: str,
        line: int,
        body: str,
    ) -> PRComment:
        """Post an inline review comment to a PR file at a specific line.

        Raises:
            GithubException: On GitHub API errors (e.g. 422 if line not in diff).
        """
        repo = self._client.get_repo(repo_slug)
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
        self,
        repo_slug: str,
        pr_number: int,
        comment_id: int,
        body: str,
    ) -> PRComment:
        """Post an in-thread reply to an existing review comment.

        Raises:
            GithubException: On GitHub API errors.
        """
        repo = self._client.get_repo(repo_slug)
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

    def submit_review(self, repo_slug: str, pr_number: int, event: str, body: str = "") -> None:
        """Submit a PR review via the GitHub API.

        Args:
            repo_slug: Repository in 'owner/repo' format.
            pr_number: Pull request number.
            event: Review event — "APPROVE" or "REQUEST_CHANGES".
            body: Optional review message (required for REQUEST_CHANGES).

        Raises:
            GithubException: On GitHub API errors.
        """
        repo = self._client.get_repo(repo_slug)
        pr = repo.get_pull(pr_number)
        pr.create_review(body=body, event=event)

    def post_pr_comment(self, repo_slug: str, pr_number: int, body: str) -> None:
        """Post a PR-level (issue-level) comment.

        Raises:
            GithubException: On GitHub API errors.
        """
        repo = self._client.get_repo(repo_slug)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(body)

    # ── Pure helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def group_comments_by_file(
        comments: list[PRComment],
    ) -> dict[str, list[PRComment]]:
        """Return inline comments grouped by file path, preserving thread order.

        Root comments (in_reply_to_id is None) are sorted by line then created_at.
        Replies are interleaved after their root comment.
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
                for reply in sorted(replies_by_root.get(root.id, []), key=lambda c: c.created_at):
                    ordered.append(reply)

            grouped[path] = ordered

        return grouped
