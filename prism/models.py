"""Data models for Prism."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PRSummary(BaseModel):
    """Lightweight pull request summary used for the PR list screen."""

    number: int
    title: str
    author: str
    repo_slug: str  # "owner/repo"
    state: str  # open, closed, merged
    base_branch: str
    head_branch: str
    review_state: str | None = None
    checks_status: str | None = None
    updated_at: datetime
    html_url: str = ""
    body: str = ""
    comments: int = 0


@dataclass(frozen=True)
class Comment:
    """A transient UI comment value composed by the user before posting."""

    file_path: str
    line_number: int
    body: str


class PRFile(BaseModel):
    """A single file changed in a pull request."""

    filename: str
    status: str  # added, modified, removed, renamed
    additions: int
    deletions: int
    patch: str | None = None
    sha: str = ""


class PRMetadata(BaseModel):
    """Pull request metadata and file list."""

    number: int
    title: str
    author: str
    state: str  # open, closed, merged
    base_branch: str
    head_branch: str
    files: list[PRFile] = []
    body: str = ""
    html_url: str = ""
    head_sha: str = ""  # PR head commit SHA, required for create_review_comment
    review_state: str | None = None  # "APPROVED" | "CHANGES_REQUESTED" — set locally after submitting
    review_comments: list["PRComment"] = []  # inline review comments pre-loaded at fetch time
    checks_status: str | None = None  # "passing" | "failing" | "pending" from combined commit status


class PRComment(BaseModel):
    """An inline review comment on a PR."""

    model_config = ConfigDict(frozen=True)

    id: int
    body: str
    author: str
    created_at: datetime
    # inline-specific (None for conversation-level comments)
    path: str | None = None
    line: int | None = None
    in_reply_to_id: int | None = None
    diff_hunk: str | None = None
    html_url: str = ""


class PRReview(BaseModel):
    """A PR review summary (APPROVED, CHANGES_REQUESTED, etc.)."""

    model_config = ConfigDict(frozen=True)

    id: int
    body: str
    author: str
    state: str  # APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
    submitted_at: datetime
    html_url: str = ""
