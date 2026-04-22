from __future__ import annotations

from prism.cli import _parse_github_url


class TestParseGithubUrl:
    def test_parses_standard_pr_url(self) -> None:
        result = _parse_github_url("https://github.com/owner/repo/pull/42")
        assert result == ("owner/repo", 42)

    def test_parses_url_with_trailing_slash(self) -> None:
        result = _parse_github_url("https://github.com/owner/repo/pull/42/")
        assert result == ("owner/repo", 42)

    def test_parses_http_url(self) -> None:
        result = _parse_github_url("http://github.com/owner/repo/pull/100")
        assert result == ("owner/repo", 100)

    def test_parses_org_repo_url(self) -> None:
        result = _parse_github_url("https://github.com/acme-corp/my-service/pull/7")
        assert result == ("acme-corp/my-service", 7)

    def test_parses_large_pr_number(self) -> None:
        result = _parse_github_url("https://github.com/owner/repo/pull/99999")
        assert result == ("owner/repo", 99999)

    def test_returns_none_for_plain_repo_string(self) -> None:
        assert _parse_github_url("owner/repo") is None

    def test_returns_none_for_empty_string(self) -> None:
        assert _parse_github_url("") is None

    def test_returns_none_for_non_github_url(self) -> None:
        assert _parse_github_url("https://gitlab.com/owner/repo/merge_requests/1") is None

    def test_returns_none_for_github_repo_without_pull(self) -> None:
        assert _parse_github_url("https://github.com/owner/repo") is None

    def test_pr_number_is_int(self) -> None:
        result = _parse_github_url("https://github.com/owner/repo/pull/5")
        assert result is not None
        assert isinstance(result[1], int)
