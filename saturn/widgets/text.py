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
        # Measuring many ordinary Text controls should not repeatedly look
        # up the same animation override map for every style field. Custom
        # subclasses keep normal attribute/property resolution.
        if type(self) is Text:
            state = object.__getattribute__(self, "__dict__")
            overrides = state["_animation_overrides"]
            if overrides:
                state = state | overrides
            value, size = state["value"], state["size"]
            weight, italic = state["weight"], state["italic"]
            family = state["font_family"]
            no_wrap, max_lines = state["no_wrap"], state["max_lines"]
            fixed_w, fixed_h = state["_width"], state["_height"]
            cache = state["_measure_cache"]
        else:
            value, size = self.value, self.size
            weight, italic, family = self.weight, self.italic, self.font_family
            no_wrap, max_lines = self.no_wrap, self.max_lines
            fixed_w, fixed_h, cache = self._width, self._height, self._measure_cache
        key = (value, size, weight, italic, family,
               font_state.default_family, font_state.font_revision,
               no_wrap, max_lines, max_w, scale, fixed_w, fixed_h)
        cached = cache.get(key)
        if cached is not None:
            cache.move_to_end(key)
            return cached
        kw = dict(scale=scale, weight=weight_num(weight), italic=italic,
                  family=family_for(value, family))
        available = max_w if max_w is not None else 10_000
        single_width = None
        if "\n" not in value and (max_lines is None or max_lines >= 1):
            candidate = line_width(value, size, **kw)
            if no_wrap or candidate <= available:
                single_width = candidate
        if single_width is not None:
            # Exact common case: neither a wrapping cache nor a second
            # width lookup is needed to measure an unbroken fitting line.
            w, h = single_width, line_height(size, scale=scale, family=kw["family"])
        elif no_wrap:
            # Explicit newlines still create lines when soft wrapping is off.
            lines = value.split("\n")[:max_lines]
            w = max((line_width(line, size, **kw) for line in lines),
                    default=0.0)
            h = line_height(size, scale=scale, family=kw["family"]) * len(lines)
        else:
            lines = self._wrapped(available, scale, kw)
            w = max((line_width(l, size, **kw) for l in lines),
                    default=0.0)
            h = line_height(size, scale=scale, family=kw["family"]) * len(lines)
        if fixed_w is not None:
            w = fixed_w
        if fixed_h is not None:
            h = fixed_h
        cache[key] = (w, h)
        if len(cache) > 4:
            cache.popitem(last=False)
        return w, h

    def _wrapped(self, width, scale, kw):
        if type(self) is Text:
            state = object.__getattribute__(self, "__dict__")
            if state["_animation_overrides"]:
                state = state | state["_animation_overrides"]
            value, size, max_lines = state["value"], state["size"], state["max_lines"]
            weight, italic, family = state["weight"], state["italic"], state["font_family"]
            cache = state["_wrap_cache"]
        else:
            value, size, max_lines = self.value, self.size, self.max_lines
            weight, italic, family = self.weight, self.italic, self.font_family
            cache = self._wrap_cache
        key = (value, size, weight, italic, family, font_state.default_family,
               font_state.font_revision, max_lines, width, scale)
        cached = cache.get(key)
        if cached is None:
            cached = wrap(
                value, width, size, max_lines=max_lines, **kw) or [""]
            cache[key] = cached
            if len(cache) > 4:
                cache.popitem(last=False)
        else:
            cache.move_to_end(key)
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
