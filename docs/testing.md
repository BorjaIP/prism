# Testing Guide

## Running tests

```bash
make test
```

This runs two steps in order:

1. **`make fix`** — applies Ruff auto-fixes and formats the code so the repo is
   always clean before the test run.
2. **`pytest`** — discovers and runs all tests under `tests/`.

To run tests without the formatting step (e.g. during a quick iteration):

```bash
uv run pytest
```

## Running a specific test file or test

```bash
uv run pytest tests/screens/test_comment_composer.py
uv run pytest tests/test_reply.py::test_some_function
```

## Useful pytest flags

| Flag          | Effect                                      |
|---------------|---------------------------------------------|
| `-v`          | Verbose output (show each test name)        |
| `-x`          | Stop on first failure                       |
| `-s`          | Disable output capture (show print/log)     |
| `-k "name"`   | Run only tests whose name matches           |
| `--tb=short`  | Shorter traceback format                    |

Example:

```bash
uv run pytest -v -x --tb=short
```

## Test structure

```
tests/
├── screens/
│   └── test_comment_composer.py
├── test_reply.py
└── test_review_actions.py
```

Textual apps can be tested with the built-in `App.run_test()` async context manager:

```python
async def test_app():
    app = PRismApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
```

See the [Textual testing guide](https://textual.textualize.io/guide/testing/) for
details on `Pilot` actions (key presses, clicks, screenshots).
