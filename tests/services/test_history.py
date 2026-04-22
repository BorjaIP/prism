from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from prism.models import PRMetadata, PRSummary
from prism.services.history import HistoryService


def _make_pr(**kwargs) -> PRMetadata:
    defaults = dict(
        number=1,
        title="My PR",
        author="alice",
        state="open",
        base_branch="main",
        head_branch="feat",
        head_sha="abc123",
        html_url="https://github.com/o/r/pull/1",
        body="Description",
        checks_status="success",
    )
    defaults.update(kwargs)
    return PRMetadata(**defaults)


class TestNowIso:
    def test_returns_iso_format_string(self) -> None:
        result = HistoryService._now_iso()
        dt = datetime.fromisoformat(result)
        assert dt.tzinfo is not None

    def test_returns_utc_time(self) -> None:
        result = HistoryService._now_iso()
        dt = datetime.fromisoformat(result)
        assert dt.utcoffset().total_seconds() == 0


class TestLoadRaw:
    def test_returns_empty_list_when_file_missing(self, tmp_path: Path) -> None:
        svc = HistoryService(path=tmp_path / "history.json")
        assert svc._load_raw() == []

    def test_returns_list_from_valid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(json.dumps([{"number": 1}]))
        assert HistoryService(path=path)._load_raw() == [{"number": 1}]

    def test_returns_empty_list_for_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text("not json{{{")
        assert HistoryService(path=path)._load_raw() == []

    def test_returns_empty_list_when_json_is_not_a_list(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(json.dumps({"key": "value"}))
        assert HistoryService(path=path)._load_raw() == []


class TestSaveToHistory:
    def test_creates_file_and_writes_entry(self, tmp_path: Path) -> None:
        path = tmp_path / "prism" / "history.json"
        HistoryService(path=path).save(_make_pr(number=5), "owner/repo")

        data = json.loads(path.read_text())
        assert len(data) == 1
        assert data[0]["number"] == 5
        assert data[0]["repo_slug"] == "owner/repo"

    def test_inserts_at_top(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(json.dumps([{"number": 1, "repo_slug": "o/r"}]))

        HistoryService(path=path).save(_make_pr(number=2), "o/r")

        data = json.loads(path.read_text())
        assert data[0]["number"] == 2

    def test_deduplicates_same_pr(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(json.dumps([{"number": 42, "repo_slug": "o/r", "title": "old"}]))

        HistoryService(path=path).save(_make_pr(number=42, title="new"), "o/r")

        data = json.loads(path.read_text())
        assert len(data) == 1
        assert data[0]["title"] == "new"

    def test_truncates_body_to_500_chars(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        HistoryService(path=path).save(_make_pr(body="x" * 1000), "o/r")

        data = json.loads(path.read_text())
        assert len(data[0]["body"]) == 500

    def test_keeps_max_50_entries(self, tmp_path: Path) -> None:
        from prism.constants import HISTORY_MAX_ENTRIES

        path = tmp_path / "history.json"
        existing = [{"number": i, "repo_slug": "o/r"} for i in range(HISTORY_MAX_ENTRIES)]
        path.write_text(json.dumps(existing))

        HistoryService(path=path).save(_make_pr(number=999), "o/r")

        data = json.loads(path.read_text())
        assert len(data) == HISTORY_MAX_ENTRIES
        assert data[0]["number"] == 999


class TestDeleteFromHistory:
    def test_removes_matching_entry(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(
            json.dumps([{"number": 1, "repo_slug": "o/r"}, {"number": 2, "repo_slug": "o/r"}])
        )

        HistoryService(path=path).delete("o/r", 1)

        data = json.loads(path.read_text())
        assert len(data) == 1
        assert data[0]["number"] == 2

    def test_no_op_when_entry_not_found(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(json.dumps([{"number": 1, "repo_slug": "o/r"}]))

        HistoryService(path=path).delete("o/r", 99)

        data = json.loads(path.read_text())
        assert len(data) == 1

    def test_writes_empty_list_when_last_entry_deleted(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(json.dumps([{"number": 1, "repo_slug": "o/r"}]))

        HistoryService(path=path).delete("o/r", 1)

        data = json.loads(path.read_text())
        assert data == []


class TestLoadHistory:
    def test_returns_pr_summary_objects(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "number": 7,
                        "title": "Fix bug",
                        "author": "bob",
                        "repo_slug": "o/r",
                        "state": "open",
                        "base_branch": "main",
                        "head_branch": "fix",
                        "html_url": "https://github.com/o/r/pull/7",
                        "opened_at": "2024-06-01T10:00:00+00:00",
                    }
                ]
            )
        )

        result = HistoryService(path=path).load()

        assert len(result) == 1
        assert isinstance(result[0], PRSummary)
        assert result[0].number == 7
        assert result[0].title == "Fix bug"

    def test_skips_malformed_entries(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(
            json.dumps(
                [
                    {"broken": "entry"},
                    {
                        "number": 1,
                        "title": "Good PR",
                        "repo_slug": "o/r",
                        "opened_at": "2024-06-01T10:00:00+00:00",
                    },
                ]
            )
        )

        result = HistoryService(path=path).load()
        assert len(result) == 1
        assert result[0].number == 1

    def test_returns_empty_for_no_history(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        assert HistoryService(path=path).load() == []
