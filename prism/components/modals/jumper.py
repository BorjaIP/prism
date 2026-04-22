from __future__ import annotations

import string

from textual.widget import Widget

# Keys used as jump targets (a-z, then digits)
_JUMP_KEYS = list(string.ascii_lowercase) + list(string.digits)


class Jumper:
    """Assign jump keys to a list of widgets and resolve selections."""

    def __init__(self, targets: list[tuple[str, Widget]]) -> None:
        """
        Args:
            targets: Ordered list of (label, widget) pairs to jump to.
                     The label is a human-readable name shown in the overlay.
        """
        self._targets: dict[str, tuple[str, Widget]] = {}
        for i, (label, widget) in enumerate(targets):
            if i >= len(_JUMP_KEYS):
                break
            key = _JUMP_KEYS[i]
            self._targets[key] = (label, widget)

    @property
    def assignments(self) -> dict[str, tuple[str, Widget]]:
        """Mapping of jump key → (label, widget)."""
        return dict(self._targets)

    def resolve(self, key: str) -> Widget | None:
        """Return the widget for a given key, or None if not found."""
        entry = self._targets.get(key.lower())
        return entry[1] if entry else None
