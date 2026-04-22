from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from prism.components.blocks.badges import CHECKS_STATUS_STYLES, REVIEW_STATE_STYLES, STATE_STYLES
from prism.models import PRMetadata


class HeaderBar(Widget):
    """Displays PR title, state badge, branch, and CI status."""

    DEFAULT_CSS = """
    HeaderBar {
        dock: top;
        height: 2;
        background: $primary-background;
        padding: 0 2;
        border-bottom: tall $surface-lighten-2;
    }
    """

    def __init__(self, pr: PRMetadata) -> None:
        super().__init__(id="header-bar")
        self._pr = pr

    def _build_line1(self) -> Text:
        pr = self._pr
        line1 = Text(overflow="ellipsis", no_wrap=True)
        line1.append(f"#{pr.number} ", style="bold cyan")
        line1.append(pr.title, style="bold")
        line1.append("  ")
        label, style = STATE_STYLES.get(pr.state, (pr.state.upper(), "bold"))
        line1.append(f" {label} ", style=style)
        if pr.review_state:
            rs_label, rs_style = REVIEW_STATE_STYLES.get(
                pr.review_state, (f" {pr.review_state} ", "bold")
            )
            line1.append("  ")
            line1.append(rs_label, style=rs_style)
        if pr.checks_status:
            ci_label, ci_style = CHECKS_STATUS_STYLES.get(
                pr.checks_status, (f" {pr.checks_status.upper()} ", "bold")
            )
            line1.append("  ")
            line1.append(ci_label, style=ci_style)
        return line1

    def _build_line2(self) -> Text:
        pr = self._pr
        total_add = sum(f.additions for f in pr.files)
        total_del = sum(f.deletions for f in pr.files)
        line2 = Text(overflow="ellipsis", no_wrap=True)
        line2.append(f"@{pr.author}", style="dim")
        line2.append("  ")
        line2.append(pr.base_branch, style="blue")
        line2.append(" ← ", style="dim")
        line2.append(pr.head_branch, style="blue")
        line2.append(f"  {len(pr.files)} files  ", style="dim")
        line2.append(f"+{total_add}", style="green")
        line2.append(" / ", style="dim")
        line2.append(f"-{total_del}", style="red")
        return line2

    def compose(self) -> ComposeResult:
        yield Static(self._build_line1(), id="header-line1")
        yield Static(self._build_line2(), id="header-line2")

    def update_review_state(self, review_state: str | None) -> None:
        """Refresh the header to show the current review state."""
        self._pr = self._pr.model_copy(update={"review_state": review_state})
        self.query_one("#header-line1", Static).update(self._build_line1())
