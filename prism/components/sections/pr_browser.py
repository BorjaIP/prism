"""PR browser section — horizontal split of PR list and preview panels."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget

from prism.components.sections.pr_list_widget import PRListWidget
from prism.components.sections.pr_preview_widget import PRPreviewWidget


class PRBrowserSection(Widget):
    """Horizontal section composing a PR list (left) and PR preview (right).

    Use this section to embed a standard PR browsing layout inside a screen or
    tab pane. The inner widgets are addressable by their IDs via the normal
    Textual query API.
    """

    def __init__(
        self,
        list_id: str = "pr-list-widget",
        preview_id: str = "pr-preview-widget",
        section_id: str | None = None,
    ) -> None:
        super().__init__(id=section_id)
        self._list_id = list_id
        self._preview_id = preview_id

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield PRListWidget(widget_id=self._list_id)
            yield PRPreviewWidget(widget_id=self._preview_id)
