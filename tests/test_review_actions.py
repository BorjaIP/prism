"""Unit tests for approve/request-changes review actions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from prism.models import PRMetadata


def _make_pr(**kwargs) -> PRMetadata:
    defaults = dict(
        number=1,
        title="Test PR",
        author="user",
        state="open",
        base_branch="main",
        head_branch="feature",
        head_sha="abc123",
    )
    defaults.update(kwargs)
    return PRMetadata(**defaults)


class TestSubmitReview:
    @patch("prism.services.github._get_client")
    def test_submit_approve_calls_create_review(
        self, mock_get_client: MagicMock
    ) -> None:
        from prism.services.github import submit_review

        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        submit_review("example/repo", 1, event="APPROVE")

        mock_pr.create_review.assert_called_once_with(body="", event="APPROVE")

    @patch("prism.services.github._get_client")
    def test_submit_request_changes_passes_body(
        self, mock_get_client: MagicMock
    ) -> None:
        from prism.services.github import submit_review

        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        submit_review("example/repo", 1, event="REQUEST_CHANGES", body="Please fix this")

        mock_pr.create_review.assert_called_once_with(
            body="Please fix this", event="REQUEST_CHANGES"
        )

    @patch("prism.services.github._get_client")
    def test_submit_review_raises_github_exception(
        self, mock_get_client: MagicMock
    ) -> None:
        from github import GithubException
        from prism.services.github import submit_review

        mock_pr = MagicMock()
        mock_pr.create_review.side_effect = GithubException(
            422, {"message": "Can't approve your own PR"}
        )
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_get_client.return_value.get_repo.return_value = mock_repo

        with pytest.raises(GithubException):
            submit_review("example/repo", 1, event="APPROVE")


class TestPRMetadataReviewState:
    def test_review_state_defaults_to_none(self) -> None:
        pr = _make_pr()
        assert pr.review_state is None

    def test_review_state_can_be_set(self) -> None:
        pr = _make_pr(review_state="APPROVED")
        assert pr.review_state == "APPROVED"

    def test_model_copy_updates_review_state(self) -> None:
        pr = _make_pr()
        updated = pr.model_copy(update={"review_state": "APPROVED"})
        assert updated.review_state == "APPROVED"
        assert pr.review_state is None  # original unchanged


class TestRequestChangesModal:
    @pytest.mark.asyncio
    async def test_cancel_returns_none(self) -> None:
        from textual.app import App, ComposeResult
        from prism.widgets.review_modal import RequestChangesModal

        result: list[str | None] = []

        class _TestApp(App):
            def compose(self) -> ComposeResult:
                return iter([])

            def on_mount(self) -> None:
                def capture(value: str | None) -> None:
                    result.append(value)

                self.push_screen(RequestChangesModal(), callback=capture)

        async with _TestApp().run_test() as pilot:
            await pilot.press("escape")

        assert result == [None]

    @pytest.mark.asyncio
    async def test_submit_returns_body_text(self) -> None:
        from textual.app import App, ComposeResult
        from textual.widgets import TextArea
        from prism.widgets.review_modal import RequestChangesModal

        result: list[str | None] = []

        class _TestApp(App):
            def compose(self) -> ComposeResult:
                return iter([])

            def on_mount(self) -> None:
                def capture(value: str | None) -> None:
                    result.append(value)

                self.push_screen(RequestChangesModal(), callback=capture)

        async with _TestApp().run_test() as pilot:
            pilot.app.screen.query_one("#body-input", TextArea).insert("please fix")
            await pilot.click("#submit")

        assert result == ["please fix"]


class TestHeaderBarReviewState:
    def test_update_review_state_approved(self) -> None:
        from prism.widgets.header_bar import HeaderBar

        pr = _make_pr()
        bar = HeaderBar(pr)
        # Update state without mounting — test _build_line1 directly
        bar._pr = pr.model_copy(update={"review_state": "APPROVED"})
        line1 = bar._build_line1()
        assert "APPROVED" in str(line1)

    def test_update_review_state_changes_requested(self) -> None:
        from prism.widgets.header_bar import HeaderBar

        pr = _make_pr()
        bar = HeaderBar(pr)
        bar._pr = pr.model_copy(update={"review_state": "CHANGES_REQUESTED"})
        line1 = bar._build_line1()
        assert "CHANGES REQUESTED" in str(line1)

    def test_no_review_badge_when_none(self) -> None:
        from prism.widgets.header_bar import HeaderBar

        pr = _make_pr()
        bar = HeaderBar(pr)
        line1 = bar._build_line1()
        assert "APPROVED" not in str(line1)
        assert "CHANGES" not in str(line1)
