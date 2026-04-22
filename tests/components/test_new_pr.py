from __future__ import annotations

import pytest

from prism.components.modals.new_pr import _parse


class TestParse:
    # ── GitHub URLs ────────────────────────────────────────────────────────────

    def test_parses_https_url(self) -> None:
        assert _parse("https://github.com/owner/repo/pull/42") == ("owner/repo", 42)

    def test_parses_http_url(self) -> None:
        assert _parse("http://github.com/owner/repo/pull/7") == ("owner/repo", 7)

    def test_parses_url_with_trailing_slash(self) -> None:
        assert _parse("https://github.com/owner/repo/pull/42/") == ("owner/repo", 42)

    def test_parses_url_with_org_and_hyphens(self) -> None:
        result = _parse("https://github.com/acme-corp/my-service/pull/100")
        assert result == ("acme-corp/my-service", 100)

    # ── owner/repo formats ─────────────────────────────────────────────────────

    def test_parses_repo_space_number(self) -> None:
        assert _parse("owner/repo 42") == ("owner/repo", 42)

    def test_parses_repo_hash_number(self) -> None:
        assert _parse("owner/repo#42") == ("owner/repo", 42)

    def test_parses_repo_with_leading_whitespace(self) -> None:
        assert _parse("  owner/repo 5  ") == ("owner/repo", 5)

    def test_parses_repo_hash_no_space(self) -> None:
        assert _parse("acme/svc#99") == ("acme/svc", 99)

    # ── pr_number type ─────────────────────────────────────────────────────────

    def test_pr_number_is_int(self) -> None:
        result = _parse("owner/repo 1")
        assert result is not None
        assert isinstance(result[1], int)

    # ── Invalid inputs ─────────────────────────────────────────────────────────

    def test_returns_none_for_empty_string(self) -> None:
        assert _parse("") is None

    def test_returns_none_for_plain_repo(self) -> None:
        assert _parse("owner/repo") is None

    def test_returns_none_for_non_github_url(self) -> None:
        assert _parse("https://gitlab.com/owner/repo/merge_requests/1") is None

    def test_returns_none_for_random_text(self) -> None:
        assert _parse("just some text") is None

    def test_returns_none_for_github_url_without_pull(self) -> None:
        assert _parse("https://github.com/owner/repo") is None


class TestNewPRScreenModal:
    @pytest.mark.asyncio
    async def test_escape_dismisses_with_none(self) -> None:
        from textual.app import App, ComposeResult

        from prism.components.modals.new_pr import NewPRScreen

        result: list = []

        class _TestApp(App):
            def compose(self) -> ComposeResult:
                return iter([])

            def on_mount(self) -> None:
                self.push_screen(NewPRScreen(), callback=result.append)

        async with _TestApp().run_test() as pilot:
            await pilot.press("escape")

        assert result == [None]

    @pytest.mark.asyncio
    async def test_invalid_input_shows_error(self) -> None:
        from textual.app import App, ComposeResult
        from textual.widgets import Input, Label

        from prism.components.modals.new_pr import NewPRScreen

        result: list = []

        class _TestApp(App):
            def compose(self) -> ComposeResult:
                return iter([])

            def on_mount(self) -> None:
                self.push_screen(NewPRScreen(), callback=result.append)

        async with _TestApp().run_test() as pilot:
            pilot.app.screen.query_one(Input).value = "not a valid url"
            await pilot.click("#new-pr-open")
            error = str(pilot.app.screen.query_one("#new-pr-error", Label).render())
            assert error != ""

        # Modal stays open — no result yet
        assert result == []

    @pytest.mark.asyncio
    async def test_valid_url_dismisses_with_tuple(self) -> None:
        from textual.app import App, ComposeResult
        from textual.widgets import Input

        from prism.components.modals.new_pr import NewPRScreen

        result: list = []

        class _TestApp(App):
            def compose(self) -> ComposeResult:
                return iter([])

            def on_mount(self) -> None:
                self.push_screen(NewPRScreen(), callback=result.append)

        async with _TestApp().run_test() as pilot:
            pilot.app.screen.query_one(Input).value = "https://github.com/owner/repo/pull/99"
            await pilot.click("#new-pr-open")

        assert result == [("owner/repo", 99)]
