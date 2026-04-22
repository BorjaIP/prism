.PHONY: format lint check fix test console build

format:
	uv run ruff format .

lint:
	uv run ruff check .

fix:
	uv run ruff check --fix .
	uv run ruff format .

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run python scripts/check_no_module_docstring.py prism/ tests/

test: fix
	uv run pytest

# Open the Textual debug console (run this in a separate terminal before 'make build')
console:
	uv run textual console -x SYSTEM -x EVENT

# Run the app in dev mode — connect to the console started with 'make console'
build:
	TEXTUAL=devtools,debug uv run prism
