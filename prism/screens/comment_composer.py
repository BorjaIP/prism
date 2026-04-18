"""Comment composer modal screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea

from prism.models import Comment


class CommentComposerScreen(ModalScreen[Comment | None]):
    """Modal screen for composing a PR review comment."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("ctrl+s", "submit", "Submit", show=False),
    ]

    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__()
        self._file_path = file_path
        self._line_number = line_number

    def compose(self) -> ComposeResult:
        with Vertical(id="comment-dialog"):
            yield Static(
                f"Commenting on `{self._file_path}` line {self._line_number}",
                id="comment-context",
            )
            yield TextArea(id="comment-area")
            yield Static("", id="comment-error")
            with Horizontal(id="comment-buttons"):
                yield Button("Submit", id="btn-submit", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_mount(self) -> None:
        self.query_one("#comment-area", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            self.action_submit()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_submit(self) -> None:
        body = self.query_one("#comment-area", TextArea).text.strip()
        if not body:
            self.query_one("#comment-error", Static).update("Comment cannot be empty.")
            return
        self.dismiss(Comment(
            file_path=self._file_path,
            line_number=self._line_number,
            body=body,
        ))

    def action_cancel(self) -> None:
        self.dismiss(None)
