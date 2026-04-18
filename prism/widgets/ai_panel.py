"""AI analysis panel — placeholder for Phase 3."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Markdown

PLACEHOLDER_MD = """\
# AI Analysis

*Coming in Phase 3*

This panel will show:
- **Summary** of the selected file's changes
- **Risk level** badge (low / medium / high)
- **Concerns** raised by Claude
- **Suggested comments** for the review

Press `p` to toggle this panel.
"""


class AIPanel(Widget):
    """Placeholder for AI-powered file analysis."""

    DEFAULT_CSS = """
    AIPanel {
        width: 35;
        min-width: 20;
        border-left: tall $primary-background;
        padding: 1 2;
    }
    AIPanel:focus-within {
        border-left: tall $accent;
    }
    """

    def __init__(self) -> None:
        super().__init__(id="ai-panel")

    def compose(self) -> ComposeResult:
        yield Markdown(PLACEHOLDER_MD)
