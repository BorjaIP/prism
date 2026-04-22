from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Static

from prism.components.blocks.comment_item import comment_label
from prism.models import PRComment


class CommentList(Widget):
    """Focusable list of inline review comments with reply support."""

    class ReplyRequested(Message):
        """Posted when the user requests a reply to a comment."""

        def __init__(self, comment: PRComment) -> None:
            super().__init__()
            self.comment = comment

    BINDINGS = [
        Binding("r", "reply", "Reply to comment"),
    ]

    DEFAULT_CSS = """
    CommentList {
        height: auto;
        max-height: 10;
        border-top: solid $primary-background;
    }
    CommentList:focus-within {
        border-top: solid $accent;
    }
    CommentList ListView {
        height: auto;
        max-height: 10;
        background: $surface;
    }
    CommentList #comment-list-empty {
        padding: 0 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(self) -> None:
        super().__init__(id="comment-list")
        self._comments: list[PRComment] = []

    def compose(self) -> ComposeResult:
        yield Static("No comments for this file", id="comment-list-empty")
        yield ListView(id="comment-listview")

    def on_mount(self) -> None:
        self.query_one("#comment-listview", ListView).display = False

    def set_comments(self, comments: list[PRComment]) -> None:
        """Replace the displayed comments for the current file."""
        self._comments = comments
        lv = self.query_one("#comment-listview", ListView)
        empty = self.query_one("#comment-list-empty", Static)

        lv.clear()
        if comments:
            for comment in comments:
                lv.append(ListItem(Static(comment_label(comment))))
            lv.display = True
            empty.display = False
        else:
            lv.display = False
            empty.display = True

    def action_reply(self) -> None:
        """Post a ReplyRequested message for the focused comment."""
        lv = self.query_one("#comment-listview", ListView)
        index = lv.index
        if index is not None and 0 <= index < len(self._comments):
            self.post_message(self.ReplyRequested(self._comments[index]))
