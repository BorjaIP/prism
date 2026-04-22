from __future__ import annotations

from pathlib import Path

from textual.app import App

from prism.commands import PrismProvider, ThemeProvider
from prism.config import load_config
from prism.themes import load_theme

CSS_PATH = Path(__file__).parent / "prism.tcss"


class PRismApp(App):
    """Terminal UI for reviewing GitHub pull requests."""

    TITLE = "PRism"
    CSS_PATH = CSS_PATH
    COMMANDS = {PrismProvider, ThemeProvider}

    def __init__(
        self,
        initial_repo: str | None = None,
        initial_pr_number: int | None = None,
    ) -> None:
        super().__init__()
        self._initial_repo = initial_repo
        self._initial_pr_number = initial_pr_number

    def on_mount(self) -> None:
        config = load_config()
        if config.keymap:
            self.set_keymap(config.keymap)
        from prism.themes import _BUILTIN

        for t in _BUILTIN.values():
            self.register_theme(t.to_textual_theme())

        theme = load_theme(config.theme)
        textual_theme = theme.to_textual_theme()
        if textual_theme.name not in _BUILTIN:
            self.register_theme(textual_theme)
        self.theme = textual_theme.name

        from prism.screens.pr_list import PRListScreen

        self.push_screen(
            PRListScreen(
                initial_repo=self._initial_repo,
                initial_pr_number=self._initial_pr_number,
            )
        )
