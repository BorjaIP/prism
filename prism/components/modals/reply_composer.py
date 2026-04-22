from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea

from prism.models import PRComment


class ReplyComposer(ModalScreen[str | None]):
    """Modal dialog for writing an in-thread reply to a review comment."""

    BINDINGS = [
        Binding("ctrl+s", "submit", "Submit reply"),
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ReplyComposer {
        align: center middle;
    }
    ReplyComposer > Vertical {
        width: 65;
        height: auto;
        max-height: 22;
        background: $surface;
        border: tall $primary;
        padding: 1 2;
    }
    ReplyComposer #reply-context {
        margin-bottom: 1;
        color: $text-muted;
        text-style: italic;
    }
    ReplyComposer #reply-area {
        height: 8;
        margin-bottom: 1;
    }
    ReplyComposer #reply-error {
        color: $error;
        height: 1;
        margin-bottom: 1;
    }
    ReplyComposer Horizontal {
        align: right middle;
        height: auto;
    }
    ReplyComposer Button {
        margin-left: 1;
    }
    """

    def __init__(self, parent_comment: PRComment) -> None:
        super().__init__()
        self._comment = parent_comment

    def compose(self) -> ComposeResult:
        context = f"Reply to @{self._comment.author}"
        if self._comment.line:
            context += f" on line {self._comment.line}"
        with Vertical():
            yield Label(context, id="reply-context")
            yield TextArea(id="reply-area")
            yield Label("", id="reply-error")
            with Horizontal():
                yield Button("Submit", id="submit", variant="primary")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#reply-area", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self._do_submit()
        else:
            self.dismiss(None)

    def action_submit(self) -> None:
        self._do_submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _do_submit(self) -> None:
        body = self.query_one("#reply-area", TextArea).text.strip()
        if not body:
            self.query_one("#reply-error", Label).update("Reply cannot be empty.")
            return
        self.dismiss(body)
