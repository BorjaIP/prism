"""PR list widget — DataTable-based left panel for the PR selection screen."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.text import Text
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable

from prism.components.blocks.badges import CI_ICONS, REVIEW_ICONS, STATE_COLORS
from prism.models import PRSummary


def _relative_time(dt: datetime) -> str:
    now = datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    if days < 30:
        return f"{days}d"
    months = days // 30
    return f"{months}mo"


class PRListWidget(Widget):
    """DataTable showing a list of pull requests."""

    BORDER_TITLE = "Recently Reviewed"

    class PRSelected(Message):
        """Posted when the user presses Enter on a PR row."""

        def __init__(self, summary: PRSummary, source_id: str) -> None:
            super().__init__()
            self.summary = summary
            self.source_id = source_id

    class PRHighlighted(Message):
        """Posted when the cursor moves to a new PR row (for preview updates)."""

        def __init__(self, summary: PRSummary, source_id: str) -> None:
            super().__init__()
            self.summary = summary
            self.source_id = source_id

    def __init__(self, widget_id: str = "pr-list-widget") -> None:
        super().__init__(id=widget_id)
        self._summaries: list[PRSummary] = []

    def compose(self):
        table: DataTable = DataTable(cursor_type="row", zebra_stripes=True)
        table.add_columns(
            Text("Updated", style="bold"),
            Text("#", style="bold"),
            Text("Title", style="bold"),
            Text("Repo", style="bold"),
            Text("CI", style="bold"),
            Text("Review", style="bold"),
        )
        yield table

    def on_focus(self) -> None:
        """Forward focus to the inner DataTable so Enter/arrows work."""
        self.query_one(DataTable).focus()

    def load(self, summaries: list[PRSummary]) -> None:
        """Replace the table rows with a new list of summaries."""
        self._summaries = summaries
        table = self.query_one(DataTable)
        table.clear()
        for summary in summaries:
            updated = _relative_time(summary.updated_at)
            ci_icon, ci_color = CI_ICONS.get(summary.checks_status or "", ("·", "dim"))
            review_icon, review_color = REVIEW_ICONS.get(summary.review_state or "", ("·", "dim"))
            state_color = STATE_COLORS.get(summary.state, "white")
            table.add_row(
                updated,
                Text(str(summary.number), style=state_color),
                summary.title,
                summary.repo_slug.split("/")[-1],
                Text(ci_icon, style=ci_color),
                Text(review_icon, style=review_color),
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        idx = event.cursor_row
        if 0 <= idx < len(self._summaries):
            self.post_message(self.PRHighlighted(self._summaries[idx], self.id or ""))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        idx = event.cursor_row
        if 0 <= idx < len(self._summaries):
            self.post_message(self.PRSelected(self._summaries[idx], self.id or ""))

    def on_key(self, event) -> None:
        table = self.query_one(DataTable)
        if event.key == "j":
            table.action_cursor_down()
            event.stop()
        elif event.key == "k":
            table.action_cursor_up()
            event.stop()
