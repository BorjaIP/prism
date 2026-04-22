"""Command palette providers for Prism."""

from __future__ import annotations

from functools import partial

from textual.command import Hit, Hits, Provider

_COMMANDS: list[tuple[str, str, str]] = [
    ("approve", "Approve PR", "Submit an APPROVE review"),
    ("request_changes", "Request Changes", "Submit a REQUEST_CHANGES review"),
    ("compose_comment", "Comment on file", "Write an inline comment on the selected line"),
    ("toggle_comments_panel", "Toggle comments panel", "Show or hide the comments panel"),
    ("refresh", "Refresh PR data", "Re-fetch PR data from GitHub"),
    ("open_in_browser", "Open in browser", "Open the PR in your default browser"),
    ("copy_url", "Copy PR URL", "Copy the PR URL to the clipboard"),
    ("open_in_editor", "Open file in editor", "Open the selected file in $EDITOR"),
    ("cycle_expand", "Expand panel", "Cycle through expanded panel modes"),
    ("toggle_ai_panel", "Toggle AI panel", "Show or hide the AI analysis panel"),
]


class PrismProvider(Provider):
    """Provides PR review actions to the Textual command palette."""

    async def discover(self) -> Hits:
        for action, name, help_text in _COMMANDS:
            yield Hit(
                score=1.0,
                match_display=name,
                command=self._make_command(action, name, help_text),
                text=name,
                help=help_text,
            )

    async def search(self, query: str) -> Hits:
        query_lower = query.lower()
        for action, name, help_text in _COMMANDS:
            if query_lower in name.lower() or query_lower in help_text.lower():
                score = 1.0 if query_lower in name.lower() else 0.5
                yield Hit(
                    score=score,
                    match_display=name,
                    command=self._make_command(action, name, help_text),
                    text=name,
                    help=help_text,
                )

    def _make_command(self, action: str, name: str, help_text: str):
        async def run() -> None:
            screen = self.screen
            handler = getattr(screen, f"action_{action}", None)
            if handler is not None:
                await screen.run_action(action)

        return run


class ThemeProvider(Provider):
    """Lists all registered Prism themes in the command palette."""

    async def discover(self) -> Hits:
        for name in sorted(self.app.available_themes):
            yield self._make_hit(name)

    async def search(self, query: str) -> Hits:
        query_lower = query.lower()
        for name in sorted(self.app.available_themes):
            if query_lower in name.lower():
                yield self._make_hit(name)

    def _make_hit(self, theme_name: str) -> Hit:
        active = self.app.theme == theme_name
        display = f"Theme: {theme_name}" + (" ✓" if active else "")

        async def apply(name: str = theme_name) -> None:
            self.app.theme = name

        return Hit(
            score=0.9,
            match_display=display,
            command=apply,
            text=f"Theme: {theme_name}",
            help=f"Switch to the {theme_name} theme",
        )
