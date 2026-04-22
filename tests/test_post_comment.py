from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from prism.services.github import GithubService


def _make_service(mock_repo=None) -> tuple[GithubService, MagicMock]:
    with patch("prism.services.github.Github"), patch("prism.services.github.diskcache.Cache"):
        svc = GithubService(token="test")
    mock_client = MagicMock()
    if mock_repo is not None:
        mock_client.get_repo.return_value = mock_repo
    svc._client = mock_client
    return svc, mock_client


class TestPostComment:
    def test_posts_comment_and_returns_pr_comment(self) -> None:
        mock_comment = MagicMock()
        mock_comment.id = 123
        mock_comment.body = "This needs a fix"
        mock_comment.user.login = "reviewer"
        mock_comment.created_at = datetime(2024, 6, 1, tzinfo=UTC)
        mock_comment.path = "src/main.py"
        mock_comment.line = 42
        mock_comment.diff_hunk = "@@ -40,5 +40,7 @@"
        mock_comment.html_url = "https://github.com/example/repo/pull/1#discussion_r123"
        mock_comment.in_reply_to_id = None

        mock_pr = MagicMock()
        mock_pr.create_review_comment.return_value = mock_comment
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        svc, _ = _make_service(mock_repo)
        result = svc.post_comment(
            repo_slug="example/repo",
            pr_number=1,
            commit_id="abc123sha",
            path="src/main.py",
            line=42,
            body="This needs a fix",
        )

        mock_pr.create_review_comment.assert_called_once_with(
            body="This needs a fix",
            commit_id="abc123sha",
            path="src/main.py",
            line=42,
        )
        assert result.id == 123
        assert result.body == "This needs a fix"
        assert result.author == "reviewer"
        assert result.path == "src/main.py"
        assert result.line == 42

    def test_raises_github_exception_on_api_error(self) -> None:
        from github import GithubException

        mock_pr = MagicMock()
        mock_pr.create_review_comment.side_effect = GithubException(
            422, {"message": "pull_request_review_thread.line is not part of the diff"}
        )
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        svc, _ = _make_service(mock_repo)
        with pytest.raises(GithubException):
            svc.post_comment(
                repo_slug="example/repo",
                pr_number=1,
                commit_id="abc123sha",
                path="src/main.py",
                line=999,
                body="comment on invalid line",
            )


class TestPRMetadataHeadSha:
    def test_pr_metadata_has_head_sha_field(self) -> None:
        from prism.models import PRMetadata

        pr = PRMetadata(
            number=1,
            title="Test PR",
            author="user",
            state="open",
            base_branch="main",
            head_branch="feature",
            head_sha="abc123def456",
        )
        assert pr.head_sha == "abc123def456"

    def test_head_sha_defaults_to_empty_string(self) -> None:
        from prism.models import PRMetadata

        pr = PRMetadata(
            number=1,
            title="Test PR",
            author="user",
            state="open",
            base_branch="main",
            head_branch="feature",
        )
        assert pr.head_sha == ""
