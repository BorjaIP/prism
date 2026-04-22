from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea


class QuitConfirmModal(ModalScreen[bool]):
    """Confirmation dialog before exiting prism."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Quit"),
    ]

    DEFAULT_CSS = """
    QuitConfirmModal {
        align: center middle;
    }
    QuitConfirmModal > Vertical {
        width: 40;
        height: auto;
        background: $surface;
        border: round $error;
        padding: 1 2;
    }
    QuitConfirmModal #quit-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }
    QuitConfirmModal Horizontal {
        align: right middle;
        height: auto;
        margin-top: 1;
    }
    QuitConfirmModal Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Quit prism?", id="quit-title")
            yield Label("Any unsaved state will be lost.")
            with Horizontal():
                yield Button("Quit", id="confirm", variant="error")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#confirm", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)


class ApproveConfirmModal(ModalScreen[bool]):
    """Confirmation dialog before submitting an APPROVE review."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Approve"),
    ]

    DEFAULT_CSS = """
    ApproveConfirmModal {
        align: center middle;
    }
    ApproveConfirmModal > Vertical {
        width: 50;
        height: auto;
        background: $surface;
        border: round $success;
        padding: 1 2;
    }
    ApproveConfirmModal Label {
        margin-bottom: 1;
    }
    ApproveConfirmModal #confirm-title {
        text-style: bold;
        color: $success;
    }
    ApproveConfirmModal Horizontal {
        align: right middle;
        height: auto;
        margin-top: 1;
    }
    ApproveConfirmModal Button {
        margin-left: 1;
    }
    """

    def __init__(self, pr_title: str, pr_number: int) -> None:
        super().__init__()
        self._pr_title = pr_title
        self._pr_number = pr_number

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Approve pull request?", id="confirm-title")
            yield Label(f"#{self._pr_number}  {self._pr_title}")
            with Horizontal():
                yield Button("Approve", id="confirm", variant="success")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#confirm", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)


class RequestChangesModal(ModalScreen[str | None]):
    """Modal dialog for collecting a 'request changes' review message."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    RequestChangesModal {
        align: center middle;
    }
    RequestChangesModal > Vertical {
        width: 60;
        height: auto;
        max-height: 20;
        background: $surface;
        border: tall $primary;
        padding: 1 2;
    }
    RequestChangesModal Label {
        margin-bottom: 1;
        text-style: bold;
    }
    RequestChangesModal TextArea {
        height: 8;
        margin-bottom: 1;
    }
    RequestChangesModal Horizontal {
        align: right middle;
        height: auto;
    }
    RequestChangesModal Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Request Changes")
            yield TextArea(id="body-input")
            with Horizontal():
                yield Button("Submit", id="submit", variant="error")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#body-input", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            body = self.query_one("#body-input", TextArea).text
            self.dismiss(body)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
