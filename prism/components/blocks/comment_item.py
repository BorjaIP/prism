from __future__ import annotations

from prism.models import PRComment


def comment_label(comment: PRComment) -> str:
    """Format a single inline review comment for display in a list."""
    indent = "  ↳ " if comment.in_reply_to_id is not None else ""
    line_info = f" (line {comment.line})" if comment.line else ""
    preview = comment.body[:80].replace("\n", " ")
    if len(comment.body) > 80:
        preview += "…"
    return f"{indent}@{comment.author}{line_info}: {preview}"
