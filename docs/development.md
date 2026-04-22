# Development Guide

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — package manager and virtual environment
- Python 3.11+

Install dependencies:

```bash
uv sync
```

---

## Running the app

### Normal mode

```bash
uv run prism
```

### Dev mode — with Textual devtools

Textual devtools give you a live debug console where `print()` calls and internal
Textual log messages appear without breaking the TUI.

It requires **two terminals running at the same time**.

**Terminal 1 — start the debug console:**

```bash
make console
# equivalent: uv run textual console -x SYSTEM -x EVENT
```

`-x SYSTEM -x EVENT` filters out the noisiest Textual internal groups so you only
see your own logs plus `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `PRINT` messages.
Remove those flags if you need to inspect Textual internals.

**Terminal 2 — run the app in dev mode:**

```bash
make build
# equivalent: TEXTUAL=devtools,debug uv run prism
```

The `TEXTUAL` environment variable accepts a comma-separated list of flags:

| Flag       | Effect                                                               |
|------------|----------------------------------------------------------------------|
| `devtools` | Connects the app to the console started with `textual console`       |
| `debug`    | Enables additional debug output inside the app (e.g. CSS reload)     |

When both are active, any `print()` or `self.log()` call in the app streams to
Terminal 1 in real time.

### Logging from code

```python
from textual.app import App

class PRismApp(App):
    def on_mount(self) -> None:
        self.log("App mounted")          # appears in the devtools console
        self.log.debug("Debug info")
        self.log.warning("Something off")
        print("Also works")              # captured by devtools when active
```

---

## Code formatting

All formatting is handled by **Ruff**, configured in `pyproject.toml`.

| Command        | Effect                                         |
|----------------|------------------------------------------------|
| `make format`  | Format only (style, no logic changes)          |
| `make lint`    | Show lint errors without modifying files       |
| `make fix`     | Apply auto-fixes + format (most common)        |
| `make check`   | Validate without modifying (CI use)            |

VSCode uses the same Ruff config via `ruff.configuration: pyproject.toml`, so
the output is identical whether you save in the editor or run `make fix`.
