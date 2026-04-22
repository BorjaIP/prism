from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from prism.models import AIAnalysis, PRFile, PRMetadata
from prism.services.ai import _build_prompt, _cache_key, _parse_response


def _make_pr(**kwargs) -> PRMetadata:
    defaults = dict(
        number=1,
        title="Add caching layer",
        author="alice",
        state="open",
        base_branch="main",
        head_branch="feat/cache",
        body="This PR adds a Redis caching layer.",
    )
    defaults.update(kwargs)
    return PRMetadata(**defaults)


def _make_file(**kwargs) -> PRFile:
    defaults = dict(
        filename="src/cache.py",
        status="added",
        additions=50,
        deletions=0,
        patch="@@ -0,0 +1,50 @@\n+class Cache:\n+    pass\n",
        sha="deadbeef",
    )
    defaults.update(kwargs)
    return PRFile(**defaults)


class TestCacheKey:
    def test_uses_sha_when_available(self) -> None:
        key = _cache_key("owner/repo", 42, _make_file(sha="abc123"))
        assert key == "ai:owner/repo:42:abc123"

    def test_falls_back_to_filename_when_sha_is_empty(self) -> None:
        # PRFile.sha defaults to "" — the cache key uses filename as fallback
        key = _cache_key("owner/repo", 42, _make_file(sha=""))
        assert key == "ai:owner/repo:42:src/cache.py"

    def test_includes_repo_slug_and_pr_number(self) -> None:
        key = _cache_key("acme/service", 7, _make_file(sha="xyz"))
        assert "acme/service" in key
        assert "7" in key


class TestBuildPrompt:
    def test_includes_pr_title(self) -> None:
        prompt = _build_prompt(_make_pr(title="My PR"), _make_file())
        assert "My PR" in prompt

    def test_includes_pr_author(self) -> None:
        prompt = _build_prompt(_make_pr(author="bob"), _make_file())
        assert "bob" in prompt

    def test_includes_filename(self) -> None:
        prompt = _build_prompt(_make_pr(), _make_file(filename="core/utils.py"))
        assert "core/utils.py" in prompt

    def test_includes_file_status(self) -> None:
        prompt = _build_prompt(_make_pr(), _make_file(status="modified"))
        assert "modified" in prompt

    def test_includes_additions_and_deletions(self) -> None:
        prompt = _build_prompt(_make_pr(), _make_file(additions=10, deletions=3))
        assert "+10" in prompt
        assert "-3" in prompt

    def test_includes_diff_patch(self) -> None:
        prompt = _build_prompt(_make_pr(), _make_file(patch="+ new line\n"))
        assert "new line" in prompt

    def test_truncates_patch_to_8000_chars(self) -> None:
        long_patch = "+" + "x" * 9000
        prompt = _build_prompt(_make_pr(), _make_file(patch=long_patch))
        # The patch portion should be at most 8000 chars
        assert len(prompt) < 9000 + 500  # + PR metadata overhead

    def test_truncates_body_to_2000_chars(self) -> None:
        long_body = "Z" * 3000  # unique char unlikely to appear elsewhere
        prompt = _build_prompt(_make_pr(body=long_body), _make_file())
        assert prompt.count("Z") == 2000

    def test_uses_none_placeholder_for_empty_body(self) -> None:
        prompt = _build_prompt(_make_pr(body=""), _make_file())
        assert "(none)" in prompt

    def test_includes_pr_description(self) -> None:
        prompt = _build_prompt(_make_pr(body="Fixes the memory leak"), _make_file())
        assert "Fixes the memory leak" in prompt


class TestParseResponse:
    def _valid_json(self, **kwargs) -> str:
        data = {
            "summary": "This change adds caching.",
            "risk": "low",
            "concerns": [],
            "suggested_comment": "",
        }
        data.update(kwargs)
        return json.dumps(data)

    def test_parses_valid_json(self) -> None:
        result = _parse_response(self._valid_json())
        assert isinstance(result, AIAnalysis)
        assert result.summary == "This change adds caching."
        assert result.risk == "low"

    def test_strips_markdown_fences(self) -> None:
        raw = "```json\n" + self._valid_json() + "\n```"
        result = _parse_response(raw)
        assert isinstance(result, AIAnalysis)
        assert result.risk == "low"

    def test_parses_concerns(self) -> None:
        raw = self._valid_json(concerns=[{"title": "Security", "description": "XSS risk"}])
        result = _parse_response(raw)
        assert len(result.concerns) == 1
        assert result.concerns[0].title == "Security"

    def test_risk_is_lowercased(self) -> None:
        raw = self._valid_json(risk="HIGH")
        result = _parse_response(raw)
        assert result.risk == "high"

    def test_returns_error_analysis_for_invalid_json(self) -> None:
        result = _parse_response("this is not json {{")
        assert isinstance(result, AIAnalysis)
        assert result.concerns[0].title == "Parse error"

    def test_returns_error_analysis_for_empty_string(self) -> None:
        result = _parse_response("")
        assert isinstance(result, AIAnalysis)

    def test_suggested_comment_defaults_to_empty(self) -> None:
        raw = json.dumps({"summary": "s", "risk": "low", "concerns": []})
        result = _parse_response(raw)
        assert result.suggested_comment == ""

    def test_parses_suggested_comment(self) -> None:
        raw = self._valid_json(suggested_comment="Consider refactoring this.")
        result = _parse_response(raw)
        assert result.suggested_comment == "Consider refactoring this."

    def test_handles_missing_summary_key(self) -> None:
        raw = json.dumps({"risk": "low", "concerns": []})
        result = _parse_response(raw)
        assert result.summary == ""


class TestGetAnthropicClient:
    def test_raises_when_api_key_missing(self) -> None:
        from prism.services.ai import _get_anthropic_client

        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                _get_anthropic_client()

    def test_returns_client_when_key_present(self) -> None:
        from prism.services.ai import _get_anthropic_client

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            client = _get_anthropic_client()

        assert client is not None


class TestAnalyzeFileSkipsRemoved:
    def test_returns_static_analysis_for_removed_file(self) -> None:
        from prism.services.ai import analyze_file

        pr = _make_pr()
        removed_file = _make_file(status="removed")

        result = analyze_file(pr, removed_file, "o/r", 1)

        assert isinstance(result, AIAnalysis)
        assert "removed" in result.summary.lower()
        assert result.risk == "low"
        assert result.concerns == []
