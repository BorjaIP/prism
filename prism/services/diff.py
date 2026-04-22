from __future__ import annotations

import shutil
import subprocess

from rich.text import Text

from prism.constants import DEFAULT_DIFF_WIDTH


class DiffService:
    """Diff rendering: syntax-highlighted via delta, or plain +/- fallback."""

    @staticmethod
    def _delta_available() -> bool:
        return shutil.which("delta") is not None

    @staticmethod
    def _render_plain(patch: str) -> Text:
        text = Text()
        for line in patch.splitlines(keepends=True):
            if line.startswith("+++") or line.startswith("---"):
                text.append(line, style="bold")
            elif line.startswith("@@"):
                text.append(line, style="cyan")
            elif line.startswith("+"):
                text.append(line, style="green")
            elif line.startswith("-"):
                text.append(line, style="red")
            else:
                text.append(line)
        return text

    @staticmethod
    def _render_with_delta(patch: str, width: int) -> Text:
        result = subprocess.run(
            [
                "delta",
                "--paging=never",
                "--no-gitconfig",
                f"--width={width}",
            ],
            input=patch.encode(),
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout:
            return Text.from_ansi(result.stdout.decode())
        return DiffService._render_plain(patch)

    @staticmethod
    def render(patch: str, width: int = DEFAULT_DIFF_WIDTH) -> Text:
        """Render a unified diff patch as styled Rich Text.

        Tries to use `delta` for syntax-highlighted output.
        Falls back to basic +/- coloring if delta is not installed.
        """
        if not patch:
            return Text("(no diff available)", style="dim")

        if DiffService._delta_available():
            return DiffService._render_with_delta(patch, width)
        return DiffService._render_plain(patch)
