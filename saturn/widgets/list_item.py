"""Expressive list item with text or existing-control content slots."""
from __future__ import annotations

from .. import colors, motion, text as txt
from ..control import Control
from ..event import fire
from ..types import as_border_radius
from ._material import (draw_state_layer, init_state_layer, press,
                        release, set_hover, tick_state_layer)


_SIDE = 16.0
_VERTICAL = 10.0
_GAP = 12.0
_MIN_HEIGHT = (56.0, 72.0, 88.0)
_STYLE = {
    "headline": (16.0, 24.0, 400),  # BodyLarge
    "supporting": (14.0, 20.0, 400),  # BodyMedium
    "overline": (11.0, 16.0, 500),   # LabelSmall
    "leading": (16.0, 24.0, 500),   # avatar label
    "trailing": (11.0, 16.0, 500),  # LabelSmall
}


def _mix(a, b, progress):
    a, b = colors.parse_color(a), colors.parse_color(b)
    return tuple(round(x + (y - x) * progress) for x, y in zip(a, b))


class ListItem(Control):
    """An interactive or passive M3 Expressive list row.

    ``content`` is the headline. ``selected`` is controlled by the caller;
    clicking invokes ``on_click`` without changing it automatically. Slots
    can be strings or controls, for example ``leading=Icon(...)``.
    """

    def __init__(self, content=None, *, headline=None, leading=None,
                 trailing=None, overline=None, supporting=None,
                 selected=False, container_color=None,
                 selected_container_color=None, content_color=None,
                 selected_content_color=None, border_radius=None,
                 on_click=None, on_hover=None, on_long_press=None, **base):
        super().__init__(**base)
        self.headline = headline if headline is not None else content
        self.leading = leading
        self.trailing = trailing
        self.overline = overline
        self.supporting = supporting
        self.selected = bool(selected)
        self.container_color = container_color
        self.selected_container_color = selected_container_color
        self.content_color = content_color
        self.selected_content_color = selected_content_color
        self.border_radius = border_radius
        self.on_click = on_click
        self.on_hover = on_hover
        self.on_long_press = on_long_press
        self._hovered = False
        self._pressed = False
        self._last_selected = self.selected
        self._selection_progress = 1.0 if self.selected else 0.0
        self._corner_radius = 16.0 if self.selected else 4.0
        self._slots = {}
        init_state_layer(self)

    def _children(self):
        return [slot for slot in (self.leading, self.overline, self.headline,
                                  self.supporting, self.trailing)
                if isinstance(slot, Control)]

    @staticmethod
    def _measure_slot(slot, name, max_width, scale):
        if slot is None:
            return 0.0, 0.0, ()
        limit = max(1.0, max_width) if max_width is not None else 1_000_000.0
        if isinstance(slot, Control):
            w, h = slot._intrinsic(limit, None, scale)
            return min(w, limit), h, ()
        if not isinstance(slot, str):
            raise TypeError(f"ListItem {name} must be a string or Control")
        size, line_height, weight = _STYLE[name]
        lines = tuple(txt.wrap(slot, limit, size, scale=scale, weight=weight))
        if not lines:
            return 0.0, line_height, ("",)
        width = max(txt.line_width(line, size, scale=scale, weight=weight)
                    for line in lines)
        return width, len(lines) * line_height, lines

    def _measure(self, width, scale):
        inner = max(1.0, width - 2 * _SIDE) if width is not None else None
        leading = self._measure_slot(self.leading, "leading", inner, scale)
        trailing = self._measure_slot(self.trailing, "trailing", inner, scale)
        gap_start = _GAP if self.leading is not None else 0.0
        gap_end = _GAP if self.trailing is not None else 0.0
        text_width = (None if inner is None else
                      max(1.0, inner - leading[0] - trailing[0]
                          - gap_start - gap_end))
        overline = self._measure_slot(self.overline, "overline", text_width, scale)
        headline = self._measure_slot(self.headline, "headline", text_width, scale)
        supporting = self._measure_slot(self.supporting, "supporting", text_width, scale)
        rows = 3 if (self.overline is not None and self.supporting is not None
                     or supporting[1] > 30.0) else 2 if (
                         self.overline is not None or self.supporting is not None) else 1
        text_height = overline[1] + headline[1] + supporting[1]
        natural_width = (2 * _SIDE + leading[0] + gap_start
                         + max(overline[0], headline[0], supporting[0])
                         + gap_end + trailing[0])
        natural_height = max(_MIN_HEIGHT[rows - 1],
                             2 * _VERTICAL + max(leading[1], text_height,
                                                 trailing[1]))
        return (natural_width, natural_height, rows,
                {"leading": leading, "trailing": trailing,
                 "overline": overline, "headline": headline,
                 "supporting": supporting})

    def _intrinsic(self, max_w, max_h, scale):
        width = self._width if self._width is not None else max_w
        natural_w, natural_h, _, _ = self._measure(width, scale)
        return (width if width is not None else natural_w,
                self._height if self._height is not None else natural_h)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        _, _, rows, measured = self._measure(w, scale)
        leading_w, leading_h, _ = measured["leading"]
        trailing_w, trailing_h, _ = measured["trailing"]
        text_x = x + _SIDE + (leading_w + _GAP if self.leading is not None else 0)
        text_w = max(0.0, w - (text_x - x) - _SIDE
                     - (trailing_w + _GAP if self.trailing is not None else 0))
        text_h = sum(measured[name][1] for name in
                     ("overline", "headline", "supporting"))
        text_y = y + (_VERTICAL if rows == 3 else (h - text_h) / 2)
        self._slots = {}
        for name in ("overline", "headline", "supporting"):
            slot = getattr(self, name)
            if slot is not None:
                _, slot_h, lines = measured[name]
                self._slots[name] = (text_x, text_y, text_w, slot_h, lines)
                if isinstance(slot, Control):
                    slot._place(text_x, text_y, text_w, slot_h, scale)
                text_y += slot_h
        side_y = y + _VERTICAL if rows == 3 else None
        if self.leading is not None:
            sy = side_y if side_y is not None else y + (h - leading_h) / 2
            self._slots["leading"] = (x + _SIDE, sy, leading_w, leading_h,
                                       measured["leading"][2])
            if isinstance(self.leading, Control):
                self.leading._place(x + _SIDE, sy, leading_w, leading_h, scale)
        if self.trailing is not None:
            sy = side_y if side_y is not None else y + (h - trailing_h) / 2
            sx = x + w - _SIDE - trailing_w
            self._slots["trailing"] = (sx, sy, trailing_w, trailing_h,
                                        measured["trailing"][2])
            if isinstance(self.trailing, Control):
                self.trailing._place(sx, sy, trailing_w, trailing_h, scale)

    def _target_radius(self):
        if self.border_radius is not None:
            return as_border_radius(self.border_radius).top_left
        if self.selected or self._pressed:
            return 16.0
        return 12.0 if self._hovered and self.on_click else 4.0

    def _prepare_animations(self, now):
        super()._prepare_animations(now)
        if self.selected != self._last_selected:
            self._last_selected = self.selected
            self._animate_internal("_selection_progress",
                                   1.0 if self.selected else 0.0,
                                   motion.SHORT3, motion.STANDARD, now=now)
            self._animate_internal("_corner_radius", self._target_radius(),
                                   motion.SHORT3, motion.STANDARD, now=now)

    def _slot_color(self, name):
        if self.disabled:
            return colors.parse_color(colors.Colors.ON_SURFACE)
        base = (self.content_color or colors.Colors.ON_SURFACE) if name == "headline" else \
            colors.Colors.ON_SURFACE_VARIANT
        selected = self.selected_content_color or colors.Colors.ON_SECONDARY_CONTAINER
        return _mix(base, selected, self._selection_progress)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        base = self.container_color or colors.Colors.SURFACE
        selected = self.selected_container_color or colors.Colors.SECONDARY_CONTAINER
        bg = (colors.parse_color(base) if self.disabled else
              _mix(base, selected, self._selection_progress))
        radius = self._corner_radius if self.border_radius is None else \
            as_border_radius(self.border_radius).top_left
        r.fill_rect(x, y, w, h, bg, radius=radius)
        if self.on_click is not None and not self.disabled:
            draw_state_layer(self, r, (x, y, w, h),
                             self._slot_color("headline"), radius)

    def _draw_all(self, r, ox=0.0, oy=0.0):
        if not self.visible:
            return
        self._effects_begin(r)
        try:
            self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
            r.clip_push(self._rect[0] + ox, self._rect[1] + oy,
                        self._rect[2], self._rect[3])
            r.opacity_push(.38 if self.disabled else 1.0)
            try:
                for name in ("leading", "overline", "headline", "supporting",
                             "trailing"):
                    slot = getattr(self, name)
                    if slot is None or name not in self._slots:
                        continue
                    sx, sy, _, _, lines = self._slots[name]
                    if isinstance(slot, Control):
                        # Inherited content color leaves explicit child colors alone.
                        attr = "color" if hasattr(slot, "color") else \
                            "icon_color" if hasattr(slot, "icon_color") else None
                        previous = getattr(slot, attr) if attr else None
                        if attr and previous is None:
                            setattr(slot, attr, self._slot_color(name))
                        try:
                            slot._draw_all(r, ox, oy)
                        finally:
                            if attr and previous is None:
                                setattr(slot, attr, None)
                        continue
                    size, line_height, weight = _STYLE[name]
                    color = self._slot_color(name)
                    for index, line in enumerate(lines):
                        surf = txt.render_line_cached(line, size, scale=r.scale,
                                                      weight=weight, color=color)
                        r.blit(surf, sx + ox, sy + oy + index * line_height
                               + (line_height - surf.get_height() / r.scale) / 2)
            finally:
                r.opacity_pop()
                r.clip_pop()
        finally:
            self._effects_end(r)

    def _hit_test_hover(self, x, y):
        if not self.visible or self.disabled:
            return None
        for child in reversed(self._children()):
            hit = child._hit_test_hover(x, y)
            if hit is not None:
                return hit
        return self if self._contains(x, y) and (
            self.on_click or self.on_hover or self.tooltip) else None

    def _set_hover(self, on):
        set_hover(self, on)
        self._animate_internal("_corner_radius", self._target_radius(),
                               motion.SHORT3, motion.STANDARD)
        self.update()
        fire(self, "hover", "true" if on else "false")

    def _pressed_hook(self, x, y):
        press(self, x, y, ripple_duration=motion.SHORT4, press_duration=75)
        self._animate_internal("_corner_radius", self._target_radius(),
                               motion.SHORT3, motion.STANDARD)

    def _released_hook(self, _x, _y):
        release(self, minimum_ms=0, fade_duration=motion.SHORT2)
        self._animate_internal("_corner_radius", self._target_radius(),
                               motion.SHORT3, motion.STANDARD)

    def _tick_animations(self, now):
        waiting = tick_state_layer(self, now)
        return super()._tick_animations(now) or waiting
