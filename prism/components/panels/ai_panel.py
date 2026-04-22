from __future__ import annotations

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Markdown, Static

from prism.components.blocks.badges import RISK_BADGE_STYLES
from prism.models import AIAnalysis, PRFile, PRMetadata


class AIPanel(Widget):
    """Streams per-file Claude analysis: summary, risk badge, concerns, suggested comment."""

    DEFAULT_CSS = """
    AIPanel {
        width: 32;
        min-width: 20;
        padding: 1 1;
    }
    """

    class AnalysisComplete(Message):
        """Posted when an analysis finishes so ReviewScreen can update risk badges."""

        def __init__(self, filename: str, analysis: AIAnalysis) -> None:
            super().__init__()
            self.filename = filename
            self.analysis = analysis

    def __init__(self, pr: PRMetadata, repo_slug: str, pr_number: int) -> None:
        super().__init__(id="ai-panel")
        self._pr = pr
        self._repo_slug = repo_slug
        self._pr_number = pr_number
        self._current_file: PRFile | None = None
        self._last_suggestion: str = ""

    def on_mount(self) -> None:
        self.border_title = "AI"
        self.query_one("#ai-loading").display = False
        self.query_one("#ai-scroll").display = False

    def compose(self) -> ComposeResult:
        yield Static("Select a file to analyze.", id="ai-empty")
        yield Static("Analyzing…", id="ai-loading")
        with VerticalScroll(id="ai-scroll"):
            yield Markdown("", id="ai-summary")
            yield Static("", id="ai-risk-badge")
            yield Markdown("", id="ai-concerns-and-suggestion")

    # ── Public API (called on main thread) ──────────────────────────────────

    def set_file(self, pr_file: PRFile) -> None:
        """Called when the user selects a file in the tree."""
        self._current_file = pr_file
        self._run_analysis(force_refresh=False)

    def trigger_reanalyze(self) -> None:
        """Force re-analysis of the current file, bypassing the cache."""
        if self._current_file is not None:
            self._run_analysis(force_refresh=True)

    def get_suggestion(self) -> str:
        """Return the last AI-suggested comment text, or empty string."""
        return self._last_suggestion

    # ── Background worker ───────────────────────────────────────────────────

    @work(thread=True, exclusive=True)
    def _run_analysis(self, force_refresh: bool = False) -> None:
        from prism.services.ai import analyze_file

        current = self._current_file
        if current is None:
            return
        self.app.call_from_thread(self._set_loading, True)
        try:
            result = analyze_file(
                self._pr,
                current,
                self._repo_slug,
                self._pr_number,
                force_refresh=force_refresh,
            )
            # Guard against stale results when the user switches files rapidly
            if self._current_file is current:
                self.app.call_from_thread(self._show_analysis, result, current.filename)
        except Exception as e:
            if self._current_file is current:
                self.app.call_from_thread(self._show_error, str(e))

    # ── Main-thread UI callbacks ────────────────────────────────────────────

    def _set_loading(self, loading: bool) -> None:
        self.query_one("#ai-empty").display = False
        self.query_one("#ai-loading").display = loading
        self.query_one("#ai-scroll").display = not loading

    def _show_analysis(self, analysis: AIAnalysis, filename: str) -> None:
        self._last_suggestion = analysis.suggested_comment

        self.query_one("#ai-loading").display = False
        self.query_one("#ai-empty").display = False
        self.query_one("#ai-scroll").display = True

        self.query_one("#ai-summary", Markdown).update(f"**Summary**\n\n{analysis.summary}")

        label, style = RISK_BADGE_STYLES.get(
            analysis.risk.lower(), (" UNKNOWN ", "bold white on grey50")
        )
        badge = Text()
        badge.append(label, style=style)
        self.query_one("#ai-risk-badge", Static).update(badge)

        parts: list[str] = []
        if analysis.concerns:
            parts.append("**Concerns**\n")
            for c in analysis.concerns:
                parts.append(f"**{c.title}**\n{c.description}\n")
        if analysis.suggested_comment:
            parts.append("**Suggested comment**\n")
            parts.append(f"> {analysis.suggested_comment}\n")
            parts.append("*Press `ctrl+s` to post.*")
        self.query_one("#ai-concerns-and-suggestion", Markdown).update("\n".join(parts))

        self.post_message(self.AnalysisComplete(filename, analysis))

    def _show_error(self, error: str) -> None:
        self.query_one("#ai-loading").display = False
        self.query_one("#ai-empty").display = False
        self.query_one("#ai-scroll").display = True
        self.query_one("#ai-summary", Markdown).update(f"**Error**\n\n{error}")
        self.query_one("#ai-risk-badge", Static).update("")
        self.query_one("#ai-concerns-and-suggestion", Markdown).update("")
