from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel
from textual.theme import Theme

from prism.constants import THEMES_DIR

BASE16_SCRIPTS_DIR = Path.home() / ".config" / "base16-shell" / "scripts"


# ── Model ─────────────────────────────────────────────────────────────────────


class PrismTheme(BaseModel):
    """Full theme definition: Prism-specific diff/badge colors + Textual palette."""

    name: str = "prism-dark"

    # Diff viewer colors
    diff_add: str = "#22863a"
    diff_remove: str = "#b31d28"
    diff_hunk: str = "#0366d6"
    diff_add_bg: str = "#0d1117"
    diff_remove_bg: str = "#0d1117"

    # PR badge colors
    badge_open: str = "#22863a"
    badge_merged: str = "#6f42c1"
    badge_approved: str = "#22863a"
    badge_changes_requested: str = "#b31d28"
    badge_pending: str = "#b08800"

    # Full Textual palette (optional — used when loaded from base16 or custom TOML)
    background: str | None = None
    surface: str | None = None
    panel: str | None = None
    primary: str | None = None
    secondary: str | None = None
    accent: str | None = None
    foreground: str | None = None
    error: str | None = None
    warning: str | None = None
    success: str | None = None

    def to_textual_theme(self) -> Theme:
        """Convert to a Textual Theme object with all available CSS variables."""
        dark = not self.name.endswith("-light")
        kwargs: dict = {
            "name": self.name,
            "dark": dark,
            "primary": self.primary or self.diff_add,
            "variables": {
                "diff-add": self.diff_add,
                "diff-remove": self.diff_remove,
                "diff-hunk": self.diff_hunk,
                "diff-add-bg": self.diff_add_bg,
                "diff-remove-bg": self.diff_remove_bg,
                "badge-open": self.badge_open,
                "badge-merged": self.badge_merged,
                "badge-approved": self.badge_approved,
                "badge-changes-requested": self.badge_changes_requested,
                "badge-pending": self.badge_pending,
            },
        }
        for field in (
            "secondary",
            "background",
            "surface",
            "panel",
            "accent",
            "foreground",
            "error",
            "warning",
            "success",
        ):
            val = getattr(self, field)
            if val:
                kwargs[field] = val
        return Theme(**kwargs)


# ── Built-in themes ───────────────────────────────────────────────────────────

DEFAULT_DARK = PrismTheme(name="prism-dark")

DEFAULT_LIGHT = PrismTheme(
    name="prism-light",
    diff_add="#1a7f37",
    diff_remove="#cf222e",
    diff_hunk="#0550ae",
    diff_add_bg="#f6fef9",
    diff_remove_bg="#fff8f8",
    badge_open="#1a7f37",
    badge_merged="#8250df",
    badge_approved="#1a7f37",
    badge_changes_requested="#cf222e",
    badge_pending="#9a6700",
)

NORD = PrismTheme(
    name="nord",
    diff_add="#A3BE8C",
    diff_remove="#BF616A",
    diff_hunk="#5E81AC",
    diff_add_bg="#3B4252",
    diff_remove_bg="#3B4252",
    badge_open="#A3BE8C",
    badge_merged="#B48EAD",
    badge_approved="#A3BE8C",
    badge_changes_requested="#BF616A",
    badge_pending="#EBCB8B",
    background="#2E3440",
    surface="#3B4252",
    panel="#434C5E",
    primary="#88C0D0",
    secondary="#B48EAD",
    accent="#81A1C1",
    foreground="#ECEFF4",
    error="#BF616A",
    warning="#EBCB8B",
    success="#A3BE8C",
)

GRUVBOX = PrismTheme(
    name="gruvbox",
    diff_add="#B8BB26",
    diff_remove="#FB4934",
    diff_hunk="#83A598",
    diff_add_bg="#3C3836",
    diff_remove_bg="#3C3836",
    badge_open="#B8BB26",
    badge_merged="#D3869B",
    badge_approved="#B8BB26",
    badge_changes_requested="#FB4934",
    badge_pending="#FABD2F",
    background="#282828",
    surface="#3C3836",
    panel="#504945",
    primary="#83A598",
    secondary="#D3869B",
    accent="#8EC07C",
    foreground="#EBDBB2",
    error="#FB4934",
    warning="#FABD2F",
    success="#B8BB26",
)

CATPPUCCIN_MOCHA = PrismTheme(
    name="catppuccin-mocha",
    diff_add="#A6E3A1",
    diff_remove="#F38BA8",
    diff_hunk="#89B4FA",
    diff_add_bg="#313244",
    diff_remove_bg="#313244",
    badge_open="#A6E3A1",
    badge_merged="#CBA6F7",
    badge_approved="#A6E3A1",
    badge_changes_requested="#F38BA8",
    badge_pending="#F9E2AF",
    background="#1E1E2E",
    surface="#181825",
    panel="#313244",
    primary="#CBA6F7",
    secondary="#F5C2E7",
    accent="#89DCEB",
    foreground="#CDD6F4",
    error="#F38BA8",
    warning="#F9E2AF",
    success="#A6E3A1",
)

DRACULA = PrismTheme(
    name="dracula",
    diff_add="#50FA7B",
    diff_remove="#FF5555",
    diff_hunk="#6272A4",
    diff_add_bg="#21222C",
    diff_remove_bg="#21222C",
    badge_open="#50FA7B",
    badge_merged="#BD93F9",
    badge_approved="#50FA7B",
    badge_changes_requested="#FF5555",
    badge_pending="#F1FA8C",
    background="#282A36",
    surface="#21222C",
    panel="#44475A",
    primary="#BD93F9",
    secondary="#FF79C6",
    accent="#8BE9FD",
    foreground="#F8F8F2",
    error="#FF5555",
    warning="#F1FA8C",
    success="#50FA7B",
)

