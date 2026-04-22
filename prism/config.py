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
    # AI backend: "claude_code" uses the `claude` CLI (reuses Claude Code auth);
    # "api" uses the Anthropic SDK directly (requires ANTHROPIC_API_KEY).
    ai_backend: str = "claude_code"
    # Claude model used for AI analysis. Any model available to your account works.
    ai_model: str = "claude-haiku-4-5-20251001"

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


def save_config(config: PrismConfig) -> None:
    """Persist config to ~/.config/prism/config.toml."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for field, value in config.model_dump().items():
        if isinstance(value, dict):
            continue  # handled below
        if isinstance(value, bool):
            lines.append(f"{field} = {str(value).lower()}")
        elif isinstance(value, int):
            lines.append(f"{field} = {value}")
        else:
            escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{field} = "{escaped}"')
    if config.keymap:
        lines.append("\n[keymap]")
        for k, v in config.keymap.items():
            escaped_v = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k} = "{escaped_v}"')
    CONFIG_PATH.write_text("\n".join(lines) + "\n")
