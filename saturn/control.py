"""Control base classes: state every control shares + dirty plumbing."""
from __future__ import annotations

import copy
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
    """Base of all controls. Mirrors flet `Control` + `LayoutControl` subset."""

    def __init__(self, *, visible: bool = True, disabled: bool = False,
                 opacity: float = 1.0, expand: bool | int | None = None,
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
                 on_animation_end=None, **_flet_ignored):
        object.__setattr__(self, "_animation_overrides", {})
        object.__setattr__(self, "_animation_targets", {})
        object.__setattr__(self, "_animations", {})
        object.__setattr__(self, "_animation_lock", threading.RLock())
        object.__setattr__(self, "_animation_seeded", False)
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
            self.page.update()

    def _attach(self, page, parent: "Control | None" = None):
        self.page = page
        self.parent = parent
        self._seed_animation_targets()
        for c in self._children():
            c._attach(page, self)

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
            self.page._app.mark_dirty()

    def _prepare_animation_tree(self, now: float):
        self._prepare_animations(now)
        for child in self._children():
            child._prepare_animation_tree(now)

    def _tick_animation_tree(self, now: float) -> bool:
        active = self._tick_animations(now)
        for child in self._children():
            active = child._tick_animation_tree(now) or active
        return active

    def _effects_begin(self, r):
        offset = self.offset
        if offset is not None:
            if isinstance(offset, tuple):
                dx, dy = offset
            else:
                dx, dy = offset.x, offset.y
            r.translate_push(dx * self._rect[2], dy * self._rect[3])
        else:
            r.translate_push(0.0, 0.0)
        r.opacity_push(max(0.0, min(1.0, float(self.opacity))))

    def _effects_end(self, r):
        r.opacity_pop()
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
        self._effects_begin(r)
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
        if (getattr(self, "on_hover", None) or self.tooltip) and self._contains(x, y):
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
