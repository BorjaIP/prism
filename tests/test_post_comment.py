"""Unit tests for post_comment() service function."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestPostComment:
    @patch("prism.services.github._get_client")
    def test_posts_comment_and_returns_pr_comment(
        self, mock_get_client: MagicMock
    ) -> None:
        from prism.services.github import post_comment

        mock_comment = MagicMock()
        mock_comment.id = 123
        mock_comment.body = "This needs a fix"
        mock_comment.user.login = "reviewer"
        mock_comment.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
        mock_comment.path = "src/main.py"
        mock_comment.line = 42
        mock_comment.diff_hunk = "@@ -40,5 +40,7 @@"
        mock_comment.html_url = "https://github.com/example/repo/pull/1#discussion_r123"
        mock_comment.in_reply_to_id = None

        mock_pr = MagicMock()
        mock_pr.create_review_comment.return_value = mock_comment
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        result = post_comment(
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

    @patch("prism.services.github._get_client")
    def test_raises_github_exception_on_api_error(
        self, mock_get_client: MagicMock
    ) -> None:
        from github import GithubException
        from prism.services.github import post_comment

        mock_pr = MagicMock()
        mock_pr.create_review_comment.side_effect = GithubException(
            422, {"message": "pull_request_review_thread.line is not part of the diff"}
        )
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        with pytest.raises(GithubException):
            post_comment(
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
