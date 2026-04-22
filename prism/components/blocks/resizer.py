from __future__ import annotations

from textual import events
from textual.app import RenderResult
from textual.widget import Widget


class PanelResizer(Widget):
    """A 1-cell wide vertical drag handle that resizes its two neighbour panels.

    Parameters
    ----------
    left_id:
        CSS id of the panel to the left of this resizer.
    right_id:
        CSS id of the panel to the right of this resizer.
    flex:
        Which side is the flexible (``1fr``) panel.  That side's width is
        never overwritten with a fixed integer so the layout engine keeps
        distributing space naturally.  Use ``"left"``, ``"right"``, or
        ``"none"`` (default) when both panels have fixed widths.
    """

    DEFAULT_CSS = """
    PanelResizer {
        width: 1;
        background: $surface-lighten-1;
    }
    PanelResizer:hover {
        background: $accent 40%;
    }
    PanelResizer.-dragging {
        background: $accent;
    }
    """

    MIN_WIDTH = 12

    def __init__(self, left_id: str, right_id: str, flex: str = "none") -> None:
        super().__init__()
        self._left_id = left_id
        self._right_id = right_id
        self._flex = flex
        self._dragging = False
        self._last_x = 0

    def render(self) -> RenderResult:
        return ""

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.capture_mouse()
        self._dragging = True
        self._last_x = event.screen_x
        self.add_class("-dragging")
        event.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if not self._dragging:
            return
        delta = event.screen_x - self._last_x
        if delta == 0:
            return
        try:
            left = self.app.query_one(f"#{self._left_id}")
            right = self.app.query_one(f"#{self._right_id}")
        except Exception:
            return
        left_w = left.size.width + delta
        right_w = right.size.width - delta
        if left_w >= self.MIN_WIDTH and right_w >= self.MIN_WIDTH:
            self._last_x = event.screen_x
            if self._flex != "left":
                left.styles.width = left_w
            if self._flex != "right":
                right.styles.width = right_w

    def on_mouse_up(self, event: events.MouseUp) -> None:
        self.release_mouse()
        self._dragging = False
        self.remove_class("-dragging")
        event.stop()
