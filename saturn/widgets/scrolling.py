"""Scrolling: ListView (vertical/horizontal, wheel + drag) and GestureDetector.

ListView(controls, horizontal, spacing, padding, on_scroll,
auto_scroll, scroll_to()); GestureDetector(content, on_tap, on_hover...).
"""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Unpack

import time
import math
from types import SimpleNamespace
from bisect import bisect_left, bisect_right
from collections import OrderedDict

from .. import colors
from .. import motion
from ..control import Control, ControlOptions
from ..event import TapEvent, fire, ControlEvent, normalize_handlers, _invoke
from ..types import as_padding
from .containers import Container, _margins
from ._compat import value, reject_options


_SCROLLBAR_THICKNESS = 8.0
_SCROLLBAR_HOVER_THICKNESS = 10.0
_SCROLLBAR_HIT_SIZE = 16.0
_SCROLLBAR_MARGIN = 2.0
_MIN_THUMB_SIZE = 32.0
_SCROLLBAR_FADE_DELAY = 0.6
_SCROLLBAR_IDLE_OPACITY = 0.48
_SCROLLBAR_ACTIVE_OPACITY = 0.64
_OVERSCAN = 96.0  # logical pixels for shadows and nearby incoming rows


def _elevation_outset(state):
    overrides = state.get("_animation_overrides", {})
    elevation = max(float(state.get("_elevation_progress") or 0),
                    float(overrides.get("_elevation_progress") or 0))
    if elevation <= 0:
        return 0.0
    # Native shadow envelope plus the rounding allowance for the reduced
    # software blur intermediate (as small as half a logical pixel scale).
    return math.ceil(3 * max(1 + elevation * .7, .5 + elevation * .8)
                     + elevation * .5) + 4


def _has_paint_overflow(control, width, height):
    """Cheap declaration scan; ordinary row trees need no bounds math."""
    state = object.__getattribute__(control, "__dict__")
    overrides = state.get("_animation_overrides", {})
    if (state.get("shadow") or state.get("offset") is not None or
            overrides.get("shadow") or overrides.get("offset") is not None):
        return True
    if any(state.get(name) is not None or overrides.get(name) is not None for name in ("rotate","scale")):
        return True
    if "_elevation_progress" in state and _elevation_outset(state) > _OVERSCAN:
        return True
    if isinstance(control, Container) and control._clip_children:
        return False
    children = state.get("controls")
    if children is None:
        content = state.get("content")
        children = (content,) if isinstance(content, Control) else ()
    for child in children:
        if not isinstance(child, Control):
            continue
        child_state = object.__getattribute__(child, "__dict__")
        if not child_state.get("visible", True):
            continue
        if (child_state.get("left") or child_state.get("top") or
                child_state.get("_width") is not None or
                child_state.get("_height") is not None or
                _has_paint_overflow(child, width, height)):
            return True
    return False


def _paint_outsets(control, width, height):
    """Conservative overflow for declared shadows, offsets and Stack boxes.

    Descendants outside a rounded Container are clipped. Other descendants
    may paint outside the row; their overflow contributes to the row guard.
    Read both the current animated value and its target so an animation
    cannot disappear halfway through a paint-only frame.
    """
    state = object.__getattribute__(control, "__dict__")
    overrides = state.get("_animation_overrides", {})
    elevation = _elevation_outset(state) if "_elevation_progress" in state else 0.0
    left = top = right = bottom = elevation
    for shadow in (state.get("shadow"), overrides.get("shadow")):
        for sh in shadow if isinstance(shadow, list) else ([shadow] if shadow else []):
            grow = max(0.0, float(sh.blur_radius)) + float(sh.spread_radius or 0.0)
            left = max(left, grow - sh.offset.x)
            top = max(top, grow - sh.offset.y)
            right = max(right, grow + sh.offset.x)
            bottom = max(bottom, grow + sh.offset.y)
    # Container clips descendants after drawing its own shadow/background.
    clipped = isinstance(control, Container) and control._clip_children
    if not clipped:
        children = state.get("controls")
        if children is None:
            content = state.get("content")
            children = [content] if content is not None else ()
        for child in children:
            if not isinstance(child, Control):
                continue
            child_state = object.__getattribute__(child, "__dict__")
            if not child_state.get("visible", True):
                continue
            cw = max(width, float(child_state.get("_width") or 0.0))
            ch = max(height, float(child_state.get("_height") or 0.0))
            cl, ct, cr, cb = _paint_outsets(child, cw, ch)
            # Absolute Stack positions and oversized descendants can escape
            # even without an offset or shadow on the top-level row.
            cx = float(child_state.get("left") or 0.0)
            cy = float(child_state.get("top") or 0.0)
            left = max(left, cl - cx)
            top = max(top, ct - cy)
            right = max(right, cr + cx + cw - width)
            bottom = max(bottom, cb + cy + ch - height)
    transformed = control._transform_outsets(width,height,bounds=(-left,-top,width+right,height+bottom))
    return tuple(max(a,b) for a,b in zip((left,top,right,bottom),transformed))


