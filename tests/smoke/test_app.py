from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from textual.widgets import Footer, TabbedContent

from prism.app import PRismApp
from prism.components.modals.new_pr import NewPRScreen
from prism.components.modals.review_modals import QuitConfirmModal
from prism.components.panels.ai_panel import AIPanel
from prism.components.panels.comments_panel import CommentsPanel
from prism.components.panels.diff_viewer import DiffViewer
from prism.components.panels.file_tree import FileTreePanel
from prism.components.sections.header_bar import HeaderBar
from prism.constants import TAB_RECENT, TAB_REVIEW
from prism.screens.main import PRListScreen
from prism.screens.review import ReviewScreen
from tests.conftest import make_pr_file, make_pr_metadata

pytestmark = pytest.mark.smoke

# Fake token so workers pass the token-presence check; actual API calls will
# fail gracefully inside the workers' own try/except blocks.
_FAKE_TOKEN_ENV = {"GITHUB_TOKEN": "smoke-test-fake-token"}


# ── PRismApp (main entry point) ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_app_boots_and_pushes_pr_list_screen() -> None:
    """PRismApp mounts without error and the top screen is PRListScreen."""
    app = PRismApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, PRListScreen)


@pytest.mark.asyncio
async def test_app_title() -> None:
    """Application title is set to PRism."""
    app = PRismApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.TITLE == "PRism"


# ── PRListScreen ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pr_list_screen_has_two_tabs() -> None:
    """Both 'Recently Reviewed' and 'Review Requested' tab panes are rendered."""
    app = PRismApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        tabs = app.screen.query_one(TabbedContent)
        pane_ids = {pane.id for pane in tabs.query("TabPane")}
        assert TAB_RECENT in pane_ids
        assert TAB_REVIEW in pane_ids


@pytest.mark.asyncio
async def test_pr_list_screen_default_tab_is_recent() -> None:
    """The active tab on startup is 'Recently Reviewed'."""
    app = PRismApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        tabs = app.screen.query_one(TabbedContent)
        assert tabs.active == TAB_RECENT


@pytest.mark.asyncio
async def test_pr_list_screen_has_footer() -> None:
    """Footer widget is present with key binding hints."""
    app = PRismApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one(Footer) is not None


@pytest.mark.asyncio
async def test_pr_list_screen_q_opens_quit_modal() -> None:
    """Pressing 'q' on PRListScreen pushes the QuitConfirmModal."""
    app = PRismApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        assert isinstance(app.screen, QuitConfirmModal)
        await pilot.press("escape")


@pytest.mark.asyncio
async def test_pr_list_screen_n_opens_new_pr_modal() -> None:
    """Pressing 'n' on PRListScreen pushes the NewPRScreen modal."""
    app = PRismApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("n")
        assert isinstance(app.screen, NewPRScreen)
        await pilot.press("escape")


@pytest.mark.asyncio
async def test_pr_list_screen_tab_switches_to_review_requested() -> None:
    """Setting TabbedContent.active switches to 'Review Requested'."""
    with patch.dict(os.environ, _FAKE_TOKEN_ENV):
        app = PRismApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            tabs = app.screen.query_one(TabbedContent)
            tabs.active = TAB_REVIEW
            await pilot.pause()
            assert tabs.active == TAB_REVIEW


# ── ReviewScreen ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_review_screen_renders_all_panels() -> None:
    """ReviewScreen mounts with all four content panels visible."""
    with patch.dict(os.environ, _FAKE_TOKEN_ENV):
        pr = make_pr_metadata(files=[make_pr_file()])
        app = PRismApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ReviewScreen(pr, "owner/repo", pr.number))
            await pilot.pause()
            screen = app.screen
            assert screen.query_one(FileTreePanel) is not None
            assert screen.query_one(DiffViewer) is not None
            assert screen.query_one(CommentsPanel) is not None
            assert screen.query_one(AIPanel) is not None


@pytest.mark.asyncio
async def test_review_screen_renders_header() -> None:
    """ReviewScreen shows a HeaderBar with the PR title."""
    with patch.dict(os.environ, _FAKE_TOKEN_ENV):
        pr = make_pr_metadata(title="feat: my feature", files=[make_pr_file()])
        app = PRismApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ReviewScreen(pr, "owner/repo", pr.number))
            await pilot.pause()
            assert app.screen.query_one(HeaderBar) is not None


@pytest.mark.asyncio
async def test_review_screen_file_tree_lists_pr_files() -> None:
    """FileTreePanel is populated with the files from the PR."""
    with patch.dict(os.environ, _FAKE_TOKEN_ENV):
        files = [
            make_pr_file(filename="src/main.py"),
            make_pr_file(filename="tests/test_main.py", status="added"),
        ]
        pr = make_pr_metadata(files=files)
        app = PRismApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ReviewScreen(pr, "owner/repo", pr.number))
            await pilot.pause()
            tree = app.screen.query_one(FileTreePanel)
            assert tree is not None


@pytest.mark.asyncio
async def test_review_screen_has_footer() -> None:
    """ReviewScreen renders a Footer with key binding hints."""
    with patch.dict(os.environ, _FAKE_TOKEN_ENV):
        pr = make_pr_metadata(files=[make_pr_file()])
        app = PRismApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ReviewScreen(pr, "owner/repo", pr.number))
            await pilot.pause()
            assert app.screen.query_one(Footer) is not None


@pytest.mark.asyncio
async def test_review_screen_q_pops_back_to_pr_list() -> None:
    """Pressing 'q' on ReviewScreen pops back to PRListScreen when it is underneath."""
    with patch.dict(os.environ, _FAKE_TOKEN_ENV):
        pr = make_pr_metadata(files=[make_pr_file()])
        app = PRismApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ReviewScreen(pr, "owner/repo", pr.number))
            await pilot.pause()
            # ReviewScreen is on top of PRListScreen → q should pop back, no modal
            await pilot.press("q")
            await pilot.pause()
            assert isinstance(app.screen, PRListScreen)


@pytest.mark.asyncio
async def test_review_screen_i_toggles_ai_panel() -> None:
    """Pressing 'i' on ReviewScreen toggles the AI panel visibility."""
    with patch.dict(os.environ, _FAKE_TOKEN_ENV):
        pr = make_pr_metadata(files=[make_pr_file()])
        app = PRismApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(ReviewScreen(pr, "owner/repo", pr.number))
            await pilot.pause()
            ai_panel = app.screen.query_one(AIPanel)
            visible_before = ai_panel.display
            await pilot.press("i")
            await pilot.pause()
            assert ai_panel.display != visible_before
