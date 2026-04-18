"""PRism — main Textual application."""

from __future__ import annotations

from pathlib import Path

from textual.app import App

from prism.models import PRMetadata
from prism.screens.review import ReviewScreen

CSS_PATH = Path(__file__).parent / "prism.tcss"


class PRismApp(App):
    """Terminal UI for reviewing GitHub pull requests."""

    TITLE = "PRism"
    CSS_PATH = CSS_PATH

    def __init__(self, pr: PRMetadata, repo_slug: str, pr_number: int) -> None:
        super().__init__()
        self._pr = pr
        self._repo_slug = repo_slug
        self._pr_number = pr_number

    def on_mount(self) -> None:
        self.push_screen(ReviewScreen(self._pr, self._repo_slug, self._pr_number))
