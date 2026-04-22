import ast
import sys
from pathlib import Path

RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def check(path: Path) -> list[str]:
    errors: list[str] = []
    files = path.rglob("*.py") if path.is_dir() else [path]
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        if ast.get_docstring(tree):
            errors.append(str(f))
    return errors


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: check_no_module_docstring.py <path> [path ...]")
        sys.exit(0)

    errors: list[str] = []
    for arg in sys.argv[1:]:
        errors.extend(check(Path(arg)))

    if errors:
        print(f"\n{BOLD}{RED}Module docstrings are not allowed{RESET}")
        print(f"{YELLOW}Remove the triple-quoted string at the top of these files:{RESET}\n")
        for f in errors:
            print(f"  {RED}✗{RESET}  {f}:1")
        print(
            f"\n{BOLD}{len(errors)} file{'s' if len(errors) != 1 else ''} with module docstring{'s' if len(errors) != 1 else ''}{RESET}\n"
        )
        sys.exit(1)

    print(f"{BOLD}No module docstrings found.{RESET}")


if __name__ == "__main__":
    main()
