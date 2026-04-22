from __future__ import annotations

import re

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
