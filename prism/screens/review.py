"""Review screen — main 3-panel layout for PR code review."""

from __future__ import annotations

import webbrowser

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer

from prism.models import Comment, PRComment, PRMetadata
from prism.screens.comment_composer import CommentComposerScreen
from prism.widgets.comment_list import CommentList
from prism.widgets.comments_panel import CommentsPanel
from prism.widgets.diff_viewer import DiffViewer
from prism.widgets.file_tree import FileTreePanel
from prism.widgets.header_bar import HeaderBar
from prism.widgets.reply_composer import ReplyComposer
from prism.widgets.review_modal import RequestChangesModal


class ReviewScreen(Screen):
    """Three-panel PR review screen: file tree | diff | comments."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "focus_next", "Next panel", show=False),
        Binding("shift+tab", "focus_previous", "Prev panel", show=False),
        Binding("p", "toggle_comments_panel", "Toggle Comments"),
        Binding("c", "compose_comment", "Comment"),
        Binding("a", "approve", "Approve"),
        Binding("r", "request_changes", "Request Changes"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("o", "open_in_browser", "Open in browser"),
    ]

    def __init__(self, pr: PRMetadata, repo_slug: str, pr_number: int) -> None:
        super().__init__()
        self._pr = pr
        self._repo_slug = repo_slug
        self._pr_number = pr_number

    def compose(self) -> ComposeResult:
        yield HeaderBar(self._pr)
        with Horizontal(id="main-content"):
            yield FileTreePanel(self._pr.files)
            yield DiffViewer(self._pr.review_comments)
            yield CommentsPanel(self._repo_slug, self._pr_number)
        yield Footer()

    def on_mount(self) -> None:
        """Auto-select the first file if available."""
        if self._pr.files:
            first_file = self._pr.files[0]
            self.query_one(DiffViewer).show_diff(first_file)
            self.query_one(CommentsPanel).set_selected_file(first_file.filename)

    def on_file_tree_panel_file_selected(
        self, event: FileTreePanel.FileSelected
    ) -> None:
        """Handle file selection from the tree."""
        self.query_one(DiffViewer).show_diff(event.pr_file)
        self.query_one(CommentsPanel).set_selected_file(event.pr_file.filename)

    def action_compose_comment(self) -> None:
        """Open the comment composer modal for the currently selected file."""
        diff = self.query_one(DiffViewer)
        if not diff.current_file:
            self.notify("Select a file first to compose a comment.", severity="warning")
            return
        self.app.push_screen(
            CommentComposerScreen(diff.current_file, diff.current_line),
            callback=self._on_comment_submitted,
        )

    def _on_comment_submitted(self, comment: Comment | None) -> None:
        """Post the comment to GitHub via a background worker."""
        if comment is None:
            return
        if not self._pr.head_sha:
            self.notify("Cannot post: PR head SHA not available.", severity="error")
            return
        self._post_comment(
            body=comment.body,
            path=comment.file_path,
            line=comment.line_number,
        )

    @work(thread=True)
    def _post_comment(self, body: str, path: str, line: int) -> None:
        """Post a comment to GitHub in a background thread."""
        from github import GithubException
        from prism.services.github import post_comment

        try:
            comment = post_comment(
                repo_slug=self._repo_slug,
                pr_number=self._pr_number,
                commit_id=self._pr.head_sha,
                path=path,
                line=line,
                body=body,
            )
            self.app.call_from_thread(
                self.query_one(CommentsPanel).add_comment, comment
            )
            self.app.call_from_thread(
                self.notify,
                f"Comment posted on {path}:{line}",
                severity="information",
            )
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(
                self.notify, f"GitHub error: {msg}", severity="error"
            )
        except RuntimeError as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Failed to post comment: {e}", severity="error"
            )

    def action_approve(self) -> None:
        """Submit an APPROVE review to GitHub in a background thread."""
        self._do_approve()

    @work(thread=True)
    def _do_approve(self) -> None:
        """Background worker that submits the APPROVE review."""
        from github import GithubException
        from prism.services.github import submit_review

        try:
            submit_review(self._repo_slug, self._pr_number, event="APPROVE")
            self._pr = self._pr.model_copy(update={"review_state": "APPROVED"})
            self.app.call_from_thread(self._update_header)
            self.app.call_from_thread(
                self.notify, "PR approved", severity="information"
            )
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(
                self.notify, f"Approve failed: {msg}", severity="error"
            )
        except RuntimeError as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Approve failed: {e}", severity="error"
            )

    def action_request_changes(self) -> None:
        """Open the request changes modal."""
        self.app.push_screen(
            RequestChangesModal(),
            callback=self._on_request_changes_submitted,
        )

    def _on_request_changes_submitted(self, body: str | None) -> None:
        """Submit REQUEST_CHANGES review if the user provided a body."""
        if body is None:
            return
        self._do_request_changes(body)

    @work(thread=True)
    def _do_request_changes(self, body: str) -> None:
        """Background worker that submits the REQUEST_CHANGES review."""
        from github import GithubException
        from prism.services.github import submit_review

        try:
            submit_review(
                self._repo_slug,
                self._pr_number,
                event="REQUEST_CHANGES",
                body=body,
            )
            self._pr = self._pr.model_copy(update={"review_state": "CHANGES_REQUESTED"})
            self.app.call_from_thread(self._update_header)
            self.app.call_from_thread(
                self.notify, "Changes requested", severity="warning"
            )
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(
                self.notify, f"Request changes failed: {msg}", severity="error"
            )
        except RuntimeError as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Request changes failed: {e}", severity="error"
            )

    def _update_header(self) -> None:
        """Refresh the HeaderBar to reflect the current review state."""
        self.query_one(HeaderBar).update_review_state(self._pr.review_state)

    def on_comment_list_reply_requested(
        self, event: CommentList.ReplyRequested
    ) -> None:
        """Open the reply composer modal when a comment reply is requested."""
        self.app.push_screen(
            ReplyComposer(event.comment),
            callback=self._on_reply_submitted,
        )

    def _on_reply_submitted(self, body: str | None) -> None:
        """Post the reply to GitHub via a background worker."""
        if not body:
            return
        diff = self.query_one(DiffViewer)
        # Find the focused comment from the CommentList
        comment_list = diff.query_one(CommentList)
        from textual.widgets import ListView
        lv = comment_list.query_one(ListView)
        index = lv.index
        if index is None:
            return
        # Access the comment that triggered the reply via the stored list
        if index < len(comment_list._comments):
            comment = comment_list._comments[index]
            self._do_post_reply(comment, body)

    @work(thread=True)
    def _do_post_reply(self, parent_comment: PRComment, body: str) -> None:
        """Post an in-thread reply to GitHub in a background thread."""
        from github import GithubException
        from prism.services.github import post_reply

        try:
            reply = post_reply(
                repo_slug=self._repo_slug,
                pr_number=self._pr_number,
                comment_id=parent_comment.id,
                body=body,
            )
            self.app.call_from_thread(
                self.query_one(CommentsPanel).add_comment, reply
            )
            self.app.call_from_thread(
                self.notify, "Reply posted", severity="information"
            )
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(
                self.notify, f"Reply failed: {msg}", severity="error"
            )
        except RuntimeError as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Reply failed: {e}", severity="error"
            )

    def action_toggle_comments_panel(self) -> None:
        """Toggle visibility of the comments panel."""
        panel = self.query_one(CommentsPanel)
        panel.display = not panel.display

    def action_refresh(self) -> None:
        """Placeholder for PR data refresh."""
        self.notify("Refreshing PR data...", severity="information")

    def action_open_in_browser(self) -> None:
        """Open the PR in the default browser."""
        if self._pr.html_url:
            webbrowser.open(self._pr.html_url)
            self.notify(f"Opened PR #{self._pr.number} in browser")
