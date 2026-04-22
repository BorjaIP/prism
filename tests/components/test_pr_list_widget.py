from __future__ import annotations

from datetime import UTC, datetime, timedelta

from prism.components.sections.pr_list_widget import _relative_time


def _ago(seconds: int) -> datetime:
    """Return a UTC datetime that many seconds in the past."""
    return datetime.now(tz=UTC) - timedelta(seconds=seconds)


class TestRelativeTime:
    def test_seconds(self) -> None:
        assert _relative_time(_ago(30)) == "30s"

    def test_seconds_boundary(self) -> None:
        assert _relative_time(_ago(59)) == "59s"

    def test_minutes(self) -> None:
        result = _relative_time(_ago(90))  # 1m 30s
        assert result == "1m"

    def test_minutes_boundary(self) -> None:
        result = _relative_time(_ago(59 * 60))  # 59m
        assert result == "59m"

    def test_hours(self) -> None:
        result = _relative_time(_ago(2 * 3600))  # 2h
        assert result == "2h"

    def test_hours_boundary(self) -> None:
        result = _relative_time(_ago(23 * 3600))  # 23h
        assert result == "23h"

    def test_days(self) -> None:
        result = _relative_time(_ago(3 * 86400))  # 3d
        assert result == "3d"

    def test_days_boundary(self) -> None:
        result = _relative_time(_ago(29 * 86400))  # 29d
        assert result == "29d"

    def test_months(self) -> None:
        result = _relative_time(_ago(60 * 86400))  # 2 months
        assert result == "2mo"

    def test_months_large(self) -> None:
        result = _relative_time(_ago(365 * 86400))  # ~12 months
        assert result.endswith("mo")

    def test_naive_datetime_treated_as_utc(self) -> None:
        # Create a naive datetime that represents 5 minutes ago in UTC
        naive = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
        result = _relative_time(naive)
        assert result == "5m"

    def test_zero_seconds_returns_0s(self) -> None:
        # Exactly now — should be 0s or 1s depending on precision
        result = _relative_time(datetime.now(tz=UTC))
        assert result.endswith("s")
