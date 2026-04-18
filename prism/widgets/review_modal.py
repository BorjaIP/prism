"""Modal dialog for composing a 'request changes' review message."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea


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