class ListView(Control):
    def __init__(self, *items, controls=None, horizontal: bool = False,
                 spacing: float = 0, item_extent: float | None = None,
                 padding=None, auto_scroll: bool = False, on_scroll=None,
                 reverse=False, first_item_prototype=False, prototype_item=None,
                 divider_thickness=0, clip_behavior="hardEdge", semantic_child_count=None,
                 cache_extent=None, build_controls_on_demand=True, scroll=None,
                 auto_scroll_animation=None, scroll_interval=10, **base: Unpack[ControlOptions]):
        reject_options("ListView", auto_scroll_animation=auto_scroll_animation)
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
        if item_extent is not None and item_extent <= 0:
            raise ValueError("item_extent must be positive")
        self.item_extent = item_extent
        self.padding = padding  # resolved lazily via as_padding
        self.auto_scroll = auto_scroll
        self.on_scroll = on_scroll
        self.reverse = reverse
        self.first_item_prototype = first_item_prototype
        self.prototype_item = prototype_item
        self.divider_thickness = divider_thickness
        self.clip_behavior = clip_behavior
        self.semantic_child_count = semantic_child_count
        self.cache_extent = cache_extent
        self.build_controls_on_demand = build_controls_on_demand
        self.scroll = scroll
        self.scroll_interval = scroll_interval
        self._last_scroll_event = 0.0
        self._last_reverse = reverse
        self._last_divider_thickness = divider_thickness
        self._reverse_slack = 0
        self._offset = 0.0
        self._content_size = 0.0
        self._placed_controls = []
        self._item_starts = []
        self._item_ends = []
        self._ordered_items = True
        self._lazy_items = set()
        self._lazy_layout_version = {}
        self._layout_version = 0
        self._fixed_axis_layout = False
        self._layout_controls = ()
        self._layout_scale = None
        self._layout_padding = None
        self._layout_spacing = None
        self._layout_item_extent = None
        self._intrinsic_cache = OrderedDict()
        self._geometry_cache = OrderedDict()
        self._paint_outsets = {}
        self._overflow_controls = []
        self._paint_guard_before = self._paint_guard_after = 0.0
        self._scrollbar_dragging = False
        self._scrollbar_drag_delta = 0.0
        self._scrollbar_hovered = False
        self._scrollbar_thickness = _SCROLLBAR_THICKNESS
        self._scrollbar_opacity = 0.0
        self._scrollbar_hide_at = None

    def _children(self):
        return self.controls

    def _pad(self):
        from ..types import as_padding
        return as_padding(self.padding)

    # -- layout --------------------------------------------------------------
    def _intrinsic(self, max_w, max_h, scale):
        # fills the box the parent gives it (ListView expands)
        return (self._width if self._width is not None else (max_w or 0),
                self._height if self._height is not None else (max_h or 0))

    def _place(self, x, y, w, h, scale):
        distance = self._max_offset()-self._offset
        pad = self._pad()
        new_view = w-pad.left-pad.right if self.horizontal else h-pad.top-pad.bottom
        if self._reverse_slack or self.reverse and self._content_size < new_view:
            self._layout_controls = ()
        if self.reverse != self._last_reverse:
            self._layout_controls = ()
            self._last_reverse = self.reverse
        if self.divider_thickness != self._last_divider_thickness:
            self._layout_controls = ()
            self._last_divider_thickness = self.divider_thickness
        original_extent = self.item_extent
        prototype = self.prototype_item or (next((c for c in self.controls if c.visible),None)
                                           if self.first_item_prototype else None)
        if prototype is not None and self.item_extent is None:
            extent = prototype._intrinsic(w,h,scale)[0 if self.horizontal else 1]
            if extent <= 0:
                raise ValueError("prototype item must have positive extent")
            self.item_extent = extent
        try:
            self._place_contents(x,y,w,h,scale)
        finally:
            self.item_extent = original_extent
        if self.reverse:
            self._offset = 0 if self.auto_scroll else max(0,self._max_offset()-distance)
            self._reverse_slack = max(0,new_view-self._content_size)
            if self._reverse_slack:
                axis = 0 if self.horizontal else 1
                for child in self._placed_controls:
                    rect = list(child._rect)
                    rect[axis] += self._reverse_slack
                    child._rect = tuple(rect)
                self._item_starts = [item+self._reverse_slack for item in self._item_starts]
                self._item_ends = [item+self._reverse_slack for item in self._item_ends]
                self._lazy_layout_version.clear()
            self._layout_lazy_candidates(scale)
        else:
            self._reverse_slack = 0
        if value(self.scroll) == "always":
            self._scrollbar_opacity = _SCROLLBAR_IDLE_OPACITY

    def _place_contents(self, x, y, w, h, scale):
        self._layout_version += 1
        p = self._pad()
        controls = tuple(reversed(self.controls)) if self.reverse else tuple(self.controls)
        layout_dirty = (self.page is None or
                        getattr(self.page, "_layout_dirty", True))
        rescan_outsets = layout_dirty or self._layout_controls != controls
        # A paint-only resize may change the viewport without changing row
        # content. Content updates mark the page layout dirty and invalidate
        # these variable-height measurements.
        if layout_dirty or self._layout_controls != controls:
            self._intrinsic_cache.clear()
            self._geometry_cache.clear()
        # A window resize changes the viewport width and height, but fixed
        # height rows keep their axis positions. Reuse those positions and
        # place only the rows near the new viewport.
        if (self._fixed_axis_layout and not self.horizontal and
                self.page is not None and
                not getattr(self.page, "_layout_dirty", True) and
                self._rect[:2] == (x, y) and
                self._layout_controls == controls and
                self._layout_scale == scale and
                self._layout_padding == p and
                self._layout_spacing == self.spacing and
                self._layout_item_extent == self.item_extent):
            self._rect = (x, y, w, h)
            view = h - p.top - p.bottom
            self._offset = max(0.0, min(self._offset,
                                       max(0.0, self._content_size - view)))
            if self.auto_scroll:
                self._offset = max(0.0, self._content_size - view)
            self._lazy_layout_version.clear()
            if self._overflow_controls:
                self._refresh_paint_outsets()
            self._layout_lazy_candidates(scale)
            return
        # A drag often revisits the last few widths. For variable-height
        # rows, their exact offsets were already measured at those widths.
        # Restore the geometry and place only visible rows again.
        geometry_key = (x, y, w, scale, p.left, p.top, p.right, p.bottom,
                        self.spacing, self.item_extent)
        cached_geometry = (None if layout_dirty or self.horizontal else
                           self._geometry_cache.get(geometry_key))
        if cached_geometry is not None:
            placed, starts, ends, ordered, total, rects = cached_geometry
            self._geometry_cache.move_to_end(geometry_key)
            self._rect = (x, y, w, h)
            for child, rect in zip(placed, rects):
                child._rect = rect
            self._placed_controls = placed
            self._item_starts = starts
            self._item_ends = ends
            self._ordered_items = ordered
            self._lazy_items = set(placed)
            self._lazy_layout_version.clear()
            self._fixed_axis_layout = False
            self._layout_controls = controls
            self._layout_scale = scale
            self._layout_padding = p
            self._layout_spacing = self.spacing
            self._layout_item_extent = self.item_extent
            self._content_size = total
            view = h - p.top - p.bottom
            self._offset = max(0.0, min(self._offset,
                                       max(0.0, total - view)))
            if self.auto_scroll:
                self._offset = max(0.0, total - view)
            if self._overflow_controls:
                self._refresh_paint_outsets()
            self._layout_lazy_candidates(scale)
            return
        self._rect = (x, y, w, h)
        ix, iy = x + p.left, y + p.top
        iw, ih = w - p.left - p.right, h - p.top - p.bottom
        total = 0.0
        placed, starts, ends, lazy = [], [], [], set()
        fixed_axis_layout = not self.horizontal
        horizontal = self.horizontal
        item_extent = self.item_extent
        spacing = self.spacing + max(0,self.divider_thickness)
        intrinsic_cache = self._intrinsic_cache
        cache_limit = max(512, len(controls) * 4)
        for k in controls:
            # Control attribute reads check animation overrides. A large list
            # needs only these few animated layout fields per row; reading
            # them together avoids that check for every intermediate value.
            raw = k.__dict__
            overrides = k._animation_overrides
            if not overrides.get("visible", raw["visible"]):
                continue
            margin = overrides.get("margin", raw["margin"])
            if margin is None:
                ml = mt = mr = mb = 0.0
            else:
                m = as_padding(margin)
                ml, mt, mr, mb = m.left, m.top, m.right, m.bottom
            row_width = overrides.get("_width", raw["_width"])
            row_height = overrides.get("_height", raw["_height"])
            # Fixed-height vertical rows know their footprint without
            # measuring all descendants. Their content is placed on demand.
            fixed_row = (not horizontal and
                         (item_extent is not None or row_height is not None))
            if not fixed_row:
                fixed_axis_layout = False
            if fixed_row:
                kw, kh = iw - ml - mr, (item_extent if
                                       item_extent is not None else row_height)
            elif horizontal and item_extent is not None:
                kw, kh = item_extent, ih - mt - mb
            else:
                measure_width = iw - ml - mr
                measure_key = (k, measure_width, scale)
                cached = intrinsic_cache.get(measure_key)
                if cached is not None:
                    intrinsic_cache.move_to_end(measure_key)
                    kw, kh = cached
                else:
                    # Containers whose natural content fits the available
                    # width cannot acquire extra wrapped lines when the
                    # window grows or shrinks within that range. Their
                    # unbounded measurement serves all such widths. Only
                    # use the built-in Container implementation here so
                    # custom row measurements retain their exact contract.
                    natural = None
                    if not horizontal and \
                            type(k)._intrinsic is Container._intrinsic:
                        natural_key = (k, None, scale)
                        natural = intrinsic_cache.get(natural_key)
                        if natural is None:
                            natural = k._intrinsic(None, None, scale)
                            intrinsic_cache[natural_key] = natural
                        else:
                            intrinsic_cache.move_to_end(natural_key)
                    if (natural is not None and 0 < natural[0] <= measure_width):
                        kw, kh = natural
                    else:
                        kw, kh = k._intrinsic(measure_width, None, scale)
                        intrinsic_cache[measure_key] = (kw, kh)
                    if len(intrinsic_cache) > cache_limit:
                        intrinsic_cache.popitem(last=False)
            if row_width is not None:
                kw = row_width
            if row_height is not None:
                kh = row_height
            if item_extent is not None:
                if horizontal:
                    kw = item_extent
                else:
                    kh = item_extent
            if horizontal:
                k._place(ix + total + ml, iy + mt, kw, ih - mt - mb, scale)
                child_rect = k._rect
                total += kw + ml + mr + spacing
            else:
                child_rect = (ix + ml, iy + total + mt,
                              iw - ml - mr, kh)
                k._rect = child_rect
                lazy.add(k)
                total += kh + mt + mb + spacing
            start = child_rect[0 if horizontal else 1]
            extent = child_rect[2 if horizontal else 3]
            placed.append(k)
            starts.append(start)
            ends.append(start + extent)
        self._placed_controls = placed
        self._lazy_items = lazy
        self._lazy_layout_version = {}
        self._fixed_axis_layout = fixed_axis_layout
        self._layout_controls = controls
        self._layout_scale = scale
        self._layout_padding = p
        self._layout_spacing = self.spacing
        self._layout_item_extent = self.item_extent
        self._item_starts = starts
        self._item_ends = ends
        self._ordered_items = all(
            starts[i] >= starts[i - 1] and ends[i] >= ends[i - 1]
            for i in range(1, len(starts)))
        self._content_size = max(0.0, total - spacing)
        self._refresh_paint_outsets(rescan=rescan_outsets)
        if not self.horizontal and not fixed_axis_layout:
            self._geometry_cache[geometry_key] = (
                placed, starts, ends, self._ordered_items,
                self._content_size, [child._rect for child in placed])
            self._geometry_cache.move_to_end(geometry_key)
            while len(self._geometry_cache) > 3:
                self._geometry_cache.popitem(last=False)
        view = ih if not self.horizontal else iw
        # clamp offset after content shrinks
        self._offset = max(0.0, min(self._offset,
                                    max(0.0, self._content_size - view)))
        if self.auto_scroll:
            self._offset = max(0.0, self._content_size - view)
        self._layout_lazy_candidates(scale)

    def _max_offset(self) -> float:
        p = self._pad()
        view = (self._rect[3] - p.top - p.bottom) if not self.horizontal \
            else (self._rect[2] - p.left - p.right)
        return max(0.0, self._content_size - view)

    def _scroll_by(self, delta):
        if value(self.scroll) == "none":
            return
        new = max(0.0, min(self._max_offset(), self._offset + delta))
        if new != self._offset:
            self._offset = new
            self._show_scrollbar()
            if self.page is not None:
                self.page.repaint()
            self._emit_scroll()

    def _emit_scroll(self):
        now = time.perf_counter()
        if now-self._last_scroll_event >= max(0,self.scroll_interval)/1000:
            self._last_scroll_event = now
            fire(self,"scroll",self._max_offset()-self._offset if self.reverse else self._offset)

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
                self.page._active_animations.add(self)
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
            if self.page is not None:
                self.page.repaint()
            self._emit_scroll()

    def scroll_to(self, offset: float = 0, delta: float | None = None,
                  scroll_key=None, duration=None, curve=None):
        reject_options("ListView.scroll_to",duration=duration,curve=curve)
        if scroll_key is not None:
            child = next((c for c in self.controls if c.key == scroll_key),None)
            if child is None:
                raise KeyError(scroll_key)
            axis = 0 if self.horizontal else 1
            offset = child._rect[axis]-self._rect[axis]
            if self.reverse:
                offset = self._max_offset()-offset
        if offset == -1:
            offset = self._max_offset()
        physical = self._max_offset()-offset if self.reverse else offset
        self._scroll_by((-delta if self.reverse else delta) if delta is not None
                        else physical-self._offset)

    def _candidates(self, low, high):
        if not self._ordered_items:
            return self._placed_controls
        # A row below the viewport can cast a shadow upward, and a row
        # above it can cast one downward. Keep the bisect path while using
        # bounds derived from actual declared effects, not a fixed limit.
        low -= self._paint_guard_after
        high += self._paint_guard_before
        first = bisect_left(self._item_ends, low)
        last = bisect_right(self._item_starts, high)
        return self._placed_controls[first:last]

    def _refresh_paint_outsets(self, *, rescan=False):
        outsets = {}
        before = after = 0.0
        axis = 0 if self.horizontal else 1
        if rescan:
            self._overflow_controls = [
                child for child in self._placed_controls
                if _has_paint_overflow(child, child._rect[2], child._rect[3])]
        for child in self._overflow_controls:
            width, height = child._rect[2], child._rect[3]
            overflow = _paint_outsets(child, width, height)
            if any(overflow):
                outsets[child] = overflow
                before = max(before, overflow[axis])
                after = max(after, overflow[axis + 2])
        self._paint_outsets = outsets
        self._paint_guard_before, self._paint_guard_after = before, after

    def _layout_lazy_candidates(self, scale):
        x, y, w, h = self._rect
        p = self._pad()
        guard = self._guard
        start = (x if self.horizontal else y) + self._offset
        size = w if self.horizontal else h
        candidates = (self._candidates(start-guard,start+size+guard) if
                      self.build_controls_on_demand and value(self.clip_behavior) != "none"
                      else self._placed_controls)
        for child in candidates:
            if (child in self._lazy_items and
                    self._lazy_layout_version.get(child) != self._layout_version):
                ml, _mt, mr, _mb = _margins(child)
                child._rect = (x + p.left + ml, child._rect[1],
                               w - p.left - p.right - ml - mr,
                               child._rect[3])
                child._place(*child._rect, scale)
                self._lazy_layout_version[child] = self._layout_version

    def _draw_all(self, r, ox: float = 0.0, oy: float = 0.0):
        if not self.visible:
            return
        self._layout_lazy_candidates(r.scale)
        self._effects_begin(r, ox, oy)
        try:
            x, y, w, h = self._rect
            clipped = value(self.clip_behavior) != "none"
            if clipped:
                r.clip_push(x + ox, y + oy, w, h)
            off_x = self._offset if self.horizontal else 0.0
            off_y = self._offset if not self.horizontal else 0.0
            # Clipping alone still runs every child renderer. The generous
            # guard keeps ordinary shadows and small paint overflow intact.
            guard = self._guard
            left, top = x + off_x - guard, y + off_y - guard
            right, bottom = x + off_x + w + guard, y + off_y + h + guard
            axis_start = (x if self.horizontal else y) + self._offset
            axis_size = w if self.horizontal else h
            candidates = self._candidates(axis_start-guard,axis_start+axis_size+guard) if self.build_controls_on_demand and clipped else self._placed_controls
            for c in candidates:
                if c.visible:
                    cx, cy, cw, ch = c._rect
                    pl, pt, pr, pb = self._paint_outsets.get(c, (0, 0, 0, 0))
                    if (cw > 0 and ch > 0 and
                            (cx + cw + pr < left or cx - pl > right or
                             cy + ch + pb < top or cy - pt > bottom)):
                        continue
                    c._draw_all(r, ox - off_x, oy - off_y)
                    if self.divider_thickness > 0 and c is not self._placed_controls[-1]:
                        t = self.divider_thickness
                        if self.horizontal:
                            r.fill_rect(cx+cw+ox-off_x,cy+oy-off_y,t,ch,colors.parse_color(colors.Colors.OUTLINE_VARIANT))
                        else:
                            r.fill_rect(cx+ox-off_x,cy+ch+oy-off_y,cw,t,colors.parse_color(colors.Colors.OUTLINE_VARIANT))
            if clipped:
                r.clip_pop()
            self._draw_scrollbar(r, ox, oy)
        finally:
            self._effects_end(r)

    def _draw_scrollbar(self, r, ox, oy):
        if value(self.scroll) in ("hidden","none"):
            return
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
        x,y = self._hit_point(x,y)
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        if self.page is not None and self.page._app.renderer is not None:
            self._layout_lazy_candidates(self.page._app.renderer.scale)
        geometry = self._scrollbar_geometry()
        if geometry is not None and self._point_in(geometry[0], x, y):
            return self
        off_x = self._offset if self.horizontal else 0.0
        off_y = self._offset if not self.horizontal else 0.0
        guard = _OVERSCAN
        axis = (x + off_x) if self.horizontal else (y + off_y)
        for c in reversed(self._candidates(axis - guard, axis + guard)):
            hit = c._hit_test(x + off_x, y + off_y)
            if hit is not None:
                return hit
        return None

    def _hit_test_hover(self, x, y):
        x,y = self._hit_point(x,y)
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        if self.page is not None and self.page._app.renderer is not None:
            self._layout_lazy_candidates(self.page._app.renderer.scale)
        geometry = self._scrollbar_geometry()
        if geometry is not None and self._point_in(geometry[0], x, y):
            return self
        off_x = self._offset if self.horizontal else 0.0
        off_y = self._offset if not self.horizontal else 0.0
        guard = _OVERSCAN
        axis = (x + off_x) if self.horizontal else (y + off_y)
        for c in reversed(self._candidates(axis - guard, axis + guard)):
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
        if self.page is not None:
            self.page.repaint()

    def _find_scrollable(self, x, y):
        x,y = self._hit_point(x,y)
        if not self.visible or not self._contains(x, y):
            return None
        if self.page is not None and self.page._app.renderer is not None:
            self._layout_lazy_candidates(self.page._app.renderer.scale)
        off_x = self._offset if self.horizontal else 0.0
        off_y = self._offset if not self.horizontal else 0.0
        guard = _OVERSCAN
        axis = (x + off_x) if self.horizontal else (y + off_y)
        for c in reversed(self._candidates(axis - guard, axis + guard)):
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
            if not self._scrollbar_hovered and not self._scrollbar_dragging and value(self.scroll) != "always":
                self._animate_internal(
                    "_scrollbar_opacity", 0.0,
                    motion.MEDIUM1, motion.STANDARD, now=now)
        return super()._tick_animations(now) or waiting

    @property
    def _guard(self):
        return _OVERSCAN if self.cache_extent is None else max(0,float(self.cache_extent))

    __unsupported_parameters__ = {"auto_scroll_animation"}


