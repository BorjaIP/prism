"""Configuration loading for Prism."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel

CONFIG_PATH = Path.home() / ".config" / "prism" / "config.toml"


class PrismConfig(BaseModel):
    """Application configuration."""

    github_token: str = ""
    default_repo: str = ""
    show_ai_panel: bool = True
    theme: str = "dark"


def load_config() -> PrismConfig:
    """Load config from ~/.config/prism/config.toml if it exists."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
        return PrismConfig(**data)
    return PrismConfig()
