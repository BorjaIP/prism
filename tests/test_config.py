from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from prism.config import PrismConfig


class TestPrismConfigDefaults:
    def test_default_theme(self) -> None:
        config = PrismConfig()
        assert config.theme == "prism-dark"

    def test_default_ai_backend(self) -> None:
        assert PrismConfig().ai_backend == "claude_code"

    def test_default_show_ai_panel(self) -> None:
        assert PrismConfig().show_ai_panel is True

    def test_default_refresh_interval(self) -> None:
        assert PrismConfig().refresh_interval_seconds == 0

    def test_default_keymap_is_empty(self) -> None:
        assert PrismConfig().keymap == {}

    def test_default_editor_is_empty(self) -> None:
        assert PrismConfig().editor == ""


class TestResolvedEditor:
    def test_returns_configured_editor_when_set(self) -> None:
        config = PrismConfig(editor="nvim")
        assert config.resolved_editor() == "nvim"

    def test_falls_back_to_editor_env_var(self) -> None:
        config = PrismConfig(editor="")
        with patch.dict(os.environ, {"EDITOR": "vim"}):
            assert config.resolved_editor() == "vim"

    def test_returns_empty_string_when_neither_set(self) -> None:
        config = PrismConfig(editor="")
        env = {k: v for k, v in os.environ.items() if k != "EDITOR"}
        with patch.dict(os.environ, env, clear=True):
            assert config.resolved_editor() == ""

    def test_configured_editor_takes_priority_over_env(self) -> None:
        config = PrismConfig(editor="emacs")
        with patch.dict(os.environ, {"EDITOR": "vim"}):
            assert config.resolved_editor() == "emacs"


class TestLoadConfig:
    def test_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        from prism import config as config_module

        with patch.object(config_module, "CONFIG_PATH", tmp_path / "config.toml"):
            from prism.config import load_config

            result = load_config()

        assert isinstance(result, PrismConfig)
        assert result.theme == "prism-dark"

    def test_loads_values_from_toml(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_file = tmp_path / "config.toml"
        config_file.write_text('theme = "nord"\nai_backend = "api"\n')

        with patch.object(config_module, "CONFIG_PATH", config_file):
            from prism.config import load_config

            result = load_config()

        assert result.theme == "nord"
        assert result.ai_backend == "api"

    def test_loads_boolean_field(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_file = tmp_path / "config.toml"
        config_file.write_text("show_ai_panel = false\n")

        with patch.object(config_module, "CONFIG_PATH", config_file):
            from prism.config import load_config

            result = load_config()

        assert result.show_ai_panel is False

    def test_loads_integer_field(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_file = tmp_path / "config.toml"
        config_file.write_text("refresh_interval_seconds = 30\n")

        with patch.object(config_module, "CONFIG_PATH", config_file):
            from prism.config import load_config

            result = load_config()

        assert result.refresh_interval_seconds == 30


class TestSaveConfig:
    def test_creates_file_with_string_fields(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_path = tmp_path / "prism" / "config.toml"

        with patch.object(config_module, "CONFIG_PATH", config_path):
            from prism.config import save_config

            save_config(PrismConfig(theme="dracula"))

        content = config_path.read_text()
        assert 'theme = "dracula"' in content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_path = tmp_path / "deep" / "nested" / "config.toml"

        with patch.object(config_module, "CONFIG_PATH", config_path):
            from prism.config import save_config

            save_config(PrismConfig())

        assert config_path.exists()

    def test_saves_boolean_as_lowercase(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_path = tmp_path / "config.toml"

        with patch.object(config_module, "CONFIG_PATH", config_path):
            from prism.config import save_config

            save_config(PrismConfig(show_ai_panel=False))

        content = config_path.read_text()
        assert "show_ai_panel = false" in content

    def test_saves_integer_without_quotes(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_path = tmp_path / "config.toml"

        with patch.object(config_module, "CONFIG_PATH", config_path):
            from prism.config import save_config

            save_config(PrismConfig(refresh_interval_seconds=60))

        content = config_path.read_text()
        assert "refresh_interval_seconds = 60" in content

    def test_saves_keymap_section(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_path = tmp_path / "config.toml"

        with patch.object(config_module, "CONFIG_PATH", config_path):
            from prism.config import save_config

            save_config(PrismConfig(keymap={"refresh": "ctrl+r"}))

        content = config_path.read_text()
        assert "[keymap]" in content
        assert 'refresh = "ctrl+r"' in content

    def test_roundtrip_load_after_save(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_path = tmp_path / "config.toml"
        original = PrismConfig(theme="gruvbox", refresh_interval_seconds=15)

        with patch.object(config_module, "CONFIG_PATH", config_path):
            from prism.config import load_config, save_config

            save_config(original)
            restored = load_config()

        assert restored.theme == "gruvbox"
        assert restored.refresh_interval_seconds == 15

    def test_escapes_special_chars_in_values(self, tmp_path: Path) -> None:
        from prism import config as config_module

        config_path = tmp_path / "config.toml"

        with patch.object(config_module, "CONFIG_PATH", config_path):
            from prism.config import save_config

            # backslash in path should be escaped
            save_config(PrismConfig(editor="C:\\Users\\bob\\nvim"))

        content = config_path.read_text()
        assert "\\\\" in content