class GestureDetector(Control):
    def __init__(self, content=None, *, on_tap=None, on_tap_down=None,
                 on_long_press=None, on_hover=None, on_enter=None, on_exit=None,
                 mouse_cursor=None, drag_interval=0, hover_interval=0,
                 on_tap_up=None, on_tap_move=None, on_tap_cancel=None,
                 on_double_tap=None, on_double_tap_down=None, on_double_tap_cancel=None,
                 on_horizontal_drag_down=None, on_horizontal_drag_start=None,
                 on_horizontal_drag_update=None, on_horizontal_drag_end=None, on_horizontal_drag_cancel=None,
                 on_vertical_drag_down=None, on_vertical_drag_start=None,
                 on_vertical_drag_update=None, on_vertical_drag_end=None,on_vertical_drag_cancel=None,
                 on_pan_down=None,on_pan_start=None,on_pan_update=None,on_pan_end=None,on_pan_cancel=None,
                 on_scroll=None,allowed_devices=None,exclude_from_semantics=False,
                 multi_tap_touches=0,trackpad_scroll_causes_scale=False, **base: Unpack[ControlOptions]):
        if multi_tap_touches:
            raise NotImplementedError("GestureDetector.multi_tap_touches requires multitouch input")
        if trackpad_scroll_causes_scale:
            raise NotImplementedError("GestureDetector.trackpad_scroll_causes_scale requires pinch input")
        super().__init__(**base)
        self.content = content
        self.on_tap = on_tap
        self.on_tap_down = on_tap_down
        self.on_long_press = on_long_press
        self.on_hover = on_hover
        self.on_enter = on_enter
        self.on_exit = on_exit
        callbacks = locals()
        for name in ("tap_up","tap_move","tap_cancel","double_tap","double_tap_down","double_tap_cancel",
                     "horizontal_drag_down","horizontal_drag_start","horizontal_drag_update","horizontal_drag_end","horizontal_drag_cancel",
                     "vertical_drag_down","vertical_drag_start","vertical_drag_update","vertical_drag_end","vertical_drag_cancel",
                     "pan_down","pan_start","pan_update","pan_end","pan_cancel","scroll"):
            setattr(self,"on_"+name,callbacks["on_"+name])
        self.mouse_cursor = mouse_cursor
        self.drag_interval,self.hover_interval = drag_interval,hover_interval
        self.allowed_devices = allowed_devices
        self.exclude_from_semantics = exclude_from_semantics
        self._drag_origin = self._drag_position = None
        self._drag_started = False
        self._drag_last_time = self._hover_last_time = 0
        self._drag_axis = None
        self._drag_velocity = (0,0)
        self._last_pointer = (0,0)
        self._consume_click = False
        self._long_press_at = None
        self._long_press_fired = False
        self.on_click = self._clicked  # internal routing
        self._hovered = False
        self._pressed = False

    def _children(self):
        return [self.content] if self.content is not None else []

    def _intrinsic(self, max_w, max_h, scale):
        if self.content is None:
            return (self._width or max_w or 0,self._height or max_h or 0)
        w, h = self.content._intrinsic(max_w, max_h, scale)
        return (self._width or w, self._height or h)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        if self.content is not None:
            self.content._place(x, y, w, h, scale)

    def _draw(self, r, x, y):
        pass

    def _hit_test(self, x, y):
        x,y = self._hit_point(x,y)
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        if self.allowed_devices is not None and not any(value(device) == "mouse" for device in self.allowed_devices):
            return None
        if self._has_drag_handlers or any(getattr(self,"on_"+name,None) for name in ("tap","tap_down","tap_up","double_tap","long_press")):
            return self
        if self.content is not None:
            hit = self.content._hit_test(x, y)
            if hit is not None:
                return hit
        return self

    def _hit_test_hover(self, x, y):
        x,y = self._hit_point(x,y)
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        return self

    # pointer hooks ------------------------------------------------------------
    def _pressed_hook(self, x, y):
        self._last_pointer = (x,y)
        self._long_press_at = time.perf_counter()+.5 if self.on_long_press else None
        self._long_press_fired = False
        self._pointer_event("tap_down",x,y)
        if getattr(self.page,"_click_count",1) == 2:
            self._pointer_event("double_tap_down",x,y)

    def _clicked(self):
        x,y = self._last_pointer
        self._pointer_event("double_tap" if getattr(self.page,"_click_count",1) == 2 and self.on_double_tap else "tap",x,y)

    def _released_hook(self,x,y):
        self._long_press_at = None
        self._last_pointer = x,y
        if not self._consume_click:
            self._pointer_event("tap_up" if self._contains(x,y) else "tap_cancel",x,y)
            if not self._contains(x,y) and getattr(self.page,"_click_count",1) == 2:
                self._pointer_event("double_tap_cancel",x,y)

    @property
    def _has_drag_handlers(self):
        return any(getattr(self,"on_"+prefix+suffix,None) for prefix in
                   ("pan_","horizontal_drag_","vertical_drag_") for suffix in ("down","start","update","end"))

    def _pointer_event(self,name,x,y,**fields):
        if self.page is None:
            return
        handlers = normalize_handlers(getattr(self,"on_"+name,None))
        if not handlers:
            return
        ev = ControlEvent(name,self)
        ev.kind = "mouse"
        ev.local_position = SimpleNamespace(x=x-self._rect[0],y=y-self._rect[1])
        gx,gy = getattr(self.page,"_pointer_pos",None) or self._screen_point(x,y)
        ev.global_position = SimpleNamespace(x=gx,y=gy)
        for field,item in fields.items():
            setattr(ev,field,item)
        for handler in handlers:
            self.page._app.call(_invoke,handler,ev)

    def _drag_start(self,x,y):
        self._drag_origin = self._drag_position = (x,y)
        self._drag_last_time = time.perf_counter()
        self._drag_started = False
        self._consume_click = False
        for prefix in ("pan","horizontal_drag","vertical_drag"):
            self._pointer_event(prefix+"_down",x,y)

    def _drag(self,x,y):
        if self._drag_origin is None:
            return
        self._last_pointer = x,y
        now = time.perf_counter()
        dx,dy = x-self._drag_position[0],y-self._drag_position[1]
        self._pointer_event("tap_move",x,y,delta_x=dx,delta_y=dy)
        ox,oy = self._drag_origin
        if not self._drag_started:
            if math.hypot(x-ox,y-oy) < 4 or not self._has_drag_handlers:
                return
            self._drag_started = True
            self._long_press_at = None
            self._consume_click = True
            self._drag_axis = "horizontal_drag" if abs(x-ox) >= abs(y-oy) else "vertical_drag"
            self._pointer_event("tap_cancel",x,y)
            self._pointer_event("pan_start",x,y)
            self._pointer_event(self._drag_axis+"_start",x,y)
        if now-self._drag_last_time < max(0,self.drag_interval)/1000:
            return
        dt = max(.001,now-self._drag_last_time)
        self._drag_velocity = dx/dt,dy/dt
        self._pointer_event("pan_update",x,y,delta_x=dx,delta_y=dy,primary_delta=None)
        self._pointer_event(self._drag_axis+"_update",x,y,delta_x=dx if self._drag_axis == "horizontal_drag" else 0,
                            delta_y=dy if self._drag_axis == "vertical_drag" else 0,
                            primary_delta=dx if self._drag_axis == "horizontal_drag" else dy)
        self._drag_position,self._drag_last_time = (x,y),now

    def _drag_end(self):
        if self._drag_started:
            x,y = self._last_pointer
            vx,vy = self._drag_velocity
            velocity = SimpleNamespace(x=vx,y=vy)
            self._pointer_event("pan_end",x,y,velocity=velocity,primary_velocity=None)
            self._pointer_event(self._drag_axis+"_end",x,y,velocity=velocity,
                                primary_velocity=vx if self._drag_axis == "horizontal_drag" else vy)
        self._drag_origin = None

    def _set_hover(self,on):
        self._hovered = on
        self._pointer_event("enter" if on else "exit",*self._last_pointer)

    def _hover_move(self,x,y):
        self._last_pointer = x,y
        now = time.perf_counter()
        if now-self._hover_last_time >= max(0,self.hover_interval)/1000:
            self._hover_last_time = now
            self._pointer_event("hover",x,y)

    def _find_scrollable(self,x,y):
        hx,hy = self._hit_point(x,y)
        if self.visible and not self.disabled and self.on_scroll and self._contains(hx,hy):
            return self
        return super()._find_scrollable(x,y)

    def _wheel(self,delta):
        self._pointer_event("scroll",*self._last_pointer,scroll_delta=SimpleNamespace(x=0,y=delta))

    def _cancel_pointer(self):
        x,y = self._last_pointer
        self._long_press_at = None
        self._pointer_event("tap_cancel",x,y)
        if self._drag_started:
            self._pointer_event("pan_cancel",x,y)
            self._pointer_event(self._drag_axis+"_cancel",x,y)
        self._drag_origin = None
        self._drag_started = False
        self._consume_click = True

    def _tick_animations(self,now):
        waiting = self._long_press_at is not None and self._pressed
        if waiting and now >= self._long_press_at:
            self._long_press_at = None
            self._long_press_fired = True
            self._consume_click = True
            self._pointer_event("long_press",*self._last_pointer)
            waiting = False
        return super()._tick_animations(now) or waiting

    __unsupported_parameters__ = {"multi_tap_touches", "trackpad_scroll_causes_scale"}
