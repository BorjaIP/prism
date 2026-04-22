from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Static

from prism.components.modals.jumper import Jumper


class JumpOverlay(ModalScreen[Widget | None]):
    """Transparent overlay that shows letter hints and jumps on keypress."""

    DEFAULT_CSS = """
    JumpOverlay {
        background: transparent;
    }
    JumpOverlay #jump-help {
        dock: bottom;
        height: 1;
        background: $primary-background;
        color: $accent;
        padding: 0 2;
    }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel jump mode")]

    def __init__(self, jumper: Jumper) -> None:
        super().__init__()
        self._jumper = jumper

    def compose(self) -> ComposeResult:
        assignments = self._jumper.assignments
        parts = [f"[bold]{key}[/bold] {label}" for key, (label, _) in sorted(assignments.items())]
        hint_text = "  ".join(parts) + "  [dim]esc to cancel[/dim]"
        yield Static(hint_text, id="jump-help", markup=True)

    def on_key(self, event) -> None:
        """Resolve the pressed key to a widget and dismiss with it."""
        widget = self._jumper.resolve(event.key)
        if widget is not None:
            event.prevent_default()
            self.dismiss(widget)

    def action_cancel(self) -> None:
        self.dismiss(None)
