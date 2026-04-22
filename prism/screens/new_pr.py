"""New PR screen — input a GitHub URL or repo+number to open a PR."""

from __future__ import annotations

import re

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

_GITHUB_PR_URL_RE = re.compile(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)")


def _parse(value: str) -> tuple[str, int] | None:
    """Parse a GitHub PR URL or 'owner/repo number' string."""
    value = value.strip()
    m = _GITHUB_PR_URL_RE.match(value.rstrip("/"))
    if m:
        return m.group(1), int(m.group(2))
    # Try "owner/repo number" or "owner/repo#number"
    m2 = re.match(r"([^/]+/[^/\s#]+)[#\s]+(\d+)$", value)
    if m2:
        return m2.group(1), int(m2.group(2))
    return None


class NewPRScreen(ModalScreen[tuple[str, int] | None]):
    """Modal input for opening a PR by URL or repo+number."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    NewPRScreen {
        align: center middle;
    }
    #new-pr-dialog {
        width: 72;
        height: auto;
        background: $surface;
        border: round $accent;
        padding: 1 2;
    }
    #new-pr-label {
        color: $text-muted;
        margin-bottom: 1;
    }
    #new-pr-input {
        margin-bottom: 1;
    }
    #new-pr-error {
        color: $error;
        height: 1;
        margin-bottom: 1;
    }
    #new-pr-buttons {
        layout: horizontal;
        align: right middle;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="new-pr-dialog"):
            yield Label("GitHub PR URL  or  owner/repo #number", id="new-pr-label")
            yield Input(
                placeholder="https://github.com/owner/repo/pull/42",
                id="new-pr-input",
            )
            yield Label("", id="new-pr-error")
            with Vertical(id="new-pr-buttons"):
                yield Button("Open", variant="primary", id="new-pr-open")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-pr-open":
            self._submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        value = self.query_one(Input).value
        parsed = _parse(value)
        if parsed is None:
            self.query_one("#new-pr-error", Label).update(
                "Invalid format. Use a GitHub URL or 'owner/repo 42'."
            )
            return
        self.dismiss(parsed)

    def action_cancel(self) -> None:
        self.dismiss(None)
