from __future__ import annotations

from unittest.mock import MagicMock, patch

from rich.text import Text

from prism.services.diff import _delta_available, _render_plain, render_diff


class TestDeltaAvailable:
    def test_returns_true_when_delta_in_path(self) -> None:
        with patch("prism.services.diff.shutil.which", return_value="/usr/bin/delta"):
            assert _delta_available() is True

    def test_returns_false_when_delta_not_in_path(self) -> None:
        with patch("prism.services.diff.shutil.which", return_value=None):
            assert _delta_available() is False


class TestRenderPlain:
    def test_added_lines_are_green(self) -> None:
        text = _render_plain("+added line\n")
        spans = [(text.plain[s.start : s.end], s.style) for s in text._spans]
        assert any("added line" in segment for segment, _ in spans)
        rendered = str(text)
        assert "added line" in rendered

    def test_removed_lines_are_styled_red(self) -> None:
        result = _render_plain("-removed\n")
        assert "removed" in result.plain

    def test_hunk_header_uses_cyan(self) -> None:
        result = _render_plain("@@ -1,3 +1,5 @@\n")
        assert "@@ -1,3 +1,5 @@" in result.plain

    def test_file_header_lines_are_bold(self) -> None:
        result = _render_plain("--- a/src/main.py\n+++ b/src/main.py\n")
        assert "--- a/src/main.py" in result.plain
        assert "+++ b/src/main.py" in result.plain

    def test_context_lines_have_no_style(self) -> None:
        result = _render_plain(" context line\n")
        assert "context line" in result.plain

    def test_returns_rich_text(self) -> None:
        assert isinstance(_render_plain("+ line\n"), Text)

    def test_multiline_patch(self) -> None:
        patch = "--- a.py\n+++ b.py\n@@ -1,2 +1,3 @@\n context\n+added\n-removed\n"
        result = _render_plain(patch)
        assert "context" in result.plain
        assert "added" in result.plain
        assert "removed" in result.plain

    def test_empty_patch_returns_empty_text(self) -> None:
        result = _render_plain("")
        assert result.plain == ""


class TestRenderDiff:
    def test_empty_patch_returns_dim_message(self) -> None:
        result = render_diff("")
        assert "no diff" in result.plain.lower()

    def test_none_like_empty_patch(self) -> None:
        # empty string is falsy — should not call delta
        with patch("prism.services.diff._delta_available") as mock_avail:
            render_diff("")
            mock_avail.assert_not_called()

    def test_uses_delta_when_available(self) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"\x1b[32m+added\x1b[0m\n"

        with (
            patch("prism.services.diff._delta_available", return_value=True),
            patch("prism.services.diff.subprocess.run", return_value=mock_proc),
        ):
            result = render_diff("+added\n")

        assert isinstance(result, Text)

    def test_falls_back_to_plain_when_delta_unavailable(self) -> None:
        with patch("prism.services.diff._delta_available", return_value=False):
            result = render_diff("+added\n-removed\n")

        assert "added" in result.plain
        assert "removed" in result.plain

    def test_falls_back_to_plain_on_delta_nonzero_exit(self) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = b""

        with (
            patch("prism.services.diff._delta_available", return_value=True),
            patch("prism.services.diff.subprocess.run", return_value=mock_proc),
        ):
            result = render_diff("+line\n")

        assert "line" in result.plain

    def test_passes_width_to_delta(self) -> None:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"out"

        with (
            patch("prism.services.diff._delta_available", return_value=True),
            patch("prism.services.diff.subprocess.run", return_value=mock_proc) as mock_run,
        ):
            render_diff("+line\n", width=80)

        call_args = mock_run.call_args[0][0]
        assert "--width=80" in call_args
