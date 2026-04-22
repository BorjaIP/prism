from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from prism.themes import (
    _BUILTIN,
    PrismTheme,
    _parse_base16_script,
    _theme_from_base16_colors,
    load_theme,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

_MINIMAL_BASE16_SCRIPT = """\
color00="1d/1f/21"
color01="cc/66/66"
color02="b5/bd/68"
color03="f0/c6/74"
color04="81/a2/be"
color05="b2/94/bb"
color06="8a/be/b7"
color07="c5/c8/c6"
color16="de/93/5f"
color18="28/2a/2e"
color19="37/3b/41"
"""


class TestParseBase16Script:
    def test_extracts_hex_colors(self, tmp_path: Path) -> None:
        script = tmp_path / "base16-test.sh"
        script.write_text(_MINIMAL_BASE16_SCRIPT)
        colors = _parse_base16_script(script)
        assert colors["color00"] == "#1d1f21"
        assert colors["color01"] == "#cc6666"

    def test_strips_slashes(self, tmp_path: Path) -> None:
        script = tmp_path / "base16-test.sh"
        script.write_text('color07="c5/c8/c6"\n')
        colors = _parse_base16_script(script)
        assert colors["color07"] == "#c5c8c6"

    def test_ignores_non_matching_lines(self, tmp_path: Path) -> None:
        script = tmp_path / "base16-test.sh"
        script.write_text('export VARIABLE="something"\ncolor00="1d/1f/21"\n')
        colors = _parse_base16_script(script)
        assert "VARIABLE" not in colors
        assert "color00" in colors

    def test_returns_empty_dict_for_empty_script(self, tmp_path: Path) -> None:
        script = tmp_path / "base16-empty.sh"
        script.write_text("")
        assert _parse_base16_script(script) == {}

    def test_parses_all_colors_from_minimal_script(self, tmp_path: Path) -> None:
        script = tmp_path / "base16-test.sh"
        script.write_text(_MINIMAL_BASE16_SCRIPT)
        colors = _parse_base16_script(script)
        expected_keys = {
            "color00",
            "color01",
            "color02",
            "color03",
            "color04",
            "color05",
            "color06",
            "color07",
            "color16",
            "color18",
            "color19",
        }
        assert expected_keys.issubset(colors.keys())


class TestThemeFromBase16Colors:
    def _colors(self):
        return {
            "color00": "#1d1f21",
            "color01": "#cc6666",
            "color02": "#b5bd68",
            "color03": "#f0c674",
            "color04": "#81a2be",
            "color05": "#b294bb",
            "color06": "#8abeb7",
            "color07": "#c5c8c6",
            "color16": "#de935f",
            "color18": "#282a2e",
            "color19": "#373b41",
        }

    def test_sets_name(self) -> None:
        theme = _theme_from_base16_colors("my-theme", self._colors())
        assert theme.name == "my-theme"

    def test_maps_diff_add_to_green(self) -> None:
        theme = _theme_from_base16_colors("t", self._colors())
        assert theme.diff_add == "#b5bd68"

    def test_maps_diff_remove_to_red(self) -> None:
        theme = _theme_from_base16_colors("t", self._colors())
        assert theme.diff_remove == "#cc6666"

    def test_maps_background(self) -> None:
        theme = _theme_from_base16_colors("t", self._colors())
        assert theme.background == "#1d1f21"

    def test_maps_foreground(self) -> None:
        theme = _theme_from_base16_colors("t", self._colors())
        assert theme.foreground == "#c5c8c6"

    def test_uses_defaults_for_missing_colors(self) -> None:
        # No colors at all — should use hard-coded defaults from function
        theme = _theme_from_base16_colors("empty", {})
        assert theme.diff_add is not None
        assert theme.background is not None

    def test_returns_prism_theme_instance(self) -> None:
        theme = _theme_from_base16_colors("t", self._colors())
        assert isinstance(theme, PrismTheme)


class TestPrismThemeToTextualTheme:
    def test_dark_theme_by_default(self) -> None:
        theme = PrismTheme(name="my-dark").to_textual_theme()
        assert theme.dark is True

    def test_light_theme_when_name_ends_with_light(self) -> None:
        theme = PrismTheme(name="my-light").to_textual_theme()
        assert theme.dark is False

    def test_name_preserved(self) -> None:
        theme = PrismTheme(name="nord").to_textual_theme()
        assert theme.name == "nord"

    def test_primary_uses_diff_add_when_not_set(self) -> None:
        t = PrismTheme(name="t", diff_add="#aabbcc", primary=None)
        textual = t.to_textual_theme()
        assert textual.primary == "#aabbcc"

    def test_explicit_primary_overrides_diff_add(self) -> None:
        t = PrismTheme(name="t", diff_add="#aabbcc", primary="#112233")
        textual = t.to_textual_theme()
        assert textual.primary == "#112233"

    def test_diff_variables_in_theme(self) -> None:
        t = PrismTheme(name="t", diff_add="#00ff00", diff_remove="#ff0000")
        textual = t.to_textual_theme()
        assert textual.variables["diff-add"] == "#00ff00"
        assert textual.variables["diff-remove"] == "#ff0000"

    def test_optional_fields_included_when_set(self) -> None:
        from textual.theme import Theme

        t = PrismTheme(name="t", background="#111111", surface="#222222")
        textual = t.to_textual_theme()
        assert isinstance(textual, Theme)


class TestLoadBase16:
    def test_returns_none_when_scripts_dir_missing(self) -> None:
        from prism import themes as themes_module
        from prism.themes import load_base16

        nonexistent = Path("/nonexistent/path/to/base16")
        with patch.object(themes_module, "BASE16_SCRIPTS_DIR", nonexistent):
            assert load_base16("test") is None

    def test_returns_none_when_script_file_missing(self, tmp_path: Path) -> None:
        from prism import themes as themes_module
        from prism.themes import load_base16

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        with patch.object(themes_module, "BASE16_SCRIPTS_DIR", scripts_dir):
            assert load_base16("nonexistent-theme") is None

    def test_loads_theme_from_script(self, tmp_path: Path) -> None:
        from prism import themes as themes_module
        from prism.themes import load_base16

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "base16-tomorrow.sh"
        script.write_text(_MINIMAL_BASE16_SCRIPT)

        with patch.object(themes_module, "BASE16_SCRIPTS_DIR", scripts_dir):
            theme = load_base16("tomorrow")

        assert theme is not None
        assert theme.name == "base16-tomorrow"


class TestDetectActiveBase16:
    def test_uses_base16_theme_env_var(self, tmp_path: Path) -> None:
        from prism import themes as themes_module
        from prism.themes import detect_active_base16

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "base16-ocean.sh").write_text(_MINIMAL_BASE16_SCRIPT)

        with (
            patch.object(themes_module, "BASE16_SCRIPTS_DIR", scripts_dir),
            patch.dict(os.environ, {"BASE16_THEME": "ocean"}),
        ):
            theme = detect_active_base16()

        assert theme is not None
        assert "ocean" in theme.name

    def test_returns_none_when_no_env_and_no_file(self, tmp_path: Path) -> None:
        from prism.themes import detect_active_base16

        env = {k: v for k, v in os.environ.items() if k != "BASE16_THEME"}

        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            theme = detect_active_base16()

        assert theme is None


