from __future__ import annotations

import webbrowser

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import (
    ContentSwitcher,
    Footer,
    LoadingIndicator,
    TabbedContent,
    TabPane,
)

from prism.components.modals.review_modals import QuitConfirmModal
from prism.components.sections.pr_list_widget import PRListWidget
from prism.components.sections.pr_preview_widget import PRPreviewWidget
from prism.models import PRSummary

_TAB_RECENT = "tab-recent"
_TAB_REVIEW = "tab-review"


class PRListScreen(Screen):
    """Tabbed screen: Recently Reviewed (local) | Review Requested (GitHub)."""

    TITLE = "PRism"

    BINDINGS = [
        Binding(
            "enter",
            "open_selected",
            "Open",
            id="open-selected",
            tooltip="Open selected PR for review",
        ),
        Binding("q", "request_quit", "Quit", id="quit", tooltip="Exit prism"),
        Binding(
            "n",
            "new_pr",
            "New PR",
            id="new-pr",
            tooltip="Open a PR by URL or repo+number",
        ),
        Binding(
            "d",
            "delete_pr",
            "Remove from list",
            id="delete-pr",
            tooltip="Remove from Prism's local history (does not affect GitHub)",
        ),
        Binding("r", "refresh", "Refresh", id="refresh", tooltip="Refresh current tab"),
        Binding(
            "o",
            "open_in_browser",
            "Open in browser",
            id="open-browser",
            tooltip="Open selected PR in browser",
        ),
    ]

    def __init__(
        self,
        initial_repo: str | None = None,
        initial_pr_number: int | None = None,
    ) -> None:
        super().__init__()
        self._initial_repo = initial_repo
        self._initial_pr_number = initial_pr_number
        self._selected_recent: PRSummary | None = None
        self._selected_review: PRSummary | None = None
        self._stopping = False
        self._review_loaded = False

    def compose(self) -> ComposeResult:
        with TabbedContent(id="pr-tabs"):
            with TabPane("Recently Reviewed", id=_TAB_RECENT):
                with Horizontal(id="recent-pane"):
                    yield PRListWidget(widget_id="recent-list")
                    yield PRPreviewWidget(widget_id="recent-preview")
            with TabPane("Review Requested", id=_TAB_REVIEW):
                with ContentSwitcher(id="review-switcher", initial="review-loading"):
                    yield LoadingIndicator(id="review-loading")
                    with Horizontal(id="review-pane"):
                        yield PRListWidget(widget_id="review-list")
                        yield PRPreviewWidget(widget_id="review-preview")
        yield Footer()

    def on_mount(self) -> None:
        self._load_history()
        if self._initial_repo and self._initial_pr_number:
            self._open_pr_by_coords(self._initial_repo, self._initial_pr_number)

    # ── Workers ───────────────────────────────────────────────────────────────

    @work(thread=True)
    def _load_history(self) -> None:
        """Load local Prism history — no network."""
        from prism.services.history import load_history

        try:
            summaries = load_history()
            self.app.call_from_thread(self._apply_history, summaries)
        except Exception as e:
            if not self._stopping:
                self.app.call_from_thread(
                    self.notify, f"Could not load history: {e}", severity="warning"
                )

    @work(thread=True, exclusive=True)
    def _fetch_review_requested(self) -> None:
        """Fetch PRs where the user is requested as reviewer from GitHub."""
        from prism.services.github import fetch_review_requested

        if self._stopping:
            return
        self.app.call_from_thread(self._set_review_title, "loading from GitHub…")
        try:
            summaries = fetch_review_requested()
            if not self._stopping:
                self.app.call_from_thread(self._apply_review_requested, summaries)
        except Exception as e:
            if not self._stopping:
                self.app.call_from_thread(
                    self.notify, f"Failed to load reviews: {e}", severity="warning"
                )
        finally:
            if not self._stopping:
                self.app.call_from_thread(self._set_review_title, "")

    @work(thread=True)
    def _open_pr_by_coords(self, repo_slug: str, pr_number: int) -> None:
        from prism.services.github import fetch_pr
        from prism.services.history import save_to_history

        if self._stopping:
            return
        self.app.call_from_thread(self.notify, f"Loading PR #{pr_number}…")
        try:
            pr = fetch_pr(repo_slug, pr_number)
            save_to_history(pr, repo_slug)
            if not self._stopping:

                def _push() -> None:
                    from prism.screens.review import ReviewScreen

                    self.app.push_screen(ReviewScreen(pr, repo_slug, pr_number))

                self.app.call_from_thread(_push)
        except Exception as e:
            if not self._stopping:
                self.app.call_from_thread(
                    self.notify,
                    f"Failed to load PR #{pr_number}: {e}",
                    severity="error",
                )

    # ── Apply data (main thread) ──────────────────────────────────────────────

    def _apply_history(self, summaries: list[PRSummary]) -> None:
        """Populate Recently Reviewed from local history only."""
        widget = self.query_one("#recent-list", PRListWidget)
        widget.load(summaries)
        widget.border_title = f"Recently Reviewed ({len(summaries)})"
        if summaries:
            # Set selected and preview directly — don't rely on message bubbling
            self._selected_recent = summaries[0]
            self.query_one("#recent-preview", PRPreviewWidget).update(summaries[0])
            widget.focus()

    def _apply_review_requested(self, summaries: list[PRSummary]) -> None:
        """Populate Review Requested from GitHub."""
        widget = self.query_one("#review-list", PRListWidget)
        widget.load(summaries)
        widget.border_title = f"Review Requested ({len(summaries)})"
        if summaries:
            self._selected_review = summaries[0]
            self.query_one("#review-preview", PRPreviewWidget).update(summaries[0])
            widget.focus()

    def _set_review_title(self, suffix: str) -> None:
        """Show/hide the loading indicator and update the border title."""
        if suffix:
            self.query_one("#review-switcher", ContentSwitcher).current = "review-loading"
        else:
            self.query_one("#review-switcher", ContentSwitcher).current = "review-pane"

    # ── Tab switching ─────────────────────────────────────────────────────────

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.tab.id == _TAB_REVIEW and not self._review_loaded:
            self._review_loaded = True
            self._fetch_review_requested()

    # ── Message handlers (cursor movement only) ───────────────────────────────

    def on_pr_list_widget_pr_highlighted(self, event: PRListWidget.PRHighlighted) -> None:
        if event.source_id == "recent-list":
            self._selected_recent = event.summary
            self.query_one("#recent-preview", PRPreviewWidget).update(event.summary)
        else:
            self._selected_review = event.summary
            self.query_one("#review-preview", PRPreviewWidget).update(event.summary)

    def on_pr_list_widget_pr_selected(self, event: PRListWidget.PRSelected) -> None:
        self._open_pr_by_coords(event.summary.repo_slug, event.summary.number)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_open_selected(self) -> None:
        selected = (
            self._selected_recent if self._active_tab() == _TAB_RECENT else self._selected_review
        )
        if selected is None:
            self.notify("No PR selected.", severity="warning")
            return
        self._open_pr_by_coords(selected.repo_slug, selected.number)

    def action_delete_pr(self) -> None:
        if self._active_tab() != _TAB_RECENT:
            self.notify("Remove is only available in Recently Reviewed.", severity="warning")
            return
        if self._selected_recent is None:
            self.notify("No PR selected.", severity="warning")
            return
        from prism.services.history import delete_from_history

        s = self._selected_recent
        delete_from_history(s.repo_slug, s.number)
        widget = self.query_one("#recent-list", PRListWidget)
        widget._summaries = [
            x
            for x in widget._summaries
            if not (x.repo_slug == s.repo_slug and x.number == s.number)
        ]
        widget.load(widget._summaries)
        widget.border_title = f"Recently Reviewed ({len(widget._summaries)})"
        self._selected_recent = widget._summaries[0] if widget._summaries else None
        if self._selected_recent:
            self.query_one("#recent-preview", PRPreviewWidget).update(self._selected_recent)
        else:
            self.query_one("#recent-preview", PRPreviewWidget).query_one(
                "#pr-preview-content"
            ).update(Text("Select a PR to preview", style="dim italic"))
        self.notify("Removed from Prism's local list (not deleted on GitHub).")

    def action_request_quit(self) -> None:
        self._stopping = True
        self.app.push_screen(
            QuitConfirmModal(),
            callback=lambda confirmed: self.app.exit() if confirmed else self._reset_stopping(),
        )

    def _reset_stopping(self) -> None:
        self._stopping = False

    def action_new_pr(self) -> None:
        from prism.components.modals.new_pr import NewPRScreen

        def _on_result(result: tuple[str, int] | None) -> None:
            if result is not None:
                self._open_pr_by_coords(result[0], result[1])

        self.app.push_screen(NewPRScreen(), callback=_on_result)

    def action_refresh(self) -> None:
        if self._active_tab() == _TAB_RECENT:
            self._load_history()
        else:
            self._review_loaded = False
            self._fetch_review_requested()
            self._review_loaded = True

    def action_open_in_browser(self) -> None:
        selected = (
            self._selected_recent if self._active_tab() == _TAB_RECENT else self._selected_review
        )
        if selected and selected.html_url:
            webbrowser.open(selected.html_url)

    def _active_tab(self) -> str:
        return self.query_one(TabbedContent).active or _TAB_RECENT
