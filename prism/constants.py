from __future__ import annotations

import os
import re
from pathlib import Path

# ── XDG Base Directory paths ──────────────────────────────────────────────────
# https://specifications.freedesktop.org/basedir/latest/
# XDG_CONFIG_HOME defaults to ~/.config, XDG_CACHE_HOME defaults to ~/.cache.

_xdg_config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
_xdg_cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")

PRISM_CONFIG_DIR: Path = _xdg_config / "prism"
PRISM_CACHE_DIR: Path = _xdg_cache / "prism"

CONFIG_FILE: Path = PRISM_CONFIG_DIR / "config.toml"
HISTORY_FILE: Path = PRISM_CONFIG_DIR / "history.json"
THEMES_DIR: Path = PRISM_CONFIG_DIR / "themes"

# ── App ───────────────────────────────────────────────────────────────────────

APP_TITLE = "PRism"

# ── GitHub ────────────────────────────────────────────────────────────────────

GITHUB_PR_URL_RE = re.compile(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)")

# ── PR list screen tab IDs ────────────────────────────────────────────────────

TAB_RECENT = "tab-recent"
TAB_REVIEW = "tab-review"

# ── Review screen panel layout ────────────────────────────────────────────────

PANEL_CYCLE: list[str | None] = [None, "diff", "comments"]

DIFF_EXPANDED_WIDTH = "4fr"
DIFF_NORMAL_WIDTH = "1fr"
COMMENTS_EXPANDED_WIDTH = 32
COMMENTS_NORMAL_WIDTH = 42

# ── AI analysis ───────────────────────────────────────────────────────────────

AI_MAX_PATCH_CHARS = 8_000
AI_MAX_BODY_CHARS = 2_000
AI_MAX_TOKENS = 1_024
AI_CLI_TIMEOUT = 60  # seconds

# ── History ───────────────────────────────────────────────────────────────────

HISTORY_MAX_ENTRIES = 50
HISTORY_BODY_EXCERPT_LEN = 500

# ── Diff rendering ────────────────────────────────────────────────────────────

DEFAULT_DIFF_WIDTH = 120

# ── Comment display ───────────────────────────────────────────────────────────

COMMENT_PREVIEW_MAX_LEN = 80
