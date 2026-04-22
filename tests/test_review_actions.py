from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from prism.models import PRMetadata
from prism.services.github import GithubService


def _make_service(mock_repo=None) -> tuple[GithubService, MagicMock]:
    with patch("prism.services.github.Github"), patch("prism.services.github.diskcache.Cache"):
        svc = GithubService(token="test")
    mock_client = MagicMock()
    if mock_repo is not None:
        mock_client.get_repo.return_value = mock_repo
    svc._client = mock_client
    return svc, mock_client


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
    def test_submit_approve_calls_create_review(self) -> None:
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        svc, _ = _make_service(mock_repo)
        svc.submit_review("example/repo", 1, event="APPROVE")

        mock_pr.create_review.assert_called_once_with(body="", event="APPROVE")

    def test_submit_request_changes_passes_body(self) -> None:
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        svc, _ = _make_service(mock_repo)
        svc.submit_review("example/repo", 1, event="REQUEST_CHANGES", body="Please fix this")

        mock_pr.create_review.assert_called_once_with(
            body="Please fix this", event="REQUEST_CHANGES"
        )

    def test_submit_review_raises_github_exception(self) -> None:
        from github import GithubException

        mock_pr = MagicMock()
        mock_pr.create_review.side_effect = GithubException(
            422, {"message": "Can't approve your own PR"}
        )
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        svc, _ = _make_service(mock_repo)
        with pytest.raises(GithubException):
            svc.submit_review("example/repo", 1, event="APPROVE")


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

        from prism.components.modals.review_modals import RequestChangesModal

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

        from prism.components.modals.review_modals import RequestChangesModal

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
        from prism.components.sections.header_bar import HeaderBar

        pr = _make_pr()
        bar = HeaderBar(pr)
        # Update state without mounting — test _build_line1 directly
        bar._pr = pr.model_copy(update={"review_state": "APPROVED"})
        line1 = bar._build_line1()
        assert "APPROVED" in str(line1)

    def test_update_review_state_changes_requested(self) -> None:
        from prism.components.sections.header_bar import HeaderBar

        pr = _make_pr()
        bar = HeaderBar(pr)
        bar._pr = pr.model_copy(update={"review_state": "CHANGES_REQUESTED"})
        line1 = bar._build_line1()
        assert "CHANGES REQUESTED" in str(line1)

    def test_no_review_badge_when_none(self) -> None:
        from prism.components.sections.header_bar import HeaderBar

        pr = _make_pr()
        bar = HeaderBar(pr)
        line1 = bar._build_line1()
        assert "APPROVED" not in str(line1)
        assert "CHANGES" not in str(line1)
