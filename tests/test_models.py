from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from prism.models import (
    AIAnalysis,
    AIConcern,
    Comment,
    PRComment,
    PRFile,
    PRMetadata,
    PRReview,
    PRSummary,
)


class TestComment:
    def test_stores_all_fields(self) -> None:
        c = Comment("src/a.py", 10, "looks good")
        assert c.file_path == "src/a.py"
        assert c.line_number == 10
        assert c.body == "looks good"

    def test_is_frozen(self) -> None:
        c = Comment("src/a.py", 1, "body")
        with pytest.raises(dataclasses.FrozenInstanceError):
            c.body = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert Comment("a.py", 1, "x") == Comment("a.py", 1, "x")

    def test_inequality_on_different_line(self) -> None:
        assert Comment("a.py", 1, "x") != Comment("a.py", 2, "x")


class TestPRFile:
    def test_patch_defaults_to_none(self) -> None:
        f = PRFile(filename="a.py", status="modified", additions=1, deletions=0)
        assert f.patch is None

    def test_sha_defaults_to_empty_string(self) -> None:
        f = PRFile(filename="a.py", status="added", additions=5, deletions=0)
        assert f.sha == ""

    def test_all_fields_stored(self) -> None:
        f = PRFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=3,
            patch="@@ -1 +1 @@",
            sha="abc",
        )
        assert f.filename == "src/main.py"
        assert f.additions == 10
        assert f.deletions == 3


class TestPRSummary:
    def _make(self, **kwargs) -> PRSummary:
        defaults = dict(
            number=1,
            title="T",
            author="u",
            repo_slug="o/r",
            state="open",
            base_branch="main",
            head_branch="feat",
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            html_url="https://github.com/o/r/pull/1",
            body="",
            comments=0,
        )
        defaults.update(kwargs)
        return PRSummary(**defaults)

    def test_review_state_defaults_to_none(self) -> None:
        assert self._make().review_state is None

    def test_checks_status_defaults_to_none(self) -> None:
        assert self._make().checks_status is None

    def test_state_merged(self) -> None:
        s = self._make(state="merged")
        assert s.state == "merged"

    def test_comments_count_stored(self) -> None:
        s = self._make(comments=5)
        assert s.comments == 5


class TestPRComment:
    def _make(self, **kwargs) -> PRComment:
        defaults = dict(
            id=1,
            body="body",
            author="user",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            path="src/a.py",
            line=5,
        )
        defaults.update(kwargs)
        return PRComment(**defaults)

    def test_in_reply_to_id_defaults_to_none(self) -> None:
        assert self._make().in_reply_to_id is None

    def test_path_can_be_none(self) -> None:
        c = self._make(path=None, line=None)
        assert c.path is None

    def test_diff_hunk_defaults_to_none(self) -> None:
        assert self._make().diff_hunk is None

    def test_is_frozen(self) -> None:
        c = self._make()
        with pytest.raises(Exception):
            c.body = "changed"  # type: ignore[misc]

    def test_reply_stores_parent_id(self) -> None:
        reply = self._make(in_reply_to_id=99)
        assert reply.in_reply_to_id == 99


class TestPRMetadata:
    def _make(self, **kwargs) -> PRMetadata:
        defaults = dict(
            number=1,
            title="T",
            author="u",
            state="open",
            base_branch="main",
            head_branch="feat",
        )
        defaults.update(kwargs)
        return PRMetadata(**defaults)

    def test_files_defaults_to_empty(self) -> None:
        assert self._make().files == []

    def test_review_comments_defaults_to_empty(self) -> None:
        assert self._make().review_comments == []

    def test_head_sha_defaults_to_empty(self) -> None:
        assert self._make().head_sha == ""

    def test_review_state_defaults_to_none(self) -> None:
        assert self._make().review_state is None

    def test_checks_status_defaults_to_none(self) -> None:
        assert self._make().checks_status is None

    def test_body_defaults_to_empty(self) -> None:
        assert self._make().body == ""

    def test_model_copy_does_not_mutate_original(self) -> None:
        pr = self._make(review_state=None)
        updated = pr.model_copy(update={"review_state": "APPROVED"})
        assert updated.review_state == "APPROVED"
        assert pr.review_state is None


class TestPRReview:
    def test_stores_all_fields(self) -> None:
        r = PRReview(
            id=10,
            body="Looks good",
            author="reviewer",
            state="APPROVED",
            submitted_at=datetime(2024, 6, 1, tzinfo=UTC),
            html_url="https://github.com/o/r/pull/1#review-10",
        )
        assert r.id == 10
        assert r.state == "APPROVED"
        assert r.author == "reviewer"

    def test_is_frozen(self) -> None:
        r = PRReview(
            id=1,
            body="",
            author="u",
            state="APPROVED",
            submitted_at=datetime(2024, 1, 1, tzinfo=UTC),
            html_url="",
        )
        with pytest.raises(Exception):
            r.state = "DISMISSED"  # type: ignore[misc]


class TestAIConcern:
    def test_stores_title_and_description(self) -> None:
        c = AIConcern(title="Security", description="SQL injection risk")
        assert c.title == "Security"
        assert c.description == "SQL injection risk"

    def test_is_frozen(self) -> None:
        c = AIConcern(title="T", description="D")
        with pytest.raises(Exception):
            c.title = "changed"  # type: ignore[misc]


class TestAIAnalysis:
    def test_defaults(self) -> None:
        a = AIAnalysis(summary="ok", risk="low", concerns=[])
        assert a.suggested_comment == ""
        assert a.concerns == []

    def test_concerns_list(self) -> None:
        concern = AIConcern(title="T", description="D")
        a = AIAnalysis(summary="s", risk="high", concerns=[concern])
        assert len(a.concerns) == 1
        assert a.concerns[0].title == "T"

    def test_is_frozen(self) -> None:
        a = AIAnalysis(summary="s", risk="low", concerns=[])
        with pytest.raises(Exception):
            a.risk = "high"  # type: ignore[misc]
