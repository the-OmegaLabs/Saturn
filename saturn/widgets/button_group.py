"""Expressive button groups with shared animated paint and hit rectangles."""
from __future__ import annotations

from .. import motion
from ..control import Control
from ..types import CrossAxisAlignment


class ButtonGroup(Control):
    """A horizontal row whose pressed button grows into its neighbors.

    ``connected=True`` uses the connected group's 2 dp gap instead
    of the standard 12 dp gap. Children may use ``expand`` as a width weight.
    ``expanded_ratio`` defaults to 15 percent.
    """

    def __init__(self, *items, controls=None, connected=False, spacing=None,
                 expanded_ratio=0.15, compression_limit=24.0,
                 vertical_alignment=CrossAxisAlignment.START, **base):
        if controls is not None:
            if items:
                raise TypeError("controls cannot be combined with positional children")
            items = tuple(controls)
        elif len(items) == 1 and isinstance(items[0], (list, tuple)):
            items = tuple(items[0])
        if not all(isinstance(item, Control) for item in items):
            raise TypeError("ButtonGroup children must be controls")
        if expanded_ratio < 0 or compression_limit < 0:
            raise ValueError("expanded_ratio and compression_limit must be nonnegative")
        super().__init__(**base)
        self.controls = list(items)
        self.connected = bool(connected)
        self.spacing = float((2.0 if connected else 12.0)
                             if spacing is None else spacing)
        if self.spacing < 0:
            raise ValueError("spacing must be nonnegative")
        self.expanded_ratio = float(expanded_ratio)
        self.compression_limit = float(compression_limit)
        self.vertical_alignment = vertical_alignment
        self._active_child = None
        self._pressed_child = None
        self._press_progress = 0.0
        self._release_pending = False
        self._natural_widths = {}
        self._clipped = set()

    def _children(self):
        return self.controls

    def _visible(self):
        return [child for child in self.controls if child.visible]

    @staticmethod
    def _weight(child):
        value = child.expand
        return 1.0 if value is True else max(0.0, float(value or 0.0))

    @staticmethod
    def _subtree_pressed(child):
        return bool(getattr(child, "_pressed", False)) or any(
            ButtonGroup._subtree_pressed(nested) for nested in child._children())

    def _prepare_animations(self, now):
        super()._prepare_animations(now)
        pressed = next((child for child in self._visible()
                        if self._subtree_pressed(child)), None)
        if pressed is self._pressed_child:
            return
        self._pressed_child = pressed
        if pressed is not None:
            self._active_child = pressed
            self._release_pending = False
            self._animate_internal("_press_progress", 1.0, motion.SHORT3,
                                   motion.EMPHASIZED, now=now)
        elif self._press_progress < 0.75:
            # Let a short press become visible before release.
            self._release_pending = True
        else:
            self._animate_internal("_press_progress", 0.0, motion.SHORT3,
                                   motion.EMPHASIZED, now=now)

    def _tick_animations(self, now):
        active = super()._tick_animations(now)
        if self._release_pending and self._press_progress >= 0.75:
            self._release_pending = False
            self._animate_internal("_press_progress", 0.0, motion.SHORT3,
                                   motion.EMPHASIZED, now=now)
            active = True
        return active or self._release_pending

    def _intrinsic(self, max_w, max_h, scale):
        children = self._visible()
        sizes = [child._intrinsic(max_w, max_h, scale) for child in children]
        natural = sum(width for width, _ in sizes)
        natural += self.spacing * max(0, len(children) - 1)
        height = max((height for _, height in sizes), default=0.0)
        if self._width is not None:
            width = self._width
        elif max_w is not None and (natural > max_w or any(
                self._weight(child) for child in children)):
            width = max_w
        else:
            width = natural
        return width, self._height if self._height is not None else height

    def _base_widths(self, children, width, scale):
        sizes = [child._intrinsic(width, None, scale) for child in children]
        widths = [max(0.0, size[0]) for size in sizes]
        available = max(0.0, width - self.spacing * max(0, len(children) - 1))
        used = sum(widths)
        weights = [self._weight(child) for child in children]
        if used < available and sum(weights) > 0:
            extra = available - used
            widths = [w + extra * weight / sum(weights)
                      for w, weight in zip(widths, weights)]
        elif used > available and used > 0:
            # Keep every child's paint and hitbox inside the row.
            widths = [w * available / used for w in widths]
        return widths, sizes

    def _press_widths(self, children, baseline):
        widths = baseline.copy()
        if self._active_child not in children or len(children) < 2:
            return widths
        index = children.index(self._active_child)
        progress = max(0.0, min(1.0, self._press_progress))
        if progress == 0:
            return widths
        def limit(child):
            return max(0.0, float(getattr(child,
                                         "button_group_compression_limit",
                                         self.compression_limit)))
        if index == 0:
            shrink = min(progress * self.expanded_ratio * baseline[0],
                         limit(children[1]), widths[1])
            widths[0] += shrink
            widths[1] -= shrink
        elif index == len(children) - 1:
            shrink = min(progress * self.expanded_ratio * baseline[index],
                         limit(children[index - 1]), widths[index - 1])
            widths[index] += shrink
            widths[index - 1] -= shrink
        else:
            target = progress * self.expanded_ratio * baseline[index] / 2
            left = min(target, limit(children[index - 1]), widths[index - 1])
            right = min(target, limit(children[index + 1]), widths[index + 1])
            widths[index - 1] -= left
            widths[index + 1] -= right
            widths[index] += left + right
        return widths

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        children = self._visible()
        baseline, sizes = self._base_widths(children, w, scale)
        widths = self._press_widths(children, baseline)
        self._natural_widths = {child: size[0]
                                for child, size in zip(children, sizes)}
        self._clipped = {child for child, width in zip(children, widths)
                         if width < self._natural_widths[child] - 0.01}
        cursor = x
        for child, child_w, (_, child_h) in zip(children, widths, sizes):
            if self.vertical_alignment is CrossAxisAlignment.STRETCH and \
                    child._height is None:
                child_h = h
            if self.vertical_alignment is CrossAxisAlignment.CENTER:
                child_y = y + (h - child_h) / 2
            elif self.vertical_alignment is CrossAxisAlignment.END:
                child_y = y + h - child_h
            else:
                child_y = y
            child._place(cursor, child_y, child_w, child_h, scale)
            cursor += child_w + self.spacing

    def _draw_all(self, r, ox=0.0, oy=0.0):
        if not self.visible:
            return
        self._effects_begin(r)
        try:
            for child in self._visible():
                if child in self._clipped:
                    x, y, w, h = child._rect
                    r.clip_push(x + ox, y + oy, w, h)
                    try:
                        child._draw_all(r, ox, oy)
                    finally:
                        r.clip_pop()
                else:
                    child._draw_all(r, ox, oy)
        finally:
            self._effects_end(r)
