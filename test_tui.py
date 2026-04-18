"""Quick smoke test — launches the TUI with mock PR data."""

from prism.app import PRismApp
from prism.models import PRFile, PRMetadata

MOCK_PATCH = """\
@@ -1,7 +1,15 @@
 import os
+import sys
+from pathlib import Path

 def main():
-    print("hello")
+    name = os.getenv("USER", "world")
+    print(f"hello {name}")
+
+    config_path = Path.home() / ".config" / "app.toml"
+    if config_path.exists():
+        print(f"Config found at {config_path}")
+    else:
+        print("No config found, using defaults")

 if __name__ == "__main__":
     main()
"""

pr = PRMetadata(
    number=142,
    title="feat: add config file support and improve greeting",
    author="octocat",
    state="open",
    base_branch="main",
    head_branch="feature/config-support",
    html_url="https://github.com/example/repo/pull/142",
    body="This PR adds config file support and personalizes the greeting.",
    files=[
        PRFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=1,
            patch=MOCK_PATCH,
            sha="abc123",
        ),
        PRFile(
            filename="src/config/__init__.py",
            status="added",
            additions=0,
            deletions=0,
            patch="",
            sha="def456",
        ),
        PRFile(
            filename="src/config/loader.py",
            status="added",
            additions=35,
            deletions=0,
            patch="+from pathlib import Path\n+import tomllib\n+\n+def load(path):\n+    with open(path, 'rb') as f:\n+        return tomllib.load(f)",
            sha="ghi789",
        ),
        PRFile(
            filename="tests/test_config.py",
            status="added",
            additions=22,
            deletions=0,
            patch="+import pytest\n+from src.config.loader import load\n+\n+def test_load_valid():\n+    pass",
            sha="jkl012",
        ),
        PRFile(
            filename="old_utils.py",
            status="removed",
            additions=0,
            deletions=15,
            patch="-# Old utility module\n-def deprecated_func():\n-    pass",
            sha="mno345",
        ),
        PRFile(
            filename="docs/README.md",
            status="modified",
            additions=5,
            deletions=2,
            patch="@@ -1,5 +1,8 @@\n # My App\n-Simple app.\n+Feature-rich app with config support.\n+\n+## Configuration\n+Place config.toml in ~/.config/app/",
            sha="pqr678",
        ),
    ],
)

if __name__ == "__main__":
    app = PRismApp(pr, "example/repo", 142)
    app.run()