class TestListBase16Themes:
    def test_returns_empty_when_dir_missing(self) -> None:
        from prism import themes as themes_module
        from prism.themes import list_base16_themes

        with patch.object(themes_module, "BASE16_SCRIPTS_DIR", Path("/nonexistent")):
            assert list_base16_themes() == []

    def test_returns_sorted_short_names(self, tmp_path: Path) -> None:
        from prism import themes as themes_module
        from prism.themes import list_base16_themes

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        for name in ("base16-zenburn.sh", "base16-nord.sh", "base16-gruvbox.sh"):
            (scripts_dir / name).touch()

        with patch.object(themes_module, "BASE16_SCRIPTS_DIR", scripts_dir):
            result = list_base16_themes()

        assert result == ["gruvbox", "nord", "zenburn"]

    def test_strips_base16_prefix(self, tmp_path: Path) -> None:
        from prism import themes as themes_module
        from prism.themes import list_base16_themes

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "base16-ocean.sh").touch()

        with patch.object(themes_module, "BASE16_SCRIPTS_DIR", scripts_dir):
            result = list_base16_themes()

        assert result == ["ocean"]


class TestLoadTheme:
    def test_returns_builtin_by_name(self) -> None:
        for name in _BUILTIN:
            theme = load_theme(name)
            assert theme.name == name

    def test_falls_back_to_default_dark_for_unknown(self) -> None:
        theme = load_theme("totally-unknown-theme-xyz")
        assert theme.name == "prism-dark"

    def test_base16_prefix_triggers_load_base16(self) -> None:
        from prism import themes as themes_module

        with patch.object(themes_module, "BASE16_SCRIPTS_DIR", Path("/nonexistent")):
            # load_base16 returns None → fallback to DEFAULT_DARK
            theme = load_theme("base16-some-theme")

        assert theme.name == "prism-dark"

    def test_loads_custom_toml_from_themes_dir(self, tmp_path: Path) -> None:
        from prism import themes as themes_module

        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()
        toml_file = themes_dir / "my-custom.toml"
        toml_file.write_text('diff_add = "#aabbcc"\n')

        with patch.object(themes_module, "THEMES_DIR", themes_dir):
            theme = load_theme("my-custom")

        assert theme.name == "my-custom"
        assert theme.diff_add == "#aabbcc"
