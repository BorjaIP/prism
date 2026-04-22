from __future__ import annotations

# ── Risk level ────────────────────────────────────────────────────────────────

# Full label form (used in AI panel)
RISK_BADGE_STYLES: dict[str, tuple[str, str]] = {
    "low": (" LOW RISK ", "bold white on dark_green"),
    "medium": (" MEDIUM RISK ", "bold black on yellow"),
    "high": (" HIGH RISK ", "bold white on dark_red"),
}

# Compact single-character form (used in file tree)
RISK_CHARS: dict[str, tuple[str, str]] = {
    "low": ("L", "green"),
    "medium": ("M", "yellow"),
    "high": ("H", "red"),
}

# ── PR state ──────────────────────────────────────────────────────────────────

# Badge form for header bar
STATE_STYLES: dict[str, tuple[str, str]] = {
    "open": ("OPEN", "bold white on dark_green"),
    "closed": ("CLOSED", "bold white on dark_red"),
    "merged": ("MERGED", "bold white on dark_violet"),
}

# Label + style form for PR preview panel
STATE_LABEL_STYLES: dict[str, tuple[str, str]] = {
    "open": ("open", "bold green"),
    "merged": ("merged", "bold magenta"),
    "closed": ("closed", "bold red"),
}

# Color only (for PR list table cell)
STATE_COLORS: dict[str, str] = {
    "open": "green",
    "merged": "magenta",
    "closed": "red",
}

# ── Review state ──────────────────────────────────────────────────────────────

# Full badge form for header bar
REVIEW_STATE_STYLES: dict[str, tuple[str, str]] = {
    "APPROVED": (" ✓ APPROVED ", "bold white on dark_green"),
    "CHANGES_REQUESTED": (" ✗ CHANGES REQUESTED ", "bold white on dark_red"),
}

# Compact icon form for PR list table
REVIEW_ICONS: dict[str, tuple[str, str]] = {
    "APPROVED": ("✓", "green"),
    "CHANGES_REQUESTED": ("!", "red"),
}

# Verbose label form for PR preview panel
REVIEW_LABELS: dict[str, tuple[str, str]] = {
    "APPROVED": ("✓ approved", "green"),
    "CHANGES_REQUESTED": ("! changes requested", "red"),
}

# ── CI / checks status ────────────────────────────────────────────────────────

# Full badge form for header bar
CHECKS_STATUS_STYLES: dict[str, tuple[str, str]] = {
    "success": (" ✓ CI ", "bold white on dark_green"),
    "failure": (" ✗ CI ", "bold white on dark_red"),
    "error": (" ✗ CI ", "bold white on dark_red"),
    "pending": (" ◷ CI ", "bold black on yellow"),
}

# Compact icon form for PR list table
CI_ICONS: dict[str, tuple[str, str]] = {
    "success": ("✓", "green"),
    "failure": ("✗", "red"),
    "error": ("✗", "red"),
    "pending": ("…", "yellow"),
}

# Verbose label form for PR preview panel
CI_LABELS: dict[str, tuple[str, str]] = {
    "success": ("✓ passing", "green"),
    "failure": ("✗ failing", "red"),
    "error": ("✗ error", "red"),
    "pending": ("… pending", "yellow"),
}
