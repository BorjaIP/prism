"""File tree panel showing changed files in a PR."""

from __future__ import annotations

from pathlib import PurePosixPath

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from prism.models import PRComment, PRFile

STATUS_ICONS = {
    "added": ("A", "green"),
    "modified": ("M", "yellow"),
    "removed": ("D", "red"),
    "renamed": ("R", "cyan"),
}


class FileTreePanel(Widget):
    """Tree widget showing PR files grouped by directory."""

    DEFAULT_CSS = """
    FileTreePanel Tree {
        padding: 0 1;
    }
    """

    class FileSelected(Message):
        """Posted when a file is selected in the tree."""

        def __init__(self, pr_file: PRFile) -> None:
            super().__init__()
            self.pr_file = pr_file

    def __init__(
        self,
        files: list[PRFile],
        review_comments: list[PRComment] | None = None,
    ) -> None:
        super().__init__(id="file-tree-panel")
        self._files = files
        self._comment_counts = self._build_comment_counts(review_comments or [])

    @staticmethod
    def _build_comment_counts(comments: list[PRComment]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in comments:
            if c.path:
                counts[c.path] = counts.get(c.path, 0) + 1
        return counts

    def set_files(
        self,
        files: list[PRFile],
        review_comments: list[PRComment] | None = None,
    ) -> None:
        """Replace the file list and re-render the tree (e.g. after refresh)."""
        self._files = files
        self._comment_counts = self._build_comment_counts(review_comments or [])
        tree = self.query_one("#file-tree", Tree)
        tree.clear()
        self._populate_tree(tree.root)
        tree.root.expand()
        self.border_subtitle = f"{len(files)} changed"

    def on_mount(self) -> None:
        self.border_title = "FILES"
        self.border_subtitle = f"{len(self._files)} changed"

    def compose(self) -> ComposeResult:
        tree: Tree[PRFile] = Tree("Files", id="file-tree")
        tree.root.expand()
        self._populate_tree(tree.root)
        tree.show_root = False
        yield tree

    def _populate_tree(self, root: TreeNode[PRFile]) -> None:
        """Add files to tree, grouped by directory."""
        dirs: dict[str, TreeNode[PRFile]] = {}

        for pr_file in sorted(self._files, key=lambda f: f.filename):
            path = PurePosixPath(pr_file.filename)
            parts = list(path.parts)

            # Create directory nodes as needed
            parent = root
            for i, part in enumerate(parts[:-1]):
                dir_path = "/".join(parts[: i + 1])
                if dir_path not in dirs:
                    dirs[dir_path] = parent.add(part, expand=True)
                parent = dirs[dir_path]

            # Add file leaf
            label = self._file_label(pr_file, parts[-1])
            parent.add_leaf(label, data=pr_file)

    def _file_label(self, pr_file: PRFile, name: str) -> Text:
        icon, color = STATUS_ICONS.get(pr_file.status, ("?", "white"))
        label = Text()
        label.append(f"{icon} ", style=color)
        label.append(name)
        label.append(f" +{pr_file.additions}", style="green")
        label.append(f"/-{pr_file.deletions}", style="red")
        count = self._comment_counts.get(pr_file.filename, 0)
        if count:
            label.append(f" {count}💬", style="dim")
        return label

    def on_tree_node_selected(self, event: Tree.NodeSelected[PRFile]) -> None:
        """Forward file selection as a message."""
        if event.node.data is not None:
            self.post_message(self.FileSelected(event.node.data))
