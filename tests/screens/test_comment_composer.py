"""Tests for CommentComposerScreen modal."""

from __future__ import annotations

import pytest

from textual.app import App, ComposeResult

from prism.models import Comment
from prism.components.modals.comment_composer import CommentComposerScreen


class _ComposerApp(App):
    """Minimal app for testing CommentComposerScreen."""

    def __init__(self, file_path: str = "src/main.py", line_number: int = 0) -> None:
        super().__init__()
        self._file_path = file_path
        self._line_number = line_number
        self.last_result: Comment | None = None
        self.dismissed = False

    def on_mount(self) -> None:
        screen = CommentComposerScreen(self._file_path, self._line_number)
        self.push_screen(screen, callback=self._on_result)

    def _on_result(self, result: Comment | None) -> None:
        self.last_result = result
        self.dismissed = True
        self.exit()

    def compose(self) -> ComposeResult:
        return iter([])


@pytest.mark.asyncio
async def test_context_header_shows_file_and_line() -> None:
    """The context static should show the file path and line number."""
    from textual.widgets import Static

    app = _ComposerApp("src/utils.py", 15)
    async with app.run_test() as pilot:
        # Find the modal screen
        modal = app.screen
        context = modal.query_one("#comment-context", Static)
        rendered = str(context.render())
        assert "src/utils.py" in rendered
        assert "15" in rendered
        await pilot.press("escape")


@pytest.mark.asyncio
async def test_comment_area_is_focused_on_mount() -> None:
    """The TextArea should be focused immediately after mount."""
    from textual.widgets import TextArea

    app = _ComposerApp("src/main.py", 42)
    async with app.run_test() as pilot:
        modal = app.screen
        area = modal.query_one("#comment-area", TextArea)
        assert area.has_focus
        await pilot.press("escape")


@pytest.mark.asyncio
async def test_empty_submit_shows_error() -> None:
    """Submitting without text shows an error message."""
    from textual.widgets import Static

    app = _ComposerApp("src/main.py", 0)
    async with app.run_test() as pilot:
        # Click submit without typing anything
        await pilot.click("#btn-submit")
        modal = app.screen
        error = modal.query_one("#comment-error", Static)
        assert str(error.render()) != ""
        await pilot.press("escape")


@pytest.mark.asyncio
async def test_esc_cancels_and_returns_none() -> None:
    """Pressing ESC dismisses the modal with None."""
    app = _ComposerApp("src/main.py", 10)
    async with app.run_test() as pilot:
        await pilot.press("escape")
    assert app.last_result is None


@pytest.mark.asyncio
async def test_ctrl_s_submits_valid_comment() -> None:
    """Ctrl+S submits a valid comment when text is present."""
    from textual.widgets import TextArea

    app = _ComposerApp("src/app.py", 7)
    async with app.run_test() as pilot:
        area = app.screen.query_one("#comment-area", TextArea)
        await pilot.click("#comment-area")
        # Type some text
        for char in "This looks good":
            await pilot.press(char)
        await pilot.press("ctrl+s")
    assert app.last_result is not None
    assert app.last_result.file_path == "src/app.py"
    assert app.last_result.line_number == 7
    assert "This looks good" in app.last_result.body


class TestCommentModel:
    def test_comment_fields(self) -> None:
        comment = Comment("src/a.py", 42, "looks good")
        assert comment.file_path == "src/a.py"
        assert comment.line_number == 42
        assert comment.body == "looks good"

    def test_comment_is_immutable(self) -> None:
        """Frozen dataclass should raise FrozenInstanceError on mutation."""
        import dataclasses

        comment = Comment("src/a.py", 1, "body")
        with pytest.raises(dataclasses.FrozenInstanceError):
            comment.body = "changed"  # type: ignore[misc]

    def test_comment_equality(self) -> None:
        c1 = Comment("src/a.py", 10, "hello")
        c2 = Comment("src/a.py", 10, "hello")
        assert c1 == c2
