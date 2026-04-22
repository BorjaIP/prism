"""AI analysis panel — placeholder for Phase 3."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Markdown

PLACEHOLDER_MD = """\
## AI Analysis

*Coming in Phase 3*

This panel will show:
- **Summary** of the selected file's changes
- **Risk level** badge (low / medium / high)
- **Concerns** raised by Claude
- **Suggested comments** for the review

Press `i` to toggle this panel.
"""


class AIPanel(Widget):
    """Placeholder for AI-powered file analysis."""

    DEFAULT_CSS = """
    AIPanel {
        width: 32;
        min-width: 20;
        padding: 1 1;
    }
    """

    def __init__(self) -> None:
        super().__init__(id="ai-panel")

    def on_mount(self) -> None:
        self.border_title = "AI"

    def compose(self) -> ComposeResult:
        yield Markdown(PLACEHOLDER_MD)
