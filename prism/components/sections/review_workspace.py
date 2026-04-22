"""Review workspace section — full panel layout for PR code review."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget

from prism.components.blocks.resizer import PanelResizer
from prism.components.panels.ai_panel import AIPanel
from prism.components.panels.comments_panel import CommentsPanel
from prism.components.panels.diff_viewer import DiffViewer
from prism.components.panels.file_tree import FileTreePanel
from prism.models import PRMetadata


class ReviewWorkspace(Widget):
    """Horizontal panel layout: file tree | diff | comments | AI.

    Replaces the inline Horizontal container in ReviewScreen, making the
    multi-panel layout independently composable and testable. The widget is
    given id='main-content' so existing CSS selectors (``#main-content``) and
    Textual queries from the parent screen continue to work without changes.
    """

    def __init__(
        self,
        pr: PRMetadata,
        repo_slug: str,
        pr_number: int,
        show_ai: bool = True,
    ) -> None:
        super().__init__(id="main-content")
        self._pr = pr
        self._repo_slug = repo_slug
        self._pr_number = pr_number
        self._show_ai = show_ai

    def compose(self) -> ComposeResult:
        yield FileTreePanel(self._pr.files, self._pr.review_comments)
        yield PanelResizer("file-tree-panel", "diff-viewer")
        yield DiffViewer(self._pr.review_comments)
        yield PanelResizer("diff-viewer", "comments-panel")
        yield CommentsPanel(self._repo_slug, self._pr_number)
        yield PanelResizer("comments-panel", "ai-panel")
        ai = AIPanel(self._pr, self._repo_slug, self._pr_number)
        if not self._show_ai:
            ai.display = False
        yield ai
