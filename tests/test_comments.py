"""Unit tests for comment fetching and grouping."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from prism.models import PRComment, PRReview
from prism.services.github import group_comments_by_file


def _make_comment(
    id: int,
    path: str,
    line: int,
    body: str = "comment",
    in_reply_to_id: int | None = None,
    created_at: datetime | None = None,
) -> PRComment:
    return PRComment(
        id=id,
        body=body,
        author="user",
        created_at=created_at or datetime(2024, 1, 1, tzinfo=timezone.utc),
        path=path,
        line=line,
        in_reply_to_id=in_reply_to_id,
        html_url="",
    )


class TestGroupCommentsByFile:
    def test_groups_by_path(self) -> None:
        comments = [
            _make_comment(1, "src/a.py", 10),
            _make_comment(2, "src/b.py", 20),
            _make_comment(3, "src/a.py", 15),
        ]
        result = group_comments_by_file(comments)
        assert set(result.keys()) == {"src/a.py", "src/b.py"}
        assert len(result["src/a.py"]) == 2
        assert len(result["src/b.py"]) == 1

    def test_roots_sorted_by_line(self) -> None:
        comments = [
            _make_comment(1, "src/a.py", 30),
            _make_comment(2, "src/a.py", 10),
            _make_comment(3, "src/a.py", 20),
        ]
        result = group_comments_by_file(comments)
        lines = [c.line for c in result["src/a.py"]]
        assert lines == [10, 20, 30]

    def test_replies_interleaved_after_root(self) -> None:
        root = _make_comment(1, "src/a.py", 10)
        reply1 = _make_comment(
            2,
            "src/a.py",
            10,
            in_reply_to_id=1,
            created_at=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
        )
        reply2 = _make_comment(
            3,
            "src/a.py",
            10,
            in_reply_to_id=1,
            created_at=datetime(2024, 1, 1, 2, tzinfo=timezone.utc),
        )
        comments = [reply2, reply1, root]  # scrambled order
        result = group_comments_by_file(comments)
        ids = [c.id for c in result["src/a.py"]]
        assert ids == [1, 2, 3]  # root, then replies by created_at

    def test_skips_comments_without_path(self) -> None:
        comment_with_path = _make_comment(1, "src/a.py", 10)
        comment_no_path = PRComment(
            id=2,
            body="general",
            author="user",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            path=None,
        )
        result = group_comments_by_file([comment_with_path, comment_no_path])
        assert list(result.keys()) == ["src/a.py"]

    def test_empty_input(self) -> None:
        assert group_comments_by_file([]) == {}


class TestFetchComments:
    @patch("prism.services.github._get_client")
    def test_maps_pygithub_comment_to_pr_comment(self, mock_get_client: MagicMock) -> None:
        from prism.services.github import fetch_comments

        mock_comment = MagicMock()
        mock_comment.id = 42
        mock_comment.body = "This needs fixing"
        mock_comment.user.login = "reviewer"
        mock_comment.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
        mock_comment.path = "src/main.py"
        mock_comment.line = 15
        mock_comment.original_line = 15
        mock_comment.in_reply_to_id = None
        mock_comment.diff_hunk = "@@ -1,3 +1,5 @@"
        mock_comment.html_url = "https://github.com/example/repo/pull/1#discussion_r42"

        mock_pr = MagicMock()
        mock_pr.get_comments.return_value = [mock_comment]
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        result = fetch_comments("example/repo", 1)

        assert len(result) == 1
        comment = result[0]
        assert comment.id == 42
        assert comment.body == "This needs fixing"
        assert comment.author == "reviewer"
        assert comment.path == "src/main.py"
        assert comment.line == 15
        assert comment.in_reply_to_id is None


class TestFetchReviews:
    @patch("prism.services.github._get_client")
    def test_maps_pygithub_review_to_pr_review(self, mock_get_client: MagicMock) -> None:
        from prism.services.github import fetch_reviews

        mock_review = MagicMock()
        mock_review.id = 99
        mock_review.body = "Looks good overall"
        mock_review.user.login = "approver"
        mock_review.state = "APPROVED"
        mock_review.submitted_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
        mock_review.html_url = "https://github.com/example/repo/pull/1#pullrequestreview-99"

        mock_pr = MagicMock()
        mock_pr.get_reviews.return_value = [mock_review]
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        result = fetch_reviews("example/repo", 1)

        assert len(result) == 1
        review = result[0]
        assert review.id == 99
        assert review.state == "APPROVED"
        assert review.author == "approver"
        assert review.body == "Looks good overall"
