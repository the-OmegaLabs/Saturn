"""Text control. Icon/Image/Divider join this module in the widgets milestone."""
from __future__ import annotations

from collections import OrderedDict

from .. import colors
from .. import text as font_state
from ..control import Control
from ..text import (family_for, line_height, line_width, measure,
                    render_line_cached, wrap)
from ..text import weight_num
from ..types import TextAlign


class Text(Control):
    def __init__(self, value: str = "", *, size: float | None = None,
                 color=None, weight=None, italic: bool = False,
                 text_align=None, max_lines: int | None = None,
                 no_wrap: bool = False, selectable: bool | None = None,
                 font_family: str | None = None, **base):
        super().__init__(**base)
        self.value = value
        self.size = size if size is not None else 14
        self.color = color            # None → theme on_surface
        self.weight = weight
        self.italic = italic
        self.text_align = text_align
        self.max_lines = max_lines
        self.no_wrap = no_wrap
        self.selectable = selectable
        self.font_family = font_family
        self._lines: list[str] = []
        self._line_h = 0.0
        self._measure_cache = OrderedDict()
        self._wrap_cache = OrderedDict()

    # -- style helpers -----------------------------------------------------
    def _style(self, scale: float):
        return dict(scale=scale, weight=weight_num(self.weight),
                    italic=self.italic,
                    family=family_for(self.value, self.font_family))

    # -- layout hooks (flex engine drives these) ---------------------------
    def _intrinsic(self, max_w, max_h, scale):
        key = (self.value, self.size, self.weight, self.italic,
               self.font_family, font_state.default_family,
               font_state.font_revision, self.no_wrap, self.max_lines,
               max_w, scale, self._width, self._height)
        cached = self._measure_cache.get(key)
        if cached is not None:
            self._measure_cache.move_to_end(key)
            return cached
        kw = self._style(scale)
        if self.no_wrap:
            # Explicit newlines still create lines when soft wrapping is off.
            lines = self.value.split("\n")[:self.max_lines]
            w = max((line_width(line, self.size, **kw) for line in lines),
                    default=0.0)
            h = line_height(self.size, scale=scale,
                            family=family_for(self.value, self.font_family)) * len(lines)
        else:
            lines = self._wrapped(max_w if max_w is not None else 10_000,
                                  scale, kw)
            w = max((line_width(l, self.size, **kw) for l in lines),
                    default=0.0)
            h = line_height(self.size, scale=scale,
                            family=family_for(self.value, self.font_family)) * len(lines)
        if self._width is not None:
            w = self._width
        if self._height is not None:
            h = self._height
        self._measure_cache[key] = (w, h)
        if len(self._measure_cache) > 4:
            self._measure_cache.popitem(last=False)
        return w, h

    def _wrapped(self, width, scale, kw):
        key = (self.value, self.size, self.weight, self.italic,
               self.font_family, font_state.default_family,
               font_state.font_revision, self.max_lines, width, scale)
        cached = self._wrap_cache.get(key)
        if cached is None:
            cached = wrap(
                self.value, width, self.size,
                max_lines=self.max_lines, **kw) or [""]
            self._wrap_cache[key] = cached
            if len(self._wrap_cache) > 4:
                self._wrap_cache.popitem(last=False)
        else:
            self._wrap_cache.move_to_end(key)
        return cached

    def _place(self, x, y, w, h, scale):
        kw = self._style(scale)
        self._lines = (self.value.split("\n")[:self.max_lines]
                       if self.no_wrap else self._wrapped(w, scale, kw))
        self._line_h = line_height(self.size, scale=scale,
                                   family=kw["family"])
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        color = colors.parse_color(self.color or colors.Colors.ON_SURFACE)
        align = self.text_align or TextAlign.START
        w = self._rect[2]
        if self.no_wrap:
            r.clip_push(x, y, self._rect[2], self._rect[3])
        for line in self._lines:
            surf = render_line_cached(
                line, self.size, color=color, **self._style(r.scale))
            lw = surf.get_width() / r.scale
            if align in (TextAlign.CENTER, TextAlign.JUSTIFY):
                ox = (w - lw) / 2
            elif align in (TextAlign.RIGHT, TextAlign.END):
                ox = w - lw
            else:
                ox = 0.0
            r.blit_cached(surf, x + ox, y)
            y += self._line_h
        if self.no_wrap:
            r.clip_pop()
