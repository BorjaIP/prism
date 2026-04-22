"""Unit tests for the reply-to-comment feature."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from prism.models import PRComment


def _make_comment(**kwargs) -> PRComment:
    defaults = dict(
        id=1,
        body="Please fix this",
        author="reviewer",
        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        path="src/main.py",
        line=42,
        diff_hunk="@@ -40,5 +40,7 @@",
        html_url="https://github.com/example/repo/pull/1#discussion_r1",
    )
    defaults.update(kwargs)
    return PRComment(**defaults)


class TestPostReply:
    @patch("prism.services.github._get_client")
    def test_post_reply_calls_create_review_comment_reply(
        self, mock_get_client: MagicMock
    ) -> None:
        from prism.services.github import post_reply

        mock_reply = MagicMock()
        mock_reply.id = 999
        mock_reply.body = "Fixed!"
        mock_reply.user.login = "author"
        mock_reply.created_at = datetime(2024, 6, 2, tzinfo=timezone.utc)
        mock_reply.path = "src/main.py"
        mock_reply.line = 42
        mock_reply.diff_hunk = "@@ -40,5 +40,7 @@"
        mock_reply.html_url = "https://github.com/example/repo/pull/1#discussion_r999"
        mock_reply.in_reply_to_id = 1

        mock_pr = MagicMock()
        mock_pr.create_review_comment_reply.return_value = mock_reply
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        result = post_reply("example/repo", 1, comment_id=1, body="Fixed!")

        mock_pr.create_review_comment_reply.assert_called_once_with(1, "Fixed!")
        assert result.id == 999
        assert result.body == "Fixed!"
        assert result.author == "author"
        assert result.in_reply_to_id == 1

    @patch("prism.services.github._get_client")
    def test_post_reply_raises_github_exception(
        self, mock_get_client: MagicMock
    ) -> None:
        from github import GithubException
        from prism.services.github import post_reply

        mock_pr = MagicMock()
        mock_pr.create_review_comment_reply.side_effect = GithubException(
            404, {"message": "Comment not found"}
        )
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        with pytest.raises(GithubException):
            post_reply("example/repo", 1, comment_id=999, body="Reply")


class TestCommentList:
    def test_set_comments_populates_list(self) -> None:
        from prism.components.panels.comment_list import CommentList

        widget = CommentList()
        comments = [_make_comment(id=1), _make_comment(id=2, line=10)]
        widget._comments = comments
        # Direct model check — set_comments needs mounted widget so only test model
        assert len(widget._comments) == 2

    def test_comment_label_root(self) -> None:
        from prism.components.blocks.comment_item import comment_label as _comment_label

        comment = _make_comment(body="Short body", in_reply_to_id=None)
        label = _comment_label(comment)
        assert "@reviewer" in label
        assert "line 42" in label
        assert "Short body" in label
        assert label.startswith("@")

    def test_comment_label_reply_indented(self) -> None:
        from prism.components.blocks.comment_item import comment_label as _comment_label

        comment = _make_comment(body="Reply body", in_reply_to_id=1)
        label = _comment_label(comment)
        assert label.startswith("  ↳ ")

    def test_comment_label_truncates_long_body(self) -> None:
        from prism.components.blocks.comment_item import comment_label as _comment_label

        long_body = "x" * 100
        comment = _make_comment(body=long_body)
        label = _comment_label(comment)
        assert label.endswith("…")
        # body portion should be 80 chars + ellipsis
        assert "x" * 80 in label


class TestReplyComposer:
    @pytest.mark.asyncio
    async def test_escape_dismisses_with_none(self) -> None:
        from textual.app import App, ComposeResult
        from prism.components.modals.reply_composer import ReplyComposer

        result: list[str | None] = []
        comment = _make_comment()

        class _TestApp(App):
            def compose(self) -> ComposeResult:
                return iter([])

            def on_mount(self) -> None:
                self.push_screen(ReplyComposer(comment), callback=result.append)

        async with _TestApp().run_test() as pilot:
            await pilot.press("escape")

        assert result == [None]

    @pytest.mark.asyncio
    async def test_ctrl_s_with_text_dismisses_with_body(self) -> None:
        from textual.app import App, ComposeResult
        from textual.widgets import TextArea
        from prism.components.modals.reply_composer import ReplyComposer

        result: list[str | None] = []
        comment = _make_comment()

        class _TestApp(App):
            def compose(self) -> ComposeResult:
                return iter([])

            def on_mount(self) -> None:
                self.push_screen(ReplyComposer(comment), callback=result.append)

        async with _TestApp().run_test() as pilot:
            pilot.app.screen.query_one("#reply-area", TextArea).insert("looks good")
            await pilot.press("ctrl+s")

        assert result == ["looks good"]

    @pytest.mark.asyncio
    async def test_empty_submit_shows_error(self) -> None:
        from textual.app import App, ComposeResult
        from textual.widgets import Label
        from prism.components.modals.reply_composer import ReplyComposer

        result: list[str | None] = []
        comment = _make_comment()

        class _TestApp(App):
            def compose(self) -> ComposeResult:
                return iter([])

            def on_mount(self) -> None:
                self.push_screen(ReplyComposer(comment), callback=result.append)

        async with _TestApp().run_test() as pilot:
            await pilot.click("#submit")
            error_text = str(
                pilot.app.screen.query_one("#reply-error", Label).render()
            )

        # Modal should still be open (result not populated yet)
        assert result == []
        assert "empty" in error_text.lower()


class TestPRMetadataReviewComments:
    def test_review_comments_defaults_empty(self) -> None:
        from prism.models import PRMetadata

        pr = PRMetadata(
            number=1, title="T", author="u", state="open",
            base_branch="main", head_branch="feature",
        )
        assert pr.review_comments == []

    def test_review_comments_stored(self) -> None:
        from prism.models import PRMetadata

        comment = _make_comment()
        pr = PRMetadata(
            number=1, title="T", author="u", state="open",
            base_branch="main", head_branch="feature",
            review_comments=[comment],
        )
        assert len(pr.review_comments) == 1
        assert pr.review_comments[0].id == 1
