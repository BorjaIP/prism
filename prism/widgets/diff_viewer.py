"""Diff viewer panel — renders syntax-highlighted diffs."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import RichLog, Static

from prism.models import PRComment, PRFile
from prism.services.diff import render_diff
from prism.widgets.comment_list import CommentList


class DiffViewer(Widget):
    """Displays the diff for a selected file using delta or plain coloring."""

    DEFAULT_CSS = """
    DiffViewer {
        width: 1fr;
    }
    DiffViewer RichLog {
        padding: 0 1;
    }
    DiffViewer #diff-placeholder {
        content-align: center middle;
        color: $text-muted;
        text-style: italic;
        width: 1fr;
        height: 1fr;
    }
    DiffViewer Vertical {
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(self, review_comments: list[PRComment] | None = None) -> None:
        super().__init__(id="diff-viewer")
        self._review_comments: list[PRComment] = review_comments or []
        self._current_file: str = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Select a file to view its diff", id="diff-placeholder")
            yield RichLog(highlight=False, markup=False, wrap=False, id="diff-log")
            yield CommentList()

    def on_mount(self) -> None:
        self.border_title = "DIFF"
        self.query_one("#diff-log", RichLog).display = False

    @property
    def current_file(self) -> str:
        """Return the currently displayed file path."""
        return self._current_file

    @property
    def current_line(self) -> int:
        """Return the current line number context (0 until precise tracking is added)."""
        return 0

    def set_review_comments(self, comments: list[PRComment]) -> None:
        """Replace the cached review comments (called after refresh)."""
        self._review_comments = comments

    def show_diff(self, pr_file: PRFile) -> None:
        """Load and display the diff for the given file."""
        from pathlib import PurePosixPath

        self._current_file = pr_file.filename
        basename = PurePosixPath(pr_file.filename).name
        self.border_title = f"DIFF  {basename}"
        self.border_subtitle = f"+{pr_file.additions} -{pr_file.deletions}"
        self._load_diff(pr_file)
        file_comments = [
            c for c in self._review_comments if c.path == pr_file.filename
        ]
        self.query_one(CommentList).set_comments(file_comments)

    @work(thread=True, exclusive=True)
    def _load_diff(self, pr_file: PRFile) -> None:
        """Render the diff in a background thread (delta is blocking)."""
        log = self.query_one("#diff-log", RichLog)
        placeholder = self.query_one("#diff-placeholder", Static)

        self.app.call_from_thread(placeholder.__setattr__, "display", False)
        self.app.call_from_thread(log.__setattr__, "display", True)
        self.app.call_from_thread(log.clear)

        width = self.size.width - 2
        text = render_diff(pr_file.patch or "", width=max(width, 40))

        self.app.call_from_thread(log.write, text)
