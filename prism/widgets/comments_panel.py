"""Comments panel — displays threaded PR review comments."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import LoadingIndicator, Markdown, Static
from textual.containers import VerticalScroll

from prism.models import PRComment, PRReview
from prism.services.github import fetch_comments, fetch_reviews, group_comments_by_file


def _format_comment(comment: PRComment, indent: bool = False) -> str:
    """Render a comment as a Markdown string."""
    prefix = "  " if indent else ""
    timestamp = comment.created_at.strftime("%Y-%m-%d %H:%M")
    location = f"\n{prefix}> `{comment.path}:{comment.line}`" if comment.path else ""
    hunk = f"\n{prefix}```diff\n{comment.diff_hunk}\n{prefix}```" if (comment.diff_hunk and not indent) else ""
    return (
        f"{prefix}**@{comment.author}** · {timestamp}{location}{hunk}\n\n"
        f"{prefix}{comment.body}\n\n"
        f"{prefix}---\n"
    )


def _format_review(review: PRReview) -> str:
    """Render a review summary as a Markdown string."""
    timestamp = review.submitted_at.strftime("%Y-%m-%d %H:%M")
    state_icon = {
        "APPROVED": "✅",
        "CHANGES_REQUESTED": "🔴",
        "COMMENTED": "💬",
        "DISMISSED": "⬜",
    }.get(review.state, "❓")
    body = f"\n\n{review.body}" if review.body else ""
    return f"{state_icon} **@{review.author}** · {review.state} · {timestamp}{body}\n\n---\n"


class CommentsPanel(Widget):
    """Displays threaded PR inline comments and review summaries."""

    DEFAULT_CSS = """
    CommentsPanel {
        width: 35;
        min-width: 20;
        border-left: tall $primary-background;
        padding: 1 2;
    }
    CommentsPanel:focus-within {
        border-left: tall $accent;
    }
    CommentsPanel #comments-empty {
        content-align: center middle;
        color: $text-muted;
        text-style: italic;
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(self, repo_slug: str, pr_number: int) -> None:
        super().__init__(id="comments-panel")
        self._repo_slug = repo_slug
        self._pr_number = pr_number
        self._all_comments: list[PRComment] = []
        self._all_reviews: list[PRReview] = []
        self._selected_file: str | None = None

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="comments-loading")
        yield Static("No comments", id="comments-empty")
        with VerticalScroll(id="comments-scroll"):
            yield Markdown("", id="comments-content")

    def on_mount(self) -> None:
        self.query_one("#comments-empty").display = False
        self.query_one("#comments-scroll").display = False
        self._fetch_data()

    @work(thread=True, exclusive=True)
    def _fetch_data(self) -> None:
        """Fetch comments and reviews in a background thread."""
        comments = fetch_comments(self._repo_slug, self._pr_number)
        reviews = fetch_reviews(self._repo_slug, self._pr_number)
        self.app.call_from_thread(self._on_data_loaded, comments, reviews)

    def _on_data_loaded(
        self, comments: list[PRComment], reviews: list[PRReview]
    ) -> None:
        """Store fetched data and update the UI (called on main thread)."""
        self._all_comments = comments
        self._all_reviews = reviews
        self.query_one("#comments-loading").display = False
        self._refresh_comments(self._selected_file)

    def set_selected_file(self, path: str) -> None:
        """Filter and re-render comments for the selected file."""
        self._selected_file = path
        if self._all_comments or self._all_reviews:
            self._refresh_comments(path)

    def add_comment(self, comment: PRComment) -> None:
        """Prepend a newly posted comment and re-render (called on main thread)."""
        self._all_comments = [comment, *self._all_comments]
        self._refresh_comments(self._selected_file)

    def _refresh_comments(self, path: str | None) -> None:
        """Re-render the comments scroll area for the given file path."""
        scroll = self.query_one("#comments-scroll")
        empty = self.query_one("#comments-empty")
        content = self.query_one("#comments-content", Markdown)

        md_parts: list[str] = []

        # Review summaries (always shown)
        if self._all_reviews:
            md_parts.append("## Reviews\n\n")
            for review in self._all_reviews:
                md_parts.append(_format_review(review))

        # Inline comments filtered by file
        if path:
            by_file = group_comments_by_file(self._all_comments)
            file_comments = by_file.get(path, [])
            if file_comments:
                md_parts.append(f"\n## {path}\n\n")
                for comment in file_comments:
                    indent = comment.in_reply_to_id is not None
                    md_parts.append(_format_comment(comment, indent=indent))

        if md_parts:
            scroll.display = True
            empty.display = False
            content.update("".join(md_parts))
            scroll.scroll_home(animate=False)
        elif not self._all_reviews:
            scroll.display = False
            empty.display = True
