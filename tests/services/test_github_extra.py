from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from prism.models import PRMetadata, PRSummary
from prism.services.github import GithubService


class TestGithubServiceInit:
    def test_raises_when_token_missing(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
                GithubService()

    def test_accepts_explicit_token(self) -> None:
        with patch("prism.services.github.Github") as mock_cls:
            svc = GithubService(token="ghp_test")
        mock_cls.assert_called_once_with("ghp_test")
        assert svc is not None

    def test_reads_token_from_env(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_env"}):
            with patch("prism.services.github.Github") as mock_cls:
                svc = GithubService()
        mock_cls.assert_called_once_with("ghp_env")
        assert svc is not None


def _make_service(mock_repo=None) -> tuple[GithubService, MagicMock]:
    """Build a GithubService with a mocked underlying Github client."""
    with patch("prism.services.github.Github"), patch("prism.services.github.diskcache.Cache"):
        svc = GithubService(token="test")
    mock_client = MagicMock()
    if mock_repo is not None:
        mock_client.get_repo.return_value = mock_repo
    svc._client = mock_client
    return svc, mock_client


class TestIssueToSummary:
    def _make_issue(self, *, number=1, title="T", state="open", merged_at=None, body=""):
        issue = MagicMock()
        issue.number = number
        issue.title = title
        issue.state = state
        issue.user.login = "author"
        issue.repository.full_name = "owner/repo"
        issue.updated_at = datetime(2024, 6, 1, tzinfo=UTC)
        issue.html_url = f"https://github.com/owner/repo/pull/{number}"
        issue.body = body
        issue.comments = 0
        pr_part = MagicMock()
        pr_part.merged_at = merged_at
        issue.pull_request = pr_part
        return issue

    def test_maps_open_pr(self) -> None:
        result = GithubService._issue_to_summary(self._make_issue())
        assert isinstance(result, PRSummary)
        assert result.number == 1
        assert result.state == "open"

    def test_maps_merged_pr(self) -> None:
        merged_at = datetime(2024, 5, 1, tzinfo=UTC)
        result = GithubService._issue_to_summary(self._make_issue(merged_at=merged_at))
        assert result is not None
        assert result.state == "merged"

    def test_returns_none_on_exception(self) -> None:
        broken = MagicMock()
        broken.number = None
        broken.repository.full_name = None
        del broken.user
        result = GithubService._issue_to_summary(broken)
        assert result is None

    def test_review_state_is_none(self) -> None:
        result = GithubService._issue_to_summary(self._make_issue())
        assert result is not None
        assert result.review_state is None

    def test_checks_status_is_none(self) -> None:
        result = GithubService._issue_to_summary(self._make_issue())
        assert result is not None
        assert result.checks_status is None

    def test_maps_body(self) -> None:
        result = GithubService._issue_to_summary(self._make_issue(body="PR description"))
        assert result is not None
        assert result.body == "PR description"

    def test_empty_body_becomes_empty_string(self) -> None:
        issue = self._make_issue()
        issue.body = None
        result = GithubService._issue_to_summary(issue)
        assert result is not None
        assert result.body == ""


class TestFetchPr:
    def test_returns_pr_metadata(self) -> None:
        mock_pr = MagicMock()
        mock_pr.number = 42
        mock_pr.title = "Add feature"
        mock_pr.user.login = "alice"
        mock_pr.merged = False
        mock_pr.state = "open"
        mock_pr.base.ref = "main"
        mock_pr.head.ref = "feature"
        mock_pr.head.sha = "deadbeef"
        mock_pr.body = "Description"
        mock_pr.html_url = "https://github.com/o/r/pull/42"
        mock_pr.get_files.return_value = []
        mock_pr.get_review_comments.return_value = []
        mock_pr.review_state = None

        mock_commit = MagicMock()
        mock_status = MagicMock()
        mock_status.state = "success"
        mock_commit.get_combined_status.return_value = mock_status

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_repo.get_commit.return_value = mock_commit

        svc, _ = _make_service(mock_repo)
        result = svc.fetch_pr("o/r", 42)

        assert isinstance(result, PRMetadata)
        assert result.number == 42
        assert result.title == "Add feature"
        assert result.state == "open"
        assert result.checks_status == "success"

    def test_state_is_merged_when_pr_merged(self) -> None:
        mock_pr = MagicMock()
        mock_pr.number = 1
        mock_pr.title = "Merged"
        mock_pr.user.login = "bob"
        mock_pr.merged = True
        mock_pr.state = "closed"
        mock_pr.base.ref = "main"
        mock_pr.head.ref = "feat"
        mock_pr.head.sha = "abc"
        mock_pr.body = ""
        mock_pr.html_url = ""
        mock_pr.get_files.return_value = []
        mock_pr.get_review_comments.return_value = []

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_repo.get_commit.side_effect = Exception("no commit")

        svc, _ = _make_service(mock_repo)
        result = svc.fetch_pr("o/r", 1)
        assert result.state == "merged"

    def test_checks_status_none_on_exception(self) -> None:
        mock_pr = MagicMock()
        mock_pr.number = 1
        mock_pr.title = "T"
        mock_pr.user.login = "u"
        mock_pr.merged = False
        mock_pr.state = "open"
        mock_pr.base.ref = "main"
        mock_pr.head.ref = "feat"
        mock_pr.head.sha = "abc"
        mock_pr.body = ""
        mock_pr.html_url = ""
        mock_pr.get_files.return_value = []
        mock_pr.get_review_comments.return_value = []

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_repo.get_commit.side_effect = Exception("network error")

        svc, _ = _make_service(mock_repo)
        result = svc.fetch_pr("o/r", 1)
        assert result.checks_status is None


class TestFetchMyPrs:
    def test_returns_list_of_pr_summaries(self) -> None:
        mock_issue = MagicMock()
        mock_issue.number = 5
        mock_issue.title = "My PR"
        mock_issue.state = "open"
        mock_issue.user.login = "me"
        mock_issue.repository.full_name = "o/r"
        mock_issue.updated_at = datetime(2024, 6, 1, tzinfo=UTC)
        mock_issue.html_url = "https://github.com/o/r/pull/5"
        mock_issue.body = ""
        mock_issue.comments = 0
        pr_part = MagicMock()
        pr_part.merged_at = None
        mock_issue.pull_request = pr_part

        svc, mock_client = _make_service()
        mock_client.search_issues.return_value = [mock_issue]

        result = svc.fetch_my_prs()
        assert len(result) == 1
        assert result[0].number == 5

    def test_skips_issues_that_fail_mapping(self) -> None:
        broken_issue = MagicMock()
        del broken_issue.user

        svc, mock_client = _make_service()
        mock_client.search_issues.return_value = [broken_issue]

        result = svc.fetch_my_prs()
        assert result == []


class TestPostPrComment:
    def test_calls_create_issue_comment(self) -> None:
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        svc, _ = _make_service(mock_repo)
        svc.post_pr_comment("o/r", 1, "Great work!")

        mock_pr.create_issue_comment.assert_called_once_with("Great work!")

    def test_raises_github_exception_on_error(self) -> None:
        from github import GithubException

        mock_pr = MagicMock()
        mock_pr.create_issue_comment.side_effect = GithubException(403, {"message": "Forbidden"})
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        svc, _ = _make_service(mock_repo)
        with pytest.raises(GithubException):
            svc.post_pr_comment("o/r", 1, "body")
