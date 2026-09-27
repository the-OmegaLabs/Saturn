"""Control base classes: state every control shares + dirty plumbing."""
from __future__ import annotations

import copy
import functools
import math
import threading
import time
from dataclasses import dataclass

from . import colors
from .animation import animation_spec, ease, interpolate
from .types import Alignment, AnimationCurve, Margin, as_padding


@dataclass
class _Tween:
    start_value: object
    end_value: object
    started: float
    duration: float
    curve: object
    group: str


class Control:
    """Base control with layout, state, animation, and event properties."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        intrinsic = cls.__dict__.get("_intrinsic")
        if intrinsic:
            @functools.wraps(intrinsic)
            def measured(self, max_w, max_h, scale):
                width, height = intrinsic(self, max_w, max_h, scale)
                state = object.__getattribute__(self, "__dict__")
                if state.get("aspect_ratio"):
                    return self._aspect_size(width, height, max_w, max_h)
                return width, height
            cls._intrinsic = measured
        place = cls.__dict__.get("_place")
        if place:
            @functools.wraps(place)
            def placed(self, x, y, width, height, scale):
                state = object.__getattribute__(self, "__dict__")
                if state.get("aspect_ratio"):
                    width, height = self._aspect_size(width, height, width, height)
                result = place(self, x, y, width, height, scale)
                if state.get("on_size_change"):
                    self._notify_size_change()
                return result
            cls._place = placed

    def __init__(self, *, visible: bool = True, disabled: bool = False,
                 opacity: float = 1.0, expand: bool | int | None = None,
                 expand_loose: bool = False,
                 tooltip: str | None = None, data=None,
                 width: float | None = None, height: float | None = None,
                 margin=None, align: Alignment | None = None,
                 left: float | None = None, top: float | None = None,
                 right: float | None = None, bottom: float | None = None,
                 rotate=None, scale=None, offset=None,
                 animate_opacity=None, animate_size=None,
                 animate_position=None, animate_align=None,
                 animate_margin=None, animate_rotation=None,
                 animate_scale=None, animate_offset=None,
                 on_animation_end=None, key=None, ref=None, rtl=None,
                 aspect_ratio=None, mouse_cursor=None, semantics_label=None,
                 can_request_focus=True, on_size_change=None,
                 size_change_interval=10, **unsupported):
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise TypeError(f"{type(self).__name__} does not implement parameter(s): {names}")
        if aspect_ratio is not None and (not math.isfinite(float(aspect_ratio)) or aspect_ratio <= 0):
            raise ValueError("aspect_ratio must be positive and finite")
        object.__setattr__(self, "_animation_overrides", {})
        object.__setattr__(self, "_animation_targets", {})
        object.__setattr__(self, "_animations", {})
        object.__setattr__(self, "_animation_lock", threading.RLock())
        object.__setattr__(self, "_animation_seeded", False)
        self.visible = visible
        self.disabled = disabled
        self.opacity = opacity
        self.expand = expand
        if not isinstance(expand_loose,bool):
            raise TypeError("expand_loose must be a bool")
        self.expand_loose = expand_loose
        self.tooltip = tooltip
        self.data = data
        self.key = key
        self.ref = ref
        if ref is not None:
            ref.current = self
        self.rtl = None if rtl is None else bool(rtl)
        self.aspect_ratio = aspect_ratio
        self.mouse_cursor = mouse_cursor
        self.semantics_label = semantics_label
        self.can_request_focus = bool(can_request_focus)
        self.on_size_change = on_size_change
        self.size_change_interval = max(0, float(size_change_interval))
        self._last_notified_size = None
        self._last_size_event_time = 0.0
        self._size_event_timer = None
        self._width = width
        self._height = height
        self.margin = as_padding(margin) if margin is not None and not isinstance(margin, Margin) else margin
        self.align = align
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.rotate = rotate
        self.scale = scale
        self.offset = offset
        self.animate_opacity = animate_opacity
        self.animate_size = animate_size
        self.animate_position = animate_position
        self.animate_align = animate_align
        self.animate_margin = animate_margin
        self.animate_rotation = animate_rotation
        self.animate_scale = animate_scale
        self.animate_offset = animate_offset
        self.on_animation_end = on_animation_end
        self.parent: Control | None = None
        self.page = None           # set on attach
        self._rect = (0.0, 0.0, 0.0, 0.0)  # (x, y, w, h), assigned by layout

    def __getattribute__(self, name):
        if name not in {"_animation_overrides", "__dict__", "__class__"}:
            try:
                overrides = object.__getattribute__(self, "_animation_overrides")
                if name in overrides:
                    return overrides[name]
            except AttributeError:
                pass
        return object.__getattribute__(self, name)

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
            self.page._reconcile_branch(self)
            self._prepare_animation_tree(time.perf_counter())
            self.page._layout_dirty = True
            self.page._animation_scan_needed = True
            if hasattr(self.page, "repaint"):
                self.page.repaint()
            else:
                self.page.update()

    def repaint(self):
        if self.page is not None:
            if hasattr(self.page, "repaint"):
                self.page.repaint()
            else:
                self.page.update()

    def focus(self):
        """Focus this attached control when keyboard focus is enabled."""
        if self.page is not None and self.can_request_focus:
            self.page.focus(self)

    @property
    def _rtl(self):
        node = self
        while node is not None:
            state = object.__getattribute__(node, "__dict__")
            if state.get("rtl") is not None:
                return bool(state["rtl"])
            node = state.get("parent")
        return False

    def _aspect_size(self, width, height, max_w=None, max_h=None):
        ratio = float(self.aspect_ratio)
        if max_w is not None and math.isfinite(max_w):
            width = max(0, max_w)
        elif max_h is not None and math.isfinite(max_h):
            width = max(0, max_h) * ratio
        height = width / ratio
        if max_h is not None and math.isfinite(max_h) and height > max_h:
            height = max(0, max_h)
            width = height * ratio
        return width, height

    def _notify_size_change(self):
        size = self._rect[2:]
        now = time.perf_counter()
        if size == self._last_notified_size or self.page is None:
            return
        remaining = self.size_change_interval / 1000 - (now - self._last_size_event_time)
        if remaining > 0:
            if self._size_event_timer is None:
                def trailing():
                    self._size_event_timer = None
                    if self.page is not None:
                        self.page._app.post(self._notify_size_change)
                self._size_event_timer = threading.Timer(remaining, trailing)
                self._size_event_timer.daemon = True
                self._size_event_timer.start()
            return
        self._last_notified_size = size
        self._last_size_event_time = now
        from .event import LayoutSizeChangeEvent, dispatch_event
        dispatch_event(self, "size_change", LayoutSizeChangeEvent(
            "size_change", self, width=size[0], height=size[1]))

    def _attach(self, page, parent: "Control | None" = None):
        newly_attached = self.page is not page
        self.page = page
        self.parent = parent
        self._seed_animation_targets()
        for c in self._children():
            c._attach(page, self)
        self._attached_child_controls = tuple(self._children())
        if newly_attached and getattr(self, "autofocus", False) and self.can_request_focus:
            page._app.post(lambda: page.focus(self) if self.page is page else None)

    def _children(self) -> list:
        return getattr(self, "controls", [])

    # -- implicit animation ---------------------------------------------
    def _animation_groups(self):
        return {
            "opacity": ("animate_opacity", ("opacity",)),
            "size": ("animate_size", ("_width", "_height")),
            "position": ("animate_position", ("left", "top", "right", "bottom")),
            "align": ("animate_align", ("align",)),
            "margin": ("animate_margin", ("margin",)),
            "rotation": ("animate_rotation", ("rotate",)),
            "scale": ("animate_scale", ("scale",)),
            "offset": ("animate_offset", ("offset",)),
        }

    def _raw(self, name):
        return object.__getattribute__(self, "__dict__").get(name)

    def _seed_animation_targets(self):
        with self._animation_lock:
            targets = object.__getattribute__(self, "_animation_targets")
            for _group, (_config, names) in self._animation_groups().items():
                for name in names:
                    targets[name] = copy.deepcopy(self._raw(name))
            self._animation_seeded = True

    def _prepare_animations(self, now: float):
        with self._animation_lock:
            if not self._animation_seeded:
                self._seed_animation_targets()
                return
            targets = object.__getattribute__(self, "_animation_targets")
            animations = object.__getattribute__(self, "_animations")
            overrides = object.__getattribute__(self, "_animation_overrides")
            for group, (config_name, names) in self._animation_groups().items():
                config = self._raw(config_name)
                spec = animation_spec(config) if config else None
                for name in names:
                    target = copy.deepcopy(self._raw(name))
                    previous = targets.get(name, target)
                    if target == previous:
                        continue
                    current = self._sample(name, now)
                    targets[name] = copy.deepcopy(target)
                    if spec is None or spec[0] <= 0:
                        animations.pop(name, None)
                        overrides.pop(name, None)
                        continue
                    duration, curve = spec
                    overrides[name] = copy.deepcopy(current)
                    animations[name] = _Tween(current, target, now, duration, curve, group)

    def _sample(self, name: str, now: float):
        with self._animation_lock:
            tween = object.__getattribute__(self, "_animations").get(name)
            if tween is None:
                overrides = object.__getattribute__(self, "_animation_overrides")
                return copy.deepcopy(overrides.get(name, self._animation_targets.get(
                    name, self._raw(name))))
            p = (now - tween.started) / tween.duration
            return interpolate(tween.start_value, tween.end_value,
                               ease(tween.curve, p), name)

    def _tick_animations(self, now: float) -> bool:
        with self._animation_lock:
            animations = object.__getattribute__(self, "_animations")
            overrides = object.__getattribute__(self, "_animation_overrides")
            layout_changed = any(name in {
                "_width", "_height", "left", "top", "right", "bottom",
                "align", "margin", "padding", "alignment",
            } for name in animations)
            completed = set()
            for name, tween in list(animations.items()):
                p = (now - tween.started) / tween.duration
                if p >= 1:
                    animations.pop(name, None)
                    overrides.pop(name, None)
                    completed.add(tween.group)
                else:
                    overrides[name] = interpolate(
                        tween.start_value, tween.end_value,
                        ease(tween.curve, p), name)
            active_groups = {a.group for a in animations.values()}
            active = bool(animations)
        if layout_changed and self.page is not None:
            self.page._layout_dirty = True
        if completed and self.page is not None:
            from .event import fire
            for group in completed - active_groups:
                if group:
                    fire(self, "animation_end", group)
        return active

    def _animate_internal(self, name: str, target, duration_ms: float,
                          curve=AnimationCurve.FAST_OUT_SLOWIN,
                          now: float | None = None):
        """Start a built-in Material state transition on a private value."""
        now = time.perf_counter() if now is None else now
        with self._animation_lock:
            animations = object.__getattribute__(self, "_animations")
            overrides = object.__getattribute__(self, "_animation_overrides")
            current = self._sample(name, now) if name in animations else copy.deepcopy(
                overrides.get(name, self._raw(name)))
            object.__getattribute__(self, "__dict__")[name] = copy.deepcopy(target)
            self._animation_targets[name] = copy.deepcopy(target)
            duration = max(0.0, float(duration_ms) / 1000.0)
            if duration == 0 or current == target:
                animations.pop(name, None)
                overrides.pop(name, None)
                return
            overrides[name] = copy.deepcopy(current)
            animations[name] = _Tween(current, target, now, duration, curve, "")
        if self.page is not None:
            if hasattr(self.page, "_active_animations"):
                self.page._active_animations.add(self)
            self.page._app.mark_dirty()

    def _prepare_animation_tree(self, now: float):
        self._prepare_animations(now)
        for child in self._children():
            child._prepare_animation_tree(now)

    def _tick_animation_tree(self, now: float) -> bool:
        active = self._tick_animations(now)
        if active and self.page is not None and hasattr(self.page, "_active_animations"):
            self.page._active_animations.add(self)
        for child in self._children():
            active = child._tick_animation_tree(now) or active
        return active

    def _transform_matrix(self, ox=0.0, oy=0.0, *, hit=False, values=None, rect=None):
        """Local paint transform around the control's layout rectangle."""
        x, y, width, height = self._rect if rect is None else rect
        x, y = x + ox, y + oy
        values = values or {}
        rotate = values.get("rotate", self.rotate)
        scale = values.get("scale", self.scale)
        offset = values.get("offset", self.offset)
        angle = (float(rotate) if isinstance(rotate, (int, float)) else
                 float(getattr(rotate, "angle", 0)))
        sx = sy = 1.0
        if isinstance(scale, (int, float)):
            sx = sy = float(scale)
        elif scale is not None:
            uniform = getattr(scale, "scale", None)
            sx = getattr(scale, "scale_x", None)
            sy = getattr(scale, "scale_y", None)
            sx = float(sx if sx is not None else uniform if uniform is not None else 1)
            sy = float(sy if sy is not None else uniform if uniform is not None else 1)
        if hit and not getattr(rotate, "transform_hit_tests", True):
            angle = 0
        if hit and not getattr(scale, "transform_hit_tests", True):
            sx = sy = 1
        def pivot(value):
            alignment = getattr(value, "alignment", None) or Alignment.CENTER
            origin = getattr(value, "origin", None)
            return (x + width * (alignment.x + 1) / 2 + getattr(origin, "x", 0),
                    y + height * (alignment.y + 1) / 2 + getattr(origin, "y", 0))
        spx, spy = pivot(scale)
        rpx, rpy = pivot(rotate)
        cosine, sine = math.cos(angle), math.sin(angle)
        a, b, c, d = cosine * sx, sine * sx, -sine * sy, cosine * sy
        tx = cosine * (spx * (1 - sx) - rpx) - sine * (spy * (1 - sy) - rpy) + rpx
        ty = sine * (spx * (1 - sx) - rpx) + cosine * (spy * (1 - sy) - rpy) + rpy
        if offset is not None and (not hit or getattr(offset, "transform_hit_tests", True)):
            dx, dy = offset if isinstance(offset, tuple) else (offset.x, offset.y)
            tx += float(dx) * width
            ty += float(dy) * height
        matrix = (a, b, c, d, tx, ty)
        if not all(math.isfinite(value) for value in matrix):
            raise ValueError("Control transforms must be finite")
        return matrix

    def _hit_point(self, x, y):
        if self.rotate is None and self.scale is None and self.offset is None:
            return x, y
        a, b, c, d, tx, ty = self._transform_matrix(hit=True)
        determinant = a * d - b * c
        if abs(determinant) < 1e-12:
            return float("inf"), float("inf")
        x, y = x - tx, y - ty
        return (d * x - c * y) / determinant, (a * y - b * x) / determinant

    def _event_point(self, x, y):
        """Convert a window pointer into this control's layout coordinates."""
        chain, node = [], self
        while node is not None and node is not self.page:
            chain.append(node)
            node = node.parent
        for node in reversed(chain):
            x, y = node._hit_point(x, y)
            if node is not self and hasattr(node, "_scrollbar_geometry"):
                if node.horizontal:
                    x += node._offset
                else:
                    y += node._offset
        return x, y

    def _screen_point(self, x, y):
        """Map a layout point to the window, including ancestor scrolling."""
        node = self
        while node is not None and node is not self.page:
            a, b, c, d, tx, ty = node._transform_matrix()
            x, y = a*x+c*y+tx, b*x+d*y+ty
            node = node.parent
            if node is not None and hasattr(node, "_scrollbar_geometry"):
                if node.horizontal:
                    x -= node._offset
                else:
                    y -= node._offset
        return x, y

    def _transform_outsets(self, width, height, bounds=None):
        """Conservative paint overflow for current and animated targets."""
        rx, ry, _, _ = self._rect
        source = bounds if bounds is not None else (0.0, 0.0, width, height)
        bounds = [source[0], source[1], source[2], source[3]]
        for values in ({}, {name: self._raw(name) for name in ("rotate", "scale", "offset")}):
            a, b, c, d, tx, ty = self._transform_matrix(values=values, rect=(rx, ry, width, height))
            for x, y in ((rx+source[0], ry+source[1]), (rx+source[2], ry+source[1]),
                         (rx+source[0], ry+source[3]), (rx+source[2], ry+source[3])):
                px, py = a*x+c*y+tx-rx, b*x+d*y+ty-ry
                bounds[0] = min(bounds[0], px)
                bounds[1] = min(bounds[1], py)
                bounds[2] = max(bounds[2], px)
                bounds[3] = max(bounds[3], py)
        return -bounds[0], -bounds[1], bounds[2]-width, bounds[3]-height

    def _paint_bounds(self, ox=0.0, oy=0.0):
        """Source bounds for the software transform fallback's temporary layer."""
        x, y, width, height = self._rect
        if hasattr(self, "_scrollbar_geometry"):
            return x+ox, y+oy, width, height
        from .widgets.scrolling import _paint_outsets
        left, top, right, bottom = _paint_outsets(self, width, height)
        return x+ox-left, y+oy-top, width+left+right, height+top+bottom

    def _effects_begin(self, r, ox=0.0, oy=0.0):
        r.translate_push(0.0, 0.0)
        if hasattr(r, "transform_push"):
            matrix = ((1., 0., 0., 1., 0., 0.) if self.rotate is None and
                      self.scale is None and self.offset is None else
                      self._transform_matrix(ox, oy))
            bounds = (self._paint_bounds(ox, oy) if matrix[:4] != (1., 0., 0., 1.)
                      and not getattr(r, "native_geometry", False) else None)
            r.transform_push(matrix, bounds=bounds)
        r.opacity_push(max(0.0, min(1.0, float(self.opacity))))

    def _effects_end(self, r):
        r.opacity_pop()
        if hasattr(r, "transform_pop"):
            r.transform_pop()
        r.translate_pop()

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
        self._effects_begin(r, ox, oy)
        try:
            self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
            for c in self._children():
                c._draw_all(r, ox, oy)
        finally:
            self._effects_end(r)

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
                    getattr(self, "url", None) or getattr(self, "on_tap_down", None) or
                    getattr(self, "on_long_press", None) or
                    getattr(self, "_focusable", False) or
                    getattr(self, "_draggable", False))

    def _contains(self, x, y) -> bool:
        rx, ry, rw, rh = self._rect
        return rw > 0 and rh > 0 and rx <= x < rx + rw and ry <= y < ry + rh

    def _hit_test(self, x, y) -> "Control | None":
        """Deepest visible, enabled control containing (x, y) that taps."""
        if not self.visible or self.disabled:
            return None
        x, y = self._hit_point(x, y)
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
        x, y = self._hit_point(x, y)
        for c in reversed(self._children()):
            hit = c._hit_test_hover(x, y)
            if hit is not None:
                return hit
        if (getattr(self, "on_hover", None) or self.tooltip or
                self.mouse_cursor or getattr(self, "_focusable", False)) and self._contains(x, y):
            return self
        return None

    def _find_scrollable(self, x, y):
        """Deepest ListView whose viewport contains (x, y)."""
        if not self.visible:
            return None
        x, y = self._hit_point(x, y)
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
