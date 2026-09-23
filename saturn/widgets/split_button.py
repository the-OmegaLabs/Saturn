"""Small filled Material 3 Expressive split button.

40dp height, 2dp gap, full outer corners, and 4dp inner corners (12dp pressed).
"""
from __future__ import annotations

from .. import colors, motion, text as txt
from .._gen.icons import Icons
from ..control import Control
from ..text import render_icon_cached
from ..types import AnimationCurve
from ._material import draw_state_layer
from .buttons import Button


_HEIGHT = 40.0
_MIN_WIDTH = 48.0
_GAP = 2.0
_LABEL_SIZE = 14.0
_LABEL_WEIGHT = 500
_LEADING_ICON_SIZE = 20.0
_TRAILING_ICON_SIZE = 22.0


def _fill_segment(r, x, y, w, h, color, side, inner):
    """Clip disjoint halves so translucent fills are composited only once."""
    outer = min(h / 2, w / 2)
    inner = min(inner, h / 2, w / 2)
    radii = (outer, inner) if side == "leading" else (inner, outer)
    for half, radius in enumerate(radii):
        r.clip_push(x + half * w / 2, y, w / 2, h)
        try:
            r.fill_rect(x, y, w, h, color, radius=radius)
        finally:
            r.clip_pop()


class _SplitSegment(Button):
    variant_bg = colors.Colors.PRIMARY
    variant_fg = colors.Colors.ON_PRIMARY

    def __init__(self, content, *, side, icon, on_click, bgcolor, color,
                 disabled=False):
        super().__init__(content=content, icon=icon, on_click=on_click,
                         bgcolor=bgcolor, color=color, disabled=disabled)
        self.side = side
        self._inner_radius = 4.0

    def _intrinsic(self, max_w, max_h, scale):
        if self.side == "trailing":
            width = _MIN_WIDTH  # 13 + 22 + 13 from the small split token
        else:
            label_w = (txt.measure(self.content, _LABEL_SIZE, scale=scale,
                                   weight=_LABEL_WEIGHT)[0]
                       if isinstance(self.content, str) and self.content else 0.0)
            icon_w = _LEADING_ICON_SIZE if self.icon is not None else 0.0
            width = max(_MIN_WIDTH, 16.0 + icon_w +
                        (8.0 if icon_w and label_w else 0.0) + label_w + 12.0)
        return width, _HEIGHT

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        bg = self._bg()
        fg = self._fg()
        if bg is not None:
            _fill_segment(r, x, y, w, h, bg, self.side, self._inner_radius)
        if not self.disabled:
            outer, inner = min(w, h) / 2, self._inner_radius
            radii = ((outer, inner, inner, outer) if self.side == "leading"
                     else (inner, outer, outer, inner))
            draw_state_layer(self, r, (x, y, w, h), self._fg_raw(), radii)

        scale = r.scale
        icon_size = (_LEADING_ICON_SIZE if self.side == "leading"
                     else _TRAILING_ICON_SIZE)
        icon_surf = (render_icon_cached(self.icon, round(icon_size * scale), fg)
                     if self.icon is not None else None)
        label_surf = (txt.render_line_cached(self.content, _LABEL_SIZE,
                                             scale=scale, weight=_LABEL_WEIGHT,
                                             color=fg)
                      if self.side == "leading" and self.content else None)
        icon_w = icon_surf.get_width() / scale if icon_surf is not None else 0.0
        label_w = label_surf.get_width() / scale if label_surf is not None else 0.0
        gap = 8.0 if icon_w and label_w else 0.0
        cx = x + (w - icon_w - gap - label_w) / 2
        cy = y + h / 2
        if icon_surf is not None:
            r.blit(icon_surf, cx, cy - icon_surf.get_height() / (2 * scale),
                   alpha=.38 if self.disabled else 1.0)
            cx += icon_w + gap
        if label_surf is not None:
            r.blit(label_surf, cx, cy - label_surf.get_height() / (2 * scale),
                   alpha=.38 if self.disabled else 1.0)

    def _pressed_hook(self, x, y):
        super()._pressed_hook(x, y)
        self._animate_internal("_inner_radius", 12.0, motion.SHORT3,
                               AnimationCurve.FAST_OUT_SLOWIN)

    def _released_hook(self, x, y):
        super()._released_hook(x, y)
        self._animate_internal("_inner_radius", 4.0, motion.SHORT3,
                               AnimationCurve.FAST_OUT_SLOWIN)


class SplitButton(Control):
    """Two independently clickable segments; ``on_click`` is the main action.

    ``on_trailing_click`` handles the arrow segment. The gap is not clickable.
    """

    def __init__(self, content: str = "", *, icon=None,
                 trailing_icon=Icons.ARROW_DROP_DOWN, on_click=None,
                 on_trailing_click=None, bgcolor=None, color=None, **base):
        if not isinstance(content, str):
            raise TypeError("SplitButton content must be text")
        if not content and icon is None:
            raise ValueError("SplitButton needs leading text or an icon")
        super().__init__(**base)
        self.content = content
        self.icon = icon
        self.trailing_icon = trailing_icon
        self.leading_button = _SplitSegment(
            content, side="leading", icon=icon, on_click=on_click,
            bgcolor=bgcolor, color=color, disabled=self.disabled)
        self.trailing_button = _SplitSegment(
            None, side="trailing", icon=trailing_icon,
            on_click=on_trailing_click, bgcolor=bgcolor, color=color,
            disabled=self.disabled)

    def _children(self):
        return [self.leading_button, self.trailing_button]

    @property
    def on_click(self):
        return self.leading_button.on_click

    @on_click.setter
    def on_click(self, handler):
        self.leading_button.on_click = handler

    @property
    def on_trailing_click(self):
        return self.trailing_button.on_click

    @on_trailing_click.setter
    def on_trailing_click(self, handler):
        self.trailing_button.on_click = handler

    def _intrinsic(self, max_w, max_h, scale):
        self.leading_button.content = self.content
        self.leading_button.icon = self.icon
        self.trailing_button.icon = self.trailing_icon
        leading_w, _ = self.leading_button._intrinsic(max_w, max_h, scale)
        trailing_w, _ = self.trailing_button._intrinsic(max_w, max_h, scale)
        return (self._width if self._width is not None else leading_w + _GAP + trailing_w,
                self._height if self._height is not None else _HEIGHT)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        self.leading_button.disabled = self.trailing_button.disabled = self.disabled
        gap = min(_GAP, max(0.0, w))
        trailing_w = min(_MIN_WIDTH, max(0.0, w - gap))
        leading_w = max(0.0, w - gap - trailing_w)
        self.leading_button._place(x, y, leading_w, h, scale)
        self.trailing_button._place(x + leading_w + gap, y,
                                    trailing_w, h, scale)

    def _hit_test(self, x, y):
        if not self.visible or self.disabled:
            return None
        return self.trailing_button._hit_test(x, y) or self.leading_button._hit_test(x, y)

    def _hit_test_hover(self, x, y):
        if not self.visible or self.disabled:
            return None
        return (self.trailing_button._hit_test_hover(x, y) or
                self.leading_button._hit_test_hover(x, y))