TOKYO_NIGHT = PrismTheme(
    name="tokyo-night",
    diff_add="#9ECE6A",
    diff_remove="#F7768E",
    diff_hunk="#7AA2F7",
    diff_add_bg="#2F3549",
    diff_remove_bg="#2F3549",
    badge_open="#9ECE6A",
    badge_merged="#BB9AF7",
    badge_approved="#9ECE6A",
    badge_changes_requested="#F7768E",
    badge_pending="#E0AF68",
    background="#1A1B26",
    surface="#16161E",
    panel="#2F3549",
    primary="#BB9AF7",
    secondary="#7DCFFF",
    accent="#7AA2F7",
    foreground="#C0CAF5",
    error="#F7768E",
    warning="#E0AF68",
    success="#9ECE6A",
)

_BUILTIN: dict[str, PrismTheme] = {
    "prism-dark": DEFAULT_DARK,
    "prism-light": DEFAULT_LIGHT,
    "nord": NORD,
    "gruvbox": GRUVBOX,
    "catppuccin-mocha": CATPPUCCIN_MOCHA,
    "dracula": DRACULA,
    "tokyo-night": TOKYO_NIGHT,
}


# ── base16 integration ────────────────────────────────────────────────────────


def _parse_base16_script(path: Path) -> dict[str, str]:
    """Return {colorXX: '#rrggbb', ...} from a base16 shell script."""
    colors: dict[str, str] = {}
    pattern = re.compile(
        r'^(color(?:\d{2}|_foreground|_background))="([0-9a-fA-F]{2}/[0-9a-fA-F]{2}/[0-9a-fA-F]{2})"'
    )
    for line in path.read_text(errors="ignore").splitlines():
        m = pattern.match(line.strip())
        if m:
            colors[m.group(1)] = "#" + m.group(2).replace("/", "")
    return colors


def _theme_from_base16_colors(name: str, c: dict[str, str]) -> PrismTheme:
    """Build a PrismTheme from a parsed base16 color dict."""
    bg = c.get("color00", "#1d1f21")  # base00 — darkest bg
    surface = c.get("color18", "#282a2e")  # base01
    panel = c.get("color19", "#373b41")  # base02
    red = c.get("color01", "#cc6666")  # base08
    green = c.get("color02", "#b5bd68")  # base0B
    yellow = c.get("color03", "#f0c674")  # base0A
    blue = c.get("color04", "#81a2be")  # base0D
    magenta = c.get("color05", "#b294bb")  # base0E
    cyan = c.get("color06", "#8abeb7")  # base0C
    fg = c.get("color07", "#c5c8c6")  # base05 — default fg

    return PrismTheme(
        name=name,
        # Diff
        diff_add=green,
        diff_remove=red,
        diff_hunk=blue,
        diff_add_bg=surface,
        diff_remove_bg=surface,
        # Badges
        badge_open=green,
        badge_merged=magenta,
        badge_approved=green,
        badge_changes_requested=red,
        badge_pending=yellow,
        # Full Textual palette
        background=bg,
        surface=surface,
        panel=panel,
        primary=blue,
        secondary=magenta,
        accent=cyan,
        foreground=fg,
        error=red,
        warning=yellow,
        success=green,
    )


def load_base16(theme_name: str) -> PrismTheme | None:
    """Load a base16 theme by short name (e.g. 'gruvbox-dark-hard').

    Returns None if the scripts directory or file is not found.
    """
    if not BASE16_SCRIPTS_DIR.exists():
        return None
    script = BASE16_SCRIPTS_DIR / f"base16-{theme_name}.sh"
    if not script.exists():
        return None
    colors = _parse_base16_script(script)
    return _theme_from_base16_colors(f"base16-{theme_name}", colors)


def detect_active_base16() -> PrismTheme | None:
    """Try to detect the currently active base16 theme and load it.

    Checks (in order):
      1. BASE16_THEME environment variable
      2. ~/.base16_theme symlink / file
    """
    import os

    name = os.environ.get("BASE16_THEME", "").strip()
    if not name:
        p = Path.home() / ".base16_theme"
        if p.exists():
            target = p.resolve() if p.is_symlink() else p
            name = target.stem.removeprefix("base16-")

    if name:
        return load_base16(name)
    return None


def list_base16_themes() -> list[str]:
    """Return sorted list of available base16 theme short names."""
    if not BASE16_SCRIPTS_DIR.exists():
        return []
    return sorted(p.stem.removeprefix("base16-") for p in BASE16_SCRIPTS_DIR.glob("base16-*.sh"))


# ── Public loader ─────────────────────────────────────────────────────────────


def load_theme(name: str) -> PrismTheme:
    """Load a theme by name.

    Resolution order:
      1. Built-in prism themes ("prism-dark", "prism-light")
      2. "base16" → auto-detect from active shell theme, else prism-dark
      3. "base16-<name>" → load that specific base16 theme
      4. ~/.config/prism/themes/<name>.toml — custom user TOML
      5. Fall back to prism-dark
    """
    if name in _BUILTIN:
        return _BUILTIN[name]

    if name == "base16":
        return detect_active_base16() or DEFAULT_DARK

    if name.startswith("base16-"):
        short = name.removeprefix("base16-")
        theme = load_base16(short)
        return theme if theme is not None else DEFAULT_DARK

    path = THEMES_DIR / f"{name}.toml"
    if path.exists():
        import tomllib

        with open(path, "rb") as f:
            data = tomllib.load(f)
        return PrismTheme(name=name, **data)

    return DEFAULT_DARK
