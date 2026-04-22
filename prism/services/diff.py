from __future__ import annotations

import shutil
import subprocess

from rich.text import Text

from prism.constants import DEFAULT_DIFF_WIDTH


def _delta_available() -> bool:
    return shutil.which("delta") is not None


def render_diff(patch: str, width: int = DEFAULT_DIFF_WIDTH) -> Text:
    """Render a unified diff patch as styled Rich Text.

    Tries to use `delta` for syntax-highlighted output.
    Falls back to basic +/- coloring if delta is not installed.
    """
    if not patch:
        return Text("(no diff available)", style="dim")

    if _delta_available():
        return _render_with_delta(patch, width)
    return _render_plain(patch)


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
    return _render_plain(patch)


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
