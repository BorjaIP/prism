from __future__ import annotations

import subprocess
import webbrowser

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer

from prism.components.modals.comment_composer import CommentComposerScreen
from prism.components.modals.reply_composer import ReplyComposer
from prism.components.modals.review_modals import (
    ApproveConfirmModal,
    QuitConfirmModal,
    RequestChangesModal,
)
from prism.components.panels.ai_panel import AIPanel
from prism.components.panels.comment_list import CommentList
from prism.components.panels.comments_panel import CommentsPanel
from prism.components.panels.diff_viewer import DiffViewer
from prism.components.panels.file_tree import FileTreePanel
from prism.components.sections.header_bar import HeaderBar
from prism.components.sections.review_workspace import ReviewWorkspace
from prism.models import Comment, PRComment, PRMetadata

_PANEL_CYCLE = [None, "diff", "comments"]


class ReviewScreen(Screen):
    """Three-panel PR review screen: file tree | diff | comments."""

    BINDING_GROUP_TITLE = "PR Review"

    BINDINGS = [
        Binding("q", "request_quit", "Quit", id="quit", tooltip="Exit prism"),
        Binding("tab", "focus_next", "Next panel", show=False, id="focus-next"),
        Binding(
            "shift+tab",
            "action_focus_previous",
            "Prev panel",
            show=False,
            id="focus-prev",
        ),
        Binding(
            "p",
            "toggle_comments_panel",
            "Toggle Comments",
            id="toggle-comments",
            tooltip="Show/hide the comments panel",
        ),
        Binding(
            "c",
            "compose_comment",
            "Comment",
            id="compose-comment",
            tooltip="Write an inline comment on the selected line",
        ),
        Binding(
            "a",
            "approve",
            "Approve",
            id="approve",
            tooltip="Submit an APPROVE review",
        ),
        Binding(
            "r",
            "request_changes",
            "Request Changes",
            id="request-changes",
            tooltip="Submit a REQUEST_CHANGES review",
        ),
        Binding(
            "ctrl+r",
            "refresh",
            "Refresh",
            id="refresh",
            tooltip="Re-fetch PR data from GitHub",
        ),
        Binding(
            "o",
            "open_in_browser",
            "Open in browser",
            id="open-browser",
            tooltip="Open the PR in your default browser",
        ),
        Binding(
            "y",
            "copy_url",
            "Copy URL",
            id="copy-url",
            tooltip="Copy the PR URL to the clipboard",
        ),
        Binding(
            "e",
            "open_in_editor",
            "Open in editor",
            id="open-editor",
            tooltip="Open the selected file in $EDITOR",
        ),
        Binding(
            "ctrl+m",
            "cycle_expand",
            "Expand panel",
            id="cycle-expand",
            tooltip="Cycle through expanded panel modes (diff / comments / normal)",
        ),
        Binding(
            "ctrl+o",
            "jump_mode",
            "Jump",
            id="jump-mode",
            tooltip="Activate jump mode to focus a panel with a single keypress",
        ),
        Binding(
            "i",
            "toggle_ai_panel",
            "AI panel",
            id="toggle-ai",
            tooltip="Show/hide the AI analysis panel",
        ),
        Binding(
            "S",
            "reanalyze",
            "Re-analyze",
            id="reanalyze",
            tooltip="Force re-analyze the current file with AI (bypasses cache)",
        ),
        Binding(
            "ctrl+s",
            "post_suggestion",
            "Post AI suggestion",
            id="post-suggestion",
            tooltip="Post the AI-suggested comment to the PR",
            show=False,
        ),
    ]

    # Tracks which panel is currently expanded ("diff" | "comments" | None)
    expanded_panel: reactive[str | None] = reactive(None)

    def __init__(self, pr: PRMetadata, repo_slug: str, pr_number: int) -> None:
        super().__init__()
        self._pr = pr
        self._repo_slug = repo_slug
        self._pr_number = pr_number

    def compose(self) -> ComposeResult:
        from prism.config import load_config

        config = load_config()
        yield HeaderBar(self._pr)
        yield ReviewWorkspace(
            self._pr, self._repo_slug, self._pr_number, show_ai=config.show_ai_panel
        )
        yield Footer()

    def on_mount(self) -> None:
        """Auto-select the first file if available."""
        if self._pr.files:
            first_file = self._pr.files[0]
            self.query_one(DiffViewer).show_diff(first_file)
            self.query_one(CommentsPanel).set_selected_file(first_file.filename)
            self.query_one(AIPanel).set_file(first_file)

    # ── Reactive layout expand ──────────────────────────────────────────────

    def watch_expanded_panel(self, panel: str | None) -> None:
        """Expand one panel by setting inline widths (overrides resized state)."""
        diff = self.query_one(DiffViewer)
        comments = self.query_one(CommentsPanel)
        if panel == "diff":
            diff.styles.width = "4fr"
            comments.styles.width = 32
        elif panel == "comments":
            diff.styles.width = "1fr"
            comments.styles.width = "4fr"
        else:
            diff.styles.width = "1fr"
            comments.styles.width = 42

    def action_cycle_expand(self) -> None:
        """Cycle expanded_panel through None → diff → comments → None."""
        current = self.expanded_panel
        idx = _PANEL_CYCLE.index(current) if current in _PANEL_CYCLE else 0
        self.expanded_panel = _PANEL_CYCLE[(idx + 1) % len(_PANEL_CYCLE)]

    # ── File selection ──────────────────────────────────────────────────────

    def on_file_tree_panel_file_selected(self, event: FileTreePanel.FileSelected) -> None:
        """Handle file selection from the tree."""
        self.query_one(DiffViewer).show_diff(event.pr_file)
        self.query_one(CommentsPanel).set_selected_file(event.pr_file.filename)
        self.query_one(AIPanel).set_file(event.pr_file)

    def on_ai_panel_analysis_complete(self, event: AIPanel.AnalysisComplete) -> None:
        """Propagate AI risk level to the file tree badge."""
        self.query_one(FileTreePanel).update_risk_badge(event.filename, event.analysis.risk)

    # ── Real refresh ────────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        """Re-fetch PR data from GitHub."""
        self.notify("Refreshing PR data…", severity="information")
        self._do_refresh()

    @work(thread=True, exclusive=True)
    def _do_refresh(self) -> None:
        """Background worker: fetch fresh PR data and update widgets."""
        from github import GithubException

        from prism.services.github import fetch_pr

        try:
            pr = fetch_pr(self._repo_slug, self._pr_number)
            self.app.call_from_thread(self._apply_refresh, pr)
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(self.notify, f"Refresh failed: {msg}", severity="error")
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Refresh failed: {e}", severity="error")

    def _apply_refresh(self, pr: PRMetadata) -> None:
        """Update all widgets with freshly fetched PR data (main thread)."""
        self._pr = pr
        self.query_one(FileTreePanel).set_files(pr.files, pr.review_comments)
        self.query_one(DiffViewer).set_review_comments(pr.review_comments)
        self.query_one(HeaderBar).update_review_state(pr.review_state)
        # Re-select the currently displayed file to refresh diff + inline comments
        current = self.query_one(DiffViewer).current_file
        if current:
            matching = next((f for f in pr.files if f.filename == current), None)
            if matching:
                self.query_one(DiffViewer).show_diff(matching)
                self.query_one(CommentsPanel).set_selected_file(current)
        self.notify("PR data refreshed", severity="information")

    # ── Comment composer ────────────────────────────────────────────────────

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
            self.app.call_from_thread(self.query_one(CommentsPanel).add_comment, comment)
            self.app.call_from_thread(
                self.notify,
                f"Comment posted on {path}:{line}",
                severity="information",
            )
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(self.notify, f"GitHub error: {msg}", severity="error")
        except RuntimeError as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Failed to post comment: {e}", severity="error")

    # ── Approve / Request changes ───────────────────────────────────────────

    def action_approve(self) -> None:
        self.app.push_screen(
            ApproveConfirmModal(self._pr.title, self._pr.number),
            callback=self._on_approve_confirmed,
        )

    def _on_approve_confirmed(self, confirmed: bool) -> None:
        if confirmed:
            self._do_approve()

    @work(thread=True)
    def _do_approve(self) -> None:
        from github import GithubException

        from prism.services.github import submit_review

        try:
            submit_review(self._repo_slug, self._pr_number, event="APPROVE")
            self._pr = self._pr.model_copy(update={"review_state": "APPROVED"})
            self.app.call_from_thread(self._update_header)
            self.app.call_from_thread(self.notify, "PR approved", severity="information")
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(self.notify, f"Approve failed: {msg}", severity="error")
        except RuntimeError as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Approve failed: {e}", severity="error")

    def action_request_changes(self) -> None:
        self.app.push_screen(
            RequestChangesModal(),
            callback=self._on_request_changes_submitted,
        )

    def _on_request_changes_submitted(self, body: str | None) -> None:
        if body is None:
            return
        self._do_request_changes(body)

    @work(thread=True)
    def _do_request_changes(self, body: str) -> None:
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
            self.app.call_from_thread(self.notify, "Changes requested", severity="warning")
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(
                self.notify, f"Request changes failed: {msg}", severity="error"
            )
        except RuntimeError as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Request changes failed: {e}", severity="error")

    def _update_header(self) -> None:
        self.query_one(HeaderBar).update_review_state(self._pr.review_state)

    # ── Reply ───────────────────────────────────────────────────────────────

    def on_comment_list_reply_requested(self, event: CommentList.ReplyRequested) -> None:
        self.app.push_screen(
            ReplyComposer(event.comment),
            callback=self._on_reply_submitted,
        )

    def _on_reply_submitted(self, body: str | None) -> None:
        if not body:
            return
        diff = self.query_one(DiffViewer)
        comment_list = diff.query_one(CommentList)
        from textual.widgets import ListView

        lv = comment_list.query_one(ListView)
        index = lv.index
        if index is None:
            return
        if index < len(comment_list._comments):
            comment = comment_list._comments[index]
            self._do_post_reply(comment, body)

    @work(thread=True)
    def _do_post_reply(self, parent_comment: PRComment, body: str) -> None:
        from github import GithubException

        from prism.services.github import post_reply

        try:
            reply = post_reply(
                repo_slug=self._repo_slug,
                pr_number=self._pr_number,
                comment_id=parent_comment.id,
                body=body,
            )
            self.app.call_from_thread(self.query_one(CommentsPanel).add_comment, reply)
            self.app.call_from_thread(self.notify, "Reply posted", severity="information")
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(self.notify, f"Reply failed: {msg}", severity="error")
        except RuntimeError as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Reply failed: {e}", severity="error")

    # ── Quit ────────────────────────────────────────────────────────────────

    def action_request_quit(self) -> None:
        """Pop back to the list screen if available, otherwise exit the app."""
        if len(self.app.screen_stack) > 1:
            # Launched on top of PRListScreen — go back without confirmation
            self.app.pop_screen()
        else:
            # Launched directly (no list underneath) — confirm before exiting
            self.app.push_screen(
                QuitConfirmModal(),
                callback=lambda confirmed: self.app.exit() if confirmed else None,
            )

    # ── Toggle panels ───────────────────────────────────────────────────────

    def action_toggle_comments_panel(self) -> None:
        panel = self.query_one(CommentsPanel)
        panel.display = not panel.display

    def action_toggle_ai_panel(self) -> None:
        panel = self.query_one(AIPanel)
        panel.display = not panel.display

    def action_reanalyze(self) -> None:
        """Force re-analyze the current file with AI, bypassing the cache."""
        self.query_one(AIPanel).trigger_reanalyze()

    def action_post_suggestion(self) -> None:
        """Post the AI-suggested comment to the PR as a PR-level comment."""
        suggestion = self.query_one(AIPanel).get_suggestion()
        if not suggestion:
            self.notify("No AI suggestion available.", severity="warning")
            return
        self._do_post_suggestion(suggestion)

    @work(thread=True)
    def _do_post_suggestion(self, body: str) -> None:
        from github import GithubException

        from prism.services.github import post_pr_comment

        try:
            post_pr_comment(self._repo_slug, self._pr_number, body)
            self.app.call_from_thread(
                self.notify,
                "AI suggestion posted as PR comment.",
                severity="information",
            )
        except GithubException as e:
            msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            self.app.call_from_thread(self.notify, f"GitHub error: {msg}", severity="error")
        except RuntimeError as e:
            self.app.call_from_thread(self.notify, str(e), severity="error")
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"Failed to post suggestion: {e}", severity="error"
            )

    # ── Browser / clipboard / editor ───────────────────────────────────────

    def action_open_in_browser(self) -> None:
        if self._pr.html_url:
            webbrowser.open(self._pr.html_url)
            self.notify(f"Opened PR #{self._pr.number} in browser")

    def action_copy_url(self) -> None:
        if self._pr.html_url:
            self.app.copy_to_clipboard(self._pr.html_url)
            self.notify("PR URL copied to clipboard")

    def action_jump_mode(self) -> None:
        """Activate jump mode: show letter hints for each panel."""
        from prism.components.modals.jump_overlay import JumpOverlay
        from prism.components.modals.jumper import Jumper

        targets = [
            ("file tree", self.query_one(FileTreePanel)),
            ("diff", self.query_one(DiffViewer)),
            ("comments", self.query_one(CommentsPanel)),
            ("AI", self.query_one(AIPanel)),
        ]
        jumper = Jumper(targets)
        self.app.push_screen(JumpOverlay(jumper), callback=self._on_jump)

    def _on_jump(self, widget: object) -> None:
        from textual.widget import Widget

        if isinstance(widget, Widget):
            widget.focus()

    def action_open_in_editor(self) -> None:
        """Open the currently selected file in $EDITOR."""
        diff = self.query_one(DiffViewer)
        if not diff.current_file:
            self.notify("No file selected.", severity="warning")
            return
        from prism.config import load_config

        editor = load_config().resolved_editor()
        if not editor:
            self.notify(
                "No editor configured. Set $EDITOR or add `editor` to config.",
                severity="warning",
            )
            return
        try:
            subprocess.Popen([editor, diff.current_file])
        except OSError as e:
            self.notify(f"Could not open editor: {e}", severity="error")
