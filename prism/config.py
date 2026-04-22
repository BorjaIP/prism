"""Configuration loading for Prism."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import BaseModel

CONFIG_PATH = Path.home() / ".config" / "prism" / "config.toml"


class PrismConfig(BaseModel):
    """Application configuration."""

    github_token: str = ""
    default_repo: str = ""
    show_ai_panel: bool = True
    theme: str = "prism-dark"
    # Keybinding overrides: maps binding id → new key, e.g. {"refresh": "ctrl+f5"}
    keymap: dict[str, str] = {}
    # Auto-refresh interval in seconds; 0 means disabled
    refresh_interval_seconds: int = 0
    # Editor to open files in; defaults to $EDITOR env var
    editor: str = ""

    def resolved_editor(self) -> str:
        """Return the configured editor, falling back to $EDITOR."""
        return self.editor or os.environ.get("EDITOR", "")


def load_config() -> PrismConfig:
    """Load config from ~/.config/prism/config.toml if it exists."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
        return PrismConfig(**data)
    return PrismConfig()
