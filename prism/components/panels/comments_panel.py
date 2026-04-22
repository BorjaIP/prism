from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import LoadingIndicator, Markdown, Static, TabbedContent, TabPane

from prism.models import PRComment, PRReview
from prism.services.github import fetch_comments, fetch_reviews, group_comments_by_file


def _format_comment(comment: PRComment, indent: bool = False) -> str:
    """Render a comment as a Markdown string."""
    prefix = "  " if indent else ""
    timestamp = comment.created_at.strftime("%Y-%m-%d %H:%M")
    location = f"\n{prefix}> `{comment.path}:{comment.line}`" if comment.path else ""
    hunk = (
        f"\n{prefix}```diff\n{comment.diff_hunk}\n{prefix}```"
        if (comment.diff_hunk and not indent)
        else ""
    )
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
    """Displays PR review summaries and per-file inline comments in tabs."""

    DEFAULT_CSS = """
    CommentsPanel {
        width: 42;
        min-width: 20;
    }
    CommentsPanel TabbedContent {
        height: 1fr;
    }
    CommentsPanel TabPane {
        padding: 0 1;
        height: 1fr;
    }
    CommentsPanel #reviews-empty,
    CommentsPanel #inline-empty {
        content-align: center middle;
        color: $text-muted;
        text-style: italic;
        width: 1fr;
        height: 1fr;
    }
    CommentsPanel LoadingIndicator {
        height: 3;
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
        with TabbedContent(id="comments-tabs"):
            with TabPane("Reviews", id="tab-reviews"):
                yield LoadingIndicator(id="reviews-loading")
                yield Static("No reviews yet", id="reviews-empty")
                with VerticalScroll(id="reviews-scroll"):
                    yield Markdown("", id="reviews-content")
            with TabPane("File", id="tab-file"):
                yield Static(
                    "Select a file to see inline comments",
                    id="inline-empty",
                )
                with VerticalScroll(id="inline-scroll"):
                    yield Markdown("", id="inline-content")

    def on_mount(self) -> None:
        self.border_title = "COMMENTS"
        self.query_one("#reviews-empty").display = False
        self.query_one("#reviews-scroll").display = False
        self.query_one("#inline-scroll").display = False
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
        """Store fetched data and update the UI (main thread)."""
        self._all_comments = comments
        self._all_reviews = reviews
        self.query_one("#reviews-loading").display = False
        self._refresh_reviews()
        if self._selected_file:
            self._refresh_inline(self._selected_file)
        total = len(comments) + len(reviews)
        self.border_subtitle = f"{total} threads"

    def set_selected_file(self, path: str) -> None:
        """Filter and re-render inline comments for the selected file."""
        self._selected_file = path
        if self._all_comments is not None:
            self._refresh_inline(path)
            # Auto-switch to File tab if there are inline comments for this file
            by_file = group_comments_by_file(self._all_comments)
            if by_file.get(path):
                try:
                    self.query_one("#comments-tabs", TabbedContent).active = "tab-file"
                except Exception:
                    pass

    def add_comment(self, comment: PRComment) -> None:
        """Prepend a newly posted comment and re-render (main thread)."""
        self._all_comments = [comment, *self._all_comments]
        self._refresh_inline(self._selected_file)

    def _refresh_reviews(self) -> None:
        """Re-render the Reviews tab."""
        scroll = self.query_one("#reviews-scroll")
        empty = self.query_one("#reviews-empty")
        content = self.query_one("#reviews-content", Markdown)

        if self._all_reviews:
            md = "\n".join(_format_review(r) for r in self._all_reviews)
            content.update(md)
            scroll.display = True
            empty.display = False
        else:
            scroll.display = False
            empty.display = True

    def _refresh_inline(self, path: str | None) -> None:
        """Re-render the File tab for the given path."""
        scroll = self.query_one("#inline-scroll")
        empty = self.query_one("#inline-empty")
        content = self.query_one("#inline-content", Markdown)

        if not path:
            scroll.display = False
            empty.display = True
            return

        by_file = group_comments_by_file(self._all_comments)
        file_comments = by_file.get(path, [])

        if file_comments:
            md_parts = [f"## {path}\n\n"]
            for comment in file_comments:
                indent = comment.in_reply_to_id is not None
                md_parts.append(_format_comment(comment, indent=indent))
            content.update("".join(md_parts))
            scroll.display = True
            empty.display = False
            scroll.scroll_home(animate=False)
        else:
            content.update("")
            scroll.display = False
            empty.display = True
