"""Control base classes: state every control shares + dirty plumbing."""
from __future__ import annotations

from . import colors
from .types import Alignment, Margin, as_padding


class Control:
    """Base of all controls. Mirrors flet `Control` + `LayoutControl` subset."""

    def __init__(self, *, visible: bool = True, disabled: bool = False,
                 opacity: float = 1.0, expand: bool | int | None = None,
                 tooltip: str | None = None, data=None,
                 width: float | None = None, height: float | None = None,
                 margin=None, align: Alignment | None = None,
                 left: float | None = None, top: float | None = None,
                 right: float | None = None, bottom: float | None = None):
        self.visible = visible
        self.disabled = disabled
        self.opacity = opacity
        self.expand = expand
        self.tooltip = tooltip
        self.data = data
        self._width = width
        self._height = height
        self.margin = as_padding(margin) if margin is not None and not isinstance(margin, Margin) else margin
        self.align = align
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.parent: Control | None = None
        self.page = None           # set on attach
        self._rect = (0.0, 0.0, 0.0, 0.0)  # (x, y, w, h), assigned by layout

    # -- state -----------------------------------------------------------
    @property
    def width(self) -> float | None:
        return self._width

    @width.setter
    def width(self, v: float | None):
        self._width = v
        self.update()

    @property
    def height(self) -> float | None:
        return self._height

    @height.setter
    def height(self, v: float | None):
        self._height = v
        self.update()

    def update(self):
        if self.page is not None:
            self.page.update()

    def _attach(self, page, parent: "Control | None" = None):
        self.page = page
        self.parent = parent
        for c in self._children():
            c._attach(page, self)

    def _children(self) -> list:
        return getattr(self, "controls", [])

    # -- drawing hooks (flex engine drives these) ---------------------------
    def _draw_at(self, r, x, y):
        if self.visible:
            self._draw(r, x, y)

    def _draw(self, r, x, y):
        pass

    def _draw_all(self, r, ox: float = 0.0, oy: float = 0.0):
        """Render self + subtree using the absolute rects from _place.
        (ox, oy) is the scroll translate applied by enclosing ListViews."""
        if not self.visible:
            return
        self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
        for c in self._children():
            c._draw_all(r, ox, oy)

    # theme helpers ------------------------------------------------------
    @property
    def _dark(self) -> bool:
        return colors.theme_dark

    # -- events (pointer handling; hit testing on absolute rects) ----------
    def handle_event(self, e) -> bool:
        for c in self._children():
            if c.handle_event(e):
                return True
        return False

    @property
    def _handles_tap(self) -> bool:
        return bool(getattr(self, "on_click", None) or
                    getattr(self, "_focusable", False) or
                    getattr(self, "_draggable", False))

    def _contains(self, x, y) -> bool:
        rx, ry, rw, rh = self._rect
        return rw > 0 and rh > 0 and rx <= x < rx + rw and ry <= y < ry + rh

    def _hit_test(self, x, y) -> "Control | None":
        """Deepest visible, enabled control containing (x, y) that taps."""
        if not self.visible or self.disabled:
            return None
        for c in reversed(self._children()):
            hit = c._hit_test(x, y)
            if hit is not None:
                return hit
        if self._handles_tap and self._contains(x, y):
            return self
        return None

    def _hit_test_hover(self, x, y) -> "Control | None":
        """Deepest control containing (x, y) that has on_hover."""
        if not self.visible or self.disabled:
            return None
        for c in reversed(self._children()):
            hit = c._hit_test_hover(x, y)
            if hit is not None:
                return hit
        if getattr(self, "on_hover", None) and self._contains(x, y):
            return self
        return None

    def _find_scrollable(self, x, y):
        """Deepest ListView whose viewport contains (x, y)."""
        if not self.visible:
            return None
        for c in reversed(self._children()):
            found = c._find_scrollable(x, y)
            if found is not None:
                return found
        return None

    # keyboard hooks (TextField overrides; page routes when focused)
    def _key(self, e):
        pass

    def _text_input(self, t):
        pass
