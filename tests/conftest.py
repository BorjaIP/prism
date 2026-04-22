from __future__ import annotations

from datetime import UTC, datetime

import pytest

from prism.models import PRComment, PRFile, PRMetadata, PRSummary

# ── Model factories ────────────────────────────────────────────────────────────


def make_pr_metadata(**overrides) -> PRMetadata:
    defaults = dict(
        number=42,
        title="Add feature X",
        author="alice",
        state="open",
        base_branch="main",
        head_branch="feature/x",
        head_sha="deadbeef1234",
        html_url="https://github.com/owner/repo/pull/42",
        body="This PR adds feature X.",
        files=[],
        review_comments=[],
        checks_status="success",
    )
    defaults.update(overrides)
    return PRMetadata(**defaults)


def make_pr_file(**overrides) -> PRFile:
    defaults = dict(
        filename="src/feature.py",
        status="modified",
        additions=10,
        deletions=3,
        patch="@@ -1,3 +1,5 @@\n context\n+new line\n-old line\n",
        sha="abc123",
    )
    defaults.update(overrides)
    return PRFile(**defaults)


def make_pr_comment(**overrides) -> PRComment:
    defaults = dict(
        id=1,
        body="Please fix this.",
        author="reviewer",
        created_at=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        path="src/feature.py",
        line=10,
        diff_hunk="@@ -8,5 +8,7 @@",
        html_url="https://github.com/owner/repo/pull/42#discussion_r1",
    )
    defaults.update(overrides)
    return PRComment(**defaults)


def make_pr_summary(**overrides) -> PRSummary:
    defaults = dict(
        number=42,
        title="Add feature X",
        author="alice",
        repo_slug="owner/repo",
        state="open",
        base_branch="main",
        head_branch="feature/x",
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        html_url="https://github.com/owner/repo/pull/42",
        body="Description.",
        comments=0,
    )
    defaults.update(overrides)
    return PRSummary(**defaults)


# ── Pytest fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def pr_metadata():
    return make_pr_metadata()


@pytest.fixture
def pr_file():
    return make_pr_file()


@pytest.fixture
def pr_comment():
    return make_pr_comment()


@pytest.fixture
def pr_summary():
    return make_pr_summary()
