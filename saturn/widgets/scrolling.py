"""Scrolling: ListView (vertical/horizontal, wheel + drag) and GestureDetector.

flet 1.0 subset: ListView(controls, horizontal, spacing, padding, on_scroll,
auto_scroll, scroll_to()); GestureDetector(content, on_tap, on_hover...).
"""
from __future__ import annotations

from .. import colors
from ..control import Control
from ..event import TapEvent, fire
from .containers import _margins


class ListView(Control):
    def __init__(self, *controls, horizontal: bool = False, spacing: float = 0,
                 padding=None, auto_scroll: bool = False, on_scroll=None,
                 **base):
        if len(controls) == 1 and isinstance(controls[0], list):
            controls = tuple(controls[0])
        super().__init__(**base)
        self.controls = list(controls)
        self.horizontal = horizontal
        self.spacing = spacing
        self.padding = padding  # resolved lazily via as_padding
        self.auto_scroll = auto_scroll
        self.on_scroll = on_scroll
        self._offset = 0.0
        self._content_size = 0.0

    def _attach(self, page, parent=None):
        super()._attach(page, parent)
        for c in self.controls:
            c._attach(page, self)

    def _children(self):
        return self.controls

    def _pad(self):
        from ..types import as_padding
        return as_padding(self.padding)

    # -- layout --------------------------------------------------------------
    def _intrinsic(self, max_w, max_h, scale):
        # fills the box the parent gives it (flet ListView expands)
        return (self._width if self._width is not None else (max_w or 0),
                self._height if self._height is not None else (max_h or 0))

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        p = self._pad()
        ix, iy = x + p.left, y + p.top
        iw, ih = w - p.left - p.right, h - p.top - p.bottom
        total = 0.0
        for k in self.controls:
            if not k.visible:
                continue
            ml, mt, mr, mb = _margins(k)
            kw, kh = k._intrinsic(iw - ml - mr, None, scale)
            if k._width is not None:
                kw = k._width
            if k._height is not None:
                kh = k._height
            if self.horizontal:
                k._place(ix + total + ml, iy + mt, kw, ih - mt - mb, scale)
                total += kw + ml + mr + self.spacing
            else:
                k._place(ix + ml, iy + total + mt, iw - ml - mr, kh, scale)
                total += kh + mt + mb + self.spacing
        self._content_size = max(0.0, total - self.spacing)
        view = ih if not self.horizontal else iw
        # clamp offset after content shrinks
        self._offset = max(0.0, min(self._offset,
                                    max(0.0, self._content_size - view)))
        if self.auto_scroll:
            self._offset = max(0.0, self._content_size - view)

    def _max_offset(self) -> float:
        p = self._pad()
        view = (self._rect[3] - p.top - p.bottom) if not self.horizontal \
            else (self._rect[2] - p.left - p.right)
        return max(0.0, self._content_size - view)

    def _scroll_by(self, delta):
        new = max(0.0, min(self._max_offset(), self._offset + delta))
        if new != self._offset:
            self._offset = new
            self.update()
            fire(self, "scroll", self._offset)

    def scroll_to(self, offset: float = 0, delta: float | None = None):
        self._scroll_by(delta if delta is not None
                        else offset - self._offset)

    def _draw_all(self, r, ox: float = 0.0, oy: float = 0.0):
        if not self.visible:
            return
        self._effects_begin(r)
        try:
            x, y, w, h = self._rect
            r.clip_push(x + ox, y + oy, w, h)
            off_x = self._offset if self.horizontal else 0.0
            off_y = self._offset if not self.horizontal else 0.0
            for c in self.controls:
                if c.visible:
                    c._draw_all(r, ox - off_x, oy - off_y)
            r.clip_pop()
            self._draw_scrollbar(r, ox, oy)
        finally:
            self._effects_end(r)

    def _draw_scrollbar(self, r, ox, oy):
        view = self._rect[3] if not self.horizontal else self._rect[2]
        if self._content_size <= view or view <= 0:
            return
        k = view / self._content_size
        bar = max(24.0, view * k)
        pos = (self._offset / self._content_size) * view
        x, y, w, h = self._rect
        if self.horizontal:
            r.fill_rect(x + ox + pos, y + oy + h - 4, bar, 3,
                        colors.parse_color(colors.Colors.OUTLINE_VARIANT),
                        radius=1.5)
        else:
            r.fill_rect(x + ox + w - 4, y + oy + pos, 3, bar,
                        colors.parse_color(colors.Colors.OUTLINE_VARIANT),
                        radius=1.5)

    # -- interaction ----------------------------------------------------------
    def _hit_test(self, x, y):
        # the viewport itself handles wheel; taps pass through to children
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        off_x = self._offset if self.horizontal else 0.0
        off_y = self._offset if not self.horizontal else 0.0
        for c in reversed(self.controls):
            hit = c._hit_test(x + off_x, y + off_y)
            if hit is not None:
                return hit
        return None

    def _find_scrollable(self, x, y):
        if not self.visible or not self._contains(x, y):
            return None
        for c in reversed(self.controls):
            found = c._find_scrollable(x, y)
            if found is not None:
                return found
        return self

    def _wheel(self, delta):
        self._scroll_by(delta)


class GestureDetector(Control):
    def __init__(self, content=None, *, on_tap=None, on_tap_down=None,
                 on_long_press=None, on_hover=None, on_enter=None, on_exit=None,
                 mouse_cursor=None, drag_interval=0, hover_interval=0, **base):
        super().__init__(**base)
        self.content = content
        self.on_tap = on_tap
        self.on_tap_down = on_tap_down
        self.on_long_press = on_long_press
        self.on_hover = on_hover
        self.on_enter = on_enter
        self.on_exit = on_exit
        self.mouse_cursor = mouse_cursor
        self.on_click = self._clicked  # internal routing
        self._hovered = False
        self._pressed = False

    def _attach(self, page, parent=None):
        super()._attach(page, parent)
        if self.content is not None:
            self.content._attach(page, self)

    def _children(self):
        return [self.content] if self.content is not None else []

    def _intrinsic(self, max_w, max_h, scale):
        if self.content is None:
            return (self._width or 0, self._height or 0)
        w, h = self.content._intrinsic(max_w, max_h, scale)
        return (self._width or w, self._height or h)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        if self.content is not None:
            self.content._place(x, y, w, h, scale)

    def _draw(self, r, x, y):
        pass

    def _hit_test(self, x, y):
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        if self.content is not None:
            hit = self.content._hit_test(x, y)
            if hit is not None:
                return hit
        return self

    def _hit_test_hover(self, x, y):
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        return self

    # pointer hooks ------------------------------------------------------------
    def _pressed_hook(self, x, y):
        if self.on_tap_down is not None:
            gx, gy = x, y
            fire(self, "tap_down",
                 TapEvent(kind="down", local_position=(x - self._rect[0], y - self._rect[1]),
                          global_position=(gx, gy)))

    def _clicked(self):
        fire(self, "tap",
             TapEvent(kind="tap", local_position=(0, 0),
                      global_position=self._rect[:2]))
