from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from prism.models import PRMetadata, PRSummary


class TestGetClient:
    def test_raises_when_token_missing(self) -> None:
        from prism.services.github import _get_client

        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
                _get_client()

    def test_returns_github_instance_when_token_set(self) -> None:
        from github import Github

        from prism.services.github import _get_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test"}):
            with patch("prism.services.github.Github") as mock_cls:
                mock_cls.return_value = MagicMock(spec=Github)
                client = _get_client()

        mock_cls.assert_called_once_with("ghp_test")
        assert client is not None


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
        from prism.services.github import _issue_to_summary

        result = _issue_to_summary(self._make_issue())
        assert isinstance(result, PRSummary)
        assert result.number == 1
        assert result.state == "open"

    def test_maps_merged_pr(self) -> None:
        from prism.services.github import _issue_to_summary

        merged_at = datetime(2024, 5, 1, tzinfo=UTC)
        result = _issue_to_summary(self._make_issue(merged_at=merged_at))
        assert result is not None
        assert result.state == "merged"

    def test_returns_none_on_exception(self) -> None:
        from prism.services.github import _issue_to_summary

        broken = MagicMock()
        broken.number = None
        broken.repository.full_name = None  # will raise in PRSummary
        # Force an attribute error
        del broken.user

        result = _issue_to_summary(broken)
        assert result is None

    def test_review_state_is_none(self) -> None:
        from prism.services.github import _issue_to_summary

        result = _issue_to_summary(self._make_issue())
        assert result is not None
        assert result.review_state is None

    def test_checks_status_is_none(self) -> None:
        from prism.services.github import _issue_to_summary

        result = _issue_to_summary(self._make_issue())
        assert result is not None
        assert result.checks_status is None

    def test_maps_body(self) -> None:
        from prism.services.github import _issue_to_summary

        result = _issue_to_summary(self._make_issue(body="PR description"))
        assert result is not None
        assert result.body == "PR description"

    def test_empty_body_becomes_empty_string(self) -> None:
        from prism.services.github import _issue_to_summary

        issue = self._make_issue()
        issue.body = None
        result = _issue_to_summary(issue)
        assert result is not None
        assert result.body == ""


class TestFetchPr:
    @patch("prism.services.github._get_client")
    def test_returns_pr_metadata(self, mock_get_client: MagicMock) -> None:
        from prism.services.github import fetch_pr

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
        mock_get_client.return_value.get_repo.return_value = mock_repo

        result = fetch_pr("o/r", 42)

        assert isinstance(result, PRMetadata)
        assert result.number == 42
        assert result.title == "Add feature"
        assert result.state == "open"
        assert result.checks_status == "success"

    @patch("prism.services.github._get_client")
    def test_state_is_merged_when_pr_merged(self, mock_get_client: MagicMock) -> None:
        from prism.services.github import fetch_pr

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
        mock_get_client.return_value.get_repo.return_value = mock_repo

        result = fetch_pr("o/r", 1)

        assert result.state == "merged"

    @patch("prism.services.github._get_client")
    def test_checks_status_none_on_exception(self, mock_get_client: MagicMock) -> None:
        from prism.services.github import fetch_pr

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
        mock_get_client.return_value.get_repo.return_value = mock_repo

        result = fetch_pr("o/r", 1)

        assert result.checks_status is None


class TestFetchMyPrs:
    @patch("prism.services.github._get_client")
    def test_returns_list_of_pr_summaries(self, mock_get_client: MagicMock) -> None:
        from prism.services.github import fetch_my_prs

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

        mock_get_client.return_value.search_issues.return_value = [mock_issue]

        result = fetch_my_prs()

        assert len(result) == 1
        assert result[0].number == 5

    @patch("prism.services.github._get_client")
    def test_skips_issues_that_fail_mapping(self, mock_get_client: MagicMock) -> None:
        from prism.services.github import fetch_my_prs

        broken_issue = MagicMock()
        del broken_issue.user  # will cause AttributeError in _issue_to_summary

        mock_get_client.return_value.search_issues.return_value = [broken_issue]

        result = fetch_my_prs()
        assert result == []


class TestPostPrComment:
    @patch("prism.services.github._get_client")
    def test_calls_create_issue_comment(self, mock_get_client: MagicMock) -> None:
        from prism.services.github import post_pr_comment

        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        post_pr_comment("o/r", 1, "Great work!")

        mock_pr.create_issue_comment.assert_called_once_with("Great work!")

    @patch("prism.services.github._get_client")
    def test_raises_github_exception_on_error(self, mock_get_client: MagicMock) -> None:
        from github import GithubException

        from prism.services.github import post_pr_comment

        mock_pr = MagicMock()
        mock_pr.create_issue_comment.side_effect = GithubException(403, {"message": "Forbidden"})
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        with pytest.raises(GithubException):
            post_pr_comment("o/r", 1, "body")
