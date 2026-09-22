"""Scrolling: ListView (vertical/horizontal, wheel + drag) and GestureDetector.

flet 1.0 subset: ListView(controls, horizontal, spacing, padding, on_scroll,
auto_scroll, scroll_to()); GestureDetector(content, on_tap, on_hover...).
"""
from __future__ import annotations

import time

from .. import colors
from .. import motion
from ..control import Control
from ..event import TapEvent, fire
from .containers import _margins


_SCROLLBAR_THICKNESS = 8.0
_SCROLLBAR_HOVER_THICKNESS = 10.0
_SCROLLBAR_HIT_SIZE = 16.0
_SCROLLBAR_MARGIN = 2.0
_MIN_THUMB_SIZE = 32.0
_SCROLLBAR_FADE_DELAY = 0.6
_SCROLLBAR_IDLE_OPACITY = 0.48
_SCROLLBAR_ACTIVE_OPACITY = 0.64


class ListView(Control):
    def __init__(self, *items, controls=None, horizontal: bool = False,
                 spacing: float = 0,
                 padding=None, auto_scroll: bool = False, on_scroll=None,
                 **base):
        if controls is not None:
            if items:
                raise TypeError("controls cannot be combined with positional children")
            items = tuple(controls)
        elif len(items) == 1 and isinstance(items[0], list):
            items = tuple(items[0])
        super().__init__(**base)
        self.controls = list(items)
        self.horizontal = horizontal
        self.spacing = spacing
        self.padding = padding  # resolved lazily via as_padding
        self.auto_scroll = auto_scroll
        self.on_scroll = on_scroll
        self._offset = 0.0
        self._content_size = 0.0
        self._scrollbar_dragging = False
        self._scrollbar_drag_delta = 0.0
        self._scrollbar_hovered = False
        self._scrollbar_thickness = _SCROLLBAR_THICKNESS
        self._scrollbar_opacity = 0.0
        self._scrollbar_hide_at = None

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
            self._show_scrollbar()
            self.update()
            fire(self, "scroll", self._offset)

    def _show_scrollbar(self, *, active: bool = False):
        """Reveal the Material scrollbar for scrolling or interaction."""
        active = active or self._scrollbar_hovered or self._scrollbar_dragging
        self._scrollbar_hide_at = None if active else (
            time.perf_counter() + _SCROLLBAR_FADE_DELAY)
        self._animate_internal(
            "_scrollbar_thickness",
            _SCROLLBAR_HOVER_THICKNESS if active else _SCROLLBAR_THICKNESS,
            motion.SHORT2, motion.STANDARD)
        self._animate_internal(
            "_scrollbar_opacity",
            _SCROLLBAR_ACTIVE_OPACITY if active else _SCROLLBAR_IDLE_OPACITY,
            motion.SHORT2, motion.STANDARD)

    def _schedule_scrollbar_hide(self):
        if not self._scrollbar_hovered and not self._scrollbar_dragging:
            self._scrollbar_hide_at = (
                time.perf_counter() + _SCROLLBAR_FADE_DELAY)
            if self.page is not None:
                self.page._app.mark_dirty()

    def _scrollbar_geometry(self):
        """Return (track, thumb, travel) in page coordinates."""
        x, y, w, h = self._rect
        p = self._pad()
        if self.horizontal:
            start = x + p.left
            extent = max(0.0, w - p.left - p.right)
            view = extent
        else:
            start = y + p.top
            extent = max(0.0, h - p.top - p.bottom)
            view = extent
        max_offset = self._max_offset()
        if max_offset <= 0.0 or view <= 0.0 or self._content_size <= 0.0:
            return None
        thumb_size = min(
            extent, max(_MIN_THUMB_SIZE, extent * view / self._content_size))
        travel = max(0.0, extent - thumb_size)
        thumb_start = start + (
            travel * self._offset / max_offset if max_offset > 0 else 0.0)
        thickness = self._scrollbar_thickness
        if self.horizontal:
            track = (start, y + h - _SCROLLBAR_HIT_SIZE,
                     extent, _SCROLLBAR_HIT_SIZE)
            thumb = (thumb_start, y + h - _SCROLLBAR_MARGIN - thickness,
                     thumb_size, thickness)
        else:
            track = (x + w - _SCROLLBAR_HIT_SIZE, start,
                     _SCROLLBAR_HIT_SIZE, extent)
            thumb = (x + w - _SCROLLBAR_MARGIN - thickness, thumb_start,
                     thickness, thumb_size)
        return track, thumb, travel

    @staticmethod
    def _point_in(rect, x, y):
        rx, ry, rw, rh = rect
        return rx <= x < rx + rw and ry <= y < ry + rh

    def _scrollbar_offset_from_pointer(self, coordinate):
        geometry = self._scrollbar_geometry()
        if geometry is None:
            return
        track, _thumb, travel = geometry
        track_start = track[0] if self.horizontal else track[1]
        thumb_start = coordinate - self._scrollbar_drag_delta
        fraction = (thumb_start - track_start) / travel if travel > 0 else 0.0
        new = max(0.0, min(self._max_offset(), fraction * self._max_offset()))
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
        geometry = self._scrollbar_geometry()
        opacity = self._scrollbar_opacity
        if geometry is None or opacity <= 0.001:
            return
        _track, thumb, _travel = geometry
        x, y, w, h = thumb
        r.opacity_push(max(0.0, min(1.0, opacity)))
        try:
            if self.horizontal:
                r.fill_rect(
                    x + ox, y + oy, w, h,
                    colors.parse_color(colors.Colors.ON_SURFACE_VARIANT),
                    radius=h / 2)
            else:
                r.fill_rect(
                    x + ox, y + oy, w, h,
                    colors.parse_color(colors.Colors.ON_SURFACE_VARIANT),
                    radius=w / 2)
        finally:
            r.opacity_pop()

    # -- interaction ----------------------------------------------------------
    def _hit_test(self, x, y):
        # the viewport itself handles wheel; taps pass through to children
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        geometry = self._scrollbar_geometry()
        if geometry is not None and self._point_in(geometry[0], x, y):
            return self
        off_x = self._offset if self.horizontal else 0.0
        off_y = self._offset if not self.horizontal else 0.0
        for c in reversed(self.controls):
            hit = c._hit_test(x + off_x, y + off_y)
            if hit is not None:
                return hit
        return None

    def _hit_test_hover(self, x, y):
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        geometry = self._scrollbar_geometry()
        if geometry is not None and self._point_in(geometry[0], x, y):
            return self
        off_x = self._offset if self.horizontal else 0.0
        off_y = self._offset if not self.horizontal else 0.0
        for c in reversed(self.controls):
            hit = c._hit_test_hover(x + off_x, y + off_y)
            if hit is not None:
                return hit
        return None

    def _set_hover(self, on: bool):
        self._scrollbar_hovered = on
        if on:
            self._show_scrollbar(active=True)
        else:
            self._animate_internal(
                "_scrollbar_thickness", _SCROLLBAR_THICKNESS,
                motion.SHORT2, motion.STANDARD)
            if self._scrollbar_dragging:
                self._show_scrollbar(active=True)
            else:
                self._animate_internal(
                    "_scrollbar_opacity", _SCROLLBAR_IDLE_OPACITY,
                    motion.SHORT2, motion.STANDARD)
                self._schedule_scrollbar_hide()
        self.update()

    def _find_scrollable(self, x, y):
        if not self.visible or not self._contains(x, y):
            return None
        off_x = self._offset if self.horizontal else 0.0
        off_y = self._offset if not self.horizontal else 0.0
        for c in reversed(self.controls):
            found = c._find_scrollable(x + off_x, y + off_y)
            if found is not None:
                return found
        return self

    def _wheel(self, delta):
        self._scroll_by(delta)

    def _drag_start(self, x, y):
        geometry = self._scrollbar_geometry()
        if geometry is None or not self._point_in(geometry[0], x, y):
            return
        _track, thumb, _travel = geometry
        coordinate = x if self.horizontal else y
        thumb_start = thumb[0] if self.horizontal else thumb[1]
        thumb_size = thumb[2] if self.horizontal else thumb[3]
        if self._point_in(thumb, x, y):
            self._scrollbar_drag_delta = coordinate - thumb_start
        else:
            self._scrollbar_drag_delta = thumb_size / 2
            self._scrollbar_offset_from_pointer(coordinate)
        self._scrollbar_dragging = True
        self._show_scrollbar(active=True)

    def _drag(self, x, y):
        if self._scrollbar_dragging:
            self._scrollbar_offset_from_pointer(x if self.horizontal else y)

    def _drag_end(self):
        self._scrollbar_dragging = False
        if self._scrollbar_hovered:
            self._show_scrollbar(active=True)
        else:
            self._animate_internal(
                "_scrollbar_thickness", _SCROLLBAR_THICKNESS,
                motion.SHORT2, motion.STANDARD)
            self._animate_internal(
                "_scrollbar_opacity", _SCROLLBAR_IDLE_OPACITY,
                motion.SHORT2, motion.STANDARD)
            self._schedule_scrollbar_hide()

    def _tick_animations(self, now: float) -> bool:
        waiting = self._scrollbar_hide_at is not None
        if waiting and now >= self._scrollbar_hide_at:
            self._scrollbar_hide_at = None
            waiting = False
            if not self._scrollbar_hovered and not self._scrollbar_dragging:
                self._animate_internal(
                    "_scrollbar_opacity", 0.0,
                    motion.MEDIUM1, motion.STANDARD, now=now)
        return super()._tick_animations(now) or waiting


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
