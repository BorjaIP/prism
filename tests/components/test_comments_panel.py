from __future__ import annotations

from datetime import UTC, datetime

from prism.components.panels.comments_panel import _format_comment, _format_review
from prism.models import PRComment, PRReview


def _make_comment(**kwargs) -> PRComment:
    defaults = dict(
        id=1,
        body="Looks good to me.",
        author="reviewer",
        created_at=datetime(2024, 6, 15, 9, 30, tzinfo=UTC),
        path="src/main.py",
        line=42,
        diff_hunk="@@ -40,5 +40,7 @@\n context\n+new\n",
    )
    defaults.update(kwargs)
    return PRComment(**defaults)


def _make_review(**kwargs) -> PRReview:
    defaults = dict(
        id=10,
        body="",
        author="approver",
        state="APPROVED",
        submitted_at=datetime(2024, 6, 15, 10, 0, tzinfo=UTC),
        html_url="https://github.com/o/r/pull/1#review-10",
    )
    defaults.update(kwargs)
    return PRReview(**defaults)


class TestFormatComment:
    def test_includes_author(self) -> None:
        md = _format_comment(_make_comment(author="alice"))
        assert "@alice" in md

    def test_includes_timestamp(self) -> None:
        md = _format_comment(_make_comment())
        assert "2024-06-15" in md
        assert "09:30" in md

    def test_includes_file_path_and_line(self) -> None:
        md = _format_comment(_make_comment(path="core/utils.py", line=7))
        assert "core/utils.py:7" in md

    def test_includes_diff_hunk_for_root_comment(self) -> None:
        md = _format_comment(_make_comment(), indent=False)
        assert "```diff" in md
        assert "@@ -40,5 +40,7 @@" in md

    def test_no_diff_hunk_for_reply(self) -> None:
        md = _format_comment(_make_comment(), indent=True)
        assert "```diff" not in md

    def test_includes_comment_body(self) -> None:
        md = _format_comment(_make_comment(body="Please fix this."))
        assert "Please fix this." in md

    def test_indented_reply_has_prefix(self) -> None:
        md = _format_comment(_make_comment(), indent=True)
        assert md.startswith("  ")

    def test_root_comment_no_indent_prefix(self) -> None:
        md = _format_comment(_make_comment(), indent=False)
        assert not md.startswith("  ")

    def test_ends_with_separator(self) -> None:
        md = _format_comment(_make_comment())
        assert "---" in md

    def test_no_path_section_when_path_is_none(self) -> None:
        md = _format_comment(_make_comment(path=None, line=None))
        # The path block `> \`path:line\`` should not appear
        assert "None" not in md

    def test_no_hunk_when_diff_hunk_is_none(self) -> None:
        md = _format_comment(_make_comment(diff_hunk=None), indent=False)
        assert "```diff" not in md


class TestFormatReview:
    def test_includes_author(self) -> None:
        md = _format_review(_make_review(author="bob"))
        assert "@bob" in md

    def test_includes_timestamp(self) -> None:
        md = _format_review(_make_review())
        assert "2024-06-15" in md
        assert "10:00" in md

    def test_includes_state(self) -> None:
        md = _format_review(_make_review(state="APPROVED"))
        assert "APPROVED" in md

    def test_approved_uses_checkmark_icon(self) -> None:
        md = _format_review(_make_review(state="APPROVED"))
        assert "✅" in md

    def test_changes_requested_uses_red_icon(self) -> None:
        md = _format_review(_make_review(state="CHANGES_REQUESTED"))
        assert "🔴" in md

    def test_commented_uses_speech_bubble(self) -> None:
        md = _format_review(_make_review(state="COMMENTED"))
        assert "💬" in md

    def test_dismissed_uses_white_square(self) -> None:
        md = _format_review(_make_review(state="DISMISSED"))
        assert "⬜" in md

    def test_unknown_state_uses_question_mark(self) -> None:
        md = _format_review(_make_review(state="UNKNOWN_STATE"))
        assert "❓" in md

    def test_includes_body_when_present(self) -> None:
        md = _format_review(_make_review(body="Needs more tests."))
        assert "Needs more tests." in md

    def test_no_body_section_when_empty(self) -> None:
        md = _format_review(_make_review(body=""))
        # An empty body should not add an extra newline block with content
        assert "Needs" not in md

    def test_ends_with_separator(self) -> None:
        md = _format_review(_make_review())
        assert "---" in md
