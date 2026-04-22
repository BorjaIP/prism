"""PR preview widget — right panel for the PR selection screen."""

from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from prism.models import PRSummary

_CI_LABELS = {
    "success": ("✓ passing", "green"),
    "failure": ("✗ failing", "red"),
    "error": ("✗ error", "red"),
    "pending": ("… pending", "yellow"),
}

_REVIEW_LABELS = {
    "APPROVED": ("✓ approved", "green"),
    "CHANGES_REQUESTED": ("! changes requested", "red"),
}

_STATE_STYLES = {
    "open": ("open", "bold green"),
    "merged": ("merged", "bold magenta"),
    "closed": ("closed", "bold red"),
}


def _build_preview(summary: PRSummary) -> RenderableType:
    lines = Text()

    # Title
    state_label, state_style = _STATE_STYLES.get(summary.state, (summary.state, "bold"))
    lines.append(f"#{summary.number} ", style="bold dim")
    lines.append(f"[{state_label}]", style=state_style)
    lines.append("\n")
    lines.append(summary.title + "\n", style="bold")
    lines.append("\n")

    # Branch info
    lines.append(f"{summary.base_branch}", style="dim")
    lines.append(" ← ", style="dim")
    lines.append(f"{summary.head_branch}\n", style="cyan")
    lines.append(f"by @{summary.author}\n", style="dim")
    lines.append("\n")

    # CI status
    if summary.checks_status:
        ci_label, ci_style = _CI_LABELS.get(summary.checks_status, (summary.checks_status, "white"))
        lines.append("CI: ", style="bold")
        lines.append(ci_label + "\n", style=ci_style)

    # Review status
    if summary.review_state:
        rv_label, rv_style = _REVIEW_LABELS.get(summary.review_state, (summary.review_state, "white"))
        lines.append("Review: ", style="bold")
        lines.append(rv_label + "\n", style=rv_style)

    if summary.comments:
        lines.append(f"Comments: {summary.comments}\n", style="dim")

    # Description
    if summary.body.strip():
        lines.append("\n")
        lines.append("─" * 30 + "\n", style="dim")
        # Show first ~10 lines of description
        body_lines = summary.body.strip().splitlines()
        snippet = "\n".join(body_lines[:10])
        if len(body_lines) > 10:
            snippet += f"\n… ({len(body_lines) - 10} more lines)"
        lines.append(snippet + "\n", style="dim")

    lines.append("\n")
    lines.append("─" * 30 + "\n", style="dim")
    lines.append("enter", style="bold cyan")
    lines.append("  open for review\n", style="dim")
    lines.append("o", style="bold cyan")
    lines.append("  open in browser\n", style="dim")

    return lines


class PRPreviewWidget(Widget):
    """Right panel showing details of the currently highlighted PR."""

    BORDER_TITLE = "Preview"

    def __init__(self, widget_id: str = "pr-preview-widget") -> None:
        super().__init__(id=widget_id)

    def compose(self) -> ComposeResult:
        yield Static(
            Text("Select a PR to preview", style="dim italic"),
            id="pr-preview-content",
        )

    def update(self, summary: PRSummary) -> None:
        """Render the given PR summary into the preview panel."""
        self.query_one("#pr-preview-content", Static).update(_build_preview(summary))
