"""Text control. Icon/Image/Divider join this module in the widgets milestone."""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Unpack

from collections import OrderedDict

from .. import colors
from .. import text as font_state
from ..control import Control, ControlOptions
from ..text import (family_for, line_height, line_width, measure,
                    render_line_cached, wrap)
from ..text import weight_num
from ..types import TextAlign, TextOverflow, TextSelection
from ..event import fire, dispatch_event, TextSelectionChangeEvent


class Text(Control):
    __unsupported_parameters__ = {"spans", "theme_style"}

    def __init__(self, value: str = "", *, size: float | None = None,
                 color=None, weight=None, italic: bool = False,
                 text_align=None, max_lines: int | None = None,
                 no_wrap: bool = False, selectable: bool | None = None,
                 font_family: str | None = None, style=None, bgcolor=None,
                 overflow=TextOverflow.CLIP, font_family_fallback=None,
                 on_tap=None, on_selection_change=None,
                 show_selection_cursor=False, enable_interactive_selection=True,
                 selection_cursor_width=2.0, selection_cursor_height=None,
                 selection_cursor_color=None, spans=None, theme_style=None,
                 **base: Unpack[ControlOptions]):
        if spans is not None or theme_style is not None:
            raise NotImplementedError("Rich TextSpan and theme_style text are not supported yet")
        if getattr(overflow, "value", overflow) == "fade":
            raise NotImplementedError("Text overflow FADE needs a renderer mask; use CLIP or ELLIPSIS")
        super().__init__(**base)
        self.value = value
        self.size = size if size is not None else getattr(style, "size", None) or 14
        self.color = color if color is not None else getattr(style, "color", None)
        self.weight = weight if weight is not None else getattr(style, "weight", None)
        self.italic = italic or getattr(style, "italic", False)
        self.text_align = text_align
        self.max_lines = max_lines
        self.no_wrap = no_wrap
        self.selectable = selectable
        self.font_family = font_family or getattr(style, "font_family", None)
        self.font_family_fallback = list(font_family_fallback or [])
        self.style = style
        self.bgcolor = bgcolor if bgcolor is not None else getattr(style, "bgcolor", None)
        self.overflow = getattr(style, "overflow", None) or overflow
        self.on_tap = on_tap
        self.on_selection_change = on_selection_change
        self.on_click = lambda event=None: fire(self, "tap")
        self.show_selection_cursor = show_selection_cursor
        self.enable_interactive_selection = enable_interactive_selection
        self.selection_cursor_width = selection_cursor_width
        self.selection_cursor_height = selection_cursor_height
        self.selection_cursor_color = selection_cursor_color
        self._focusable = bool(selectable)
        self.read_only = True
        self._caret = self._selection_anchor = 0
        self._focused = False
        self._selection_dragging = False
        self._last_selection = None
        self._paint_offset = (0.0, 0.0)
        self._lines: list[str] = []
        self._line_h = 0.0
        self._style_snapshot = None
        self._sync_style(initial=True)
        self._measure_cache = OrderedDict()
        self._wrap_cache = OrderedDict()

    # -- style helpers -----------------------------------------------------
    @property
    def value(self) -> str:
        return self.__dict__["value"]

    @value.setter
    def value(self, value):
        # flet parity: numbers and other non-strings are accepted and shown
        # as text instead of crashing the layout pass. Stored under the raw
        # __dict__ key the animation/measurement paths read.
        self.__dict__["value"] = "" if value is None else str(value)

    def _style(self, scale: float):
        self._sync_style()
        return dict(scale=scale, weight=weight_num(self.weight),
                    italic=self.italic,
                    family=self._family(),
                    letter_spacing=float(getattr(self.style, "letter_spacing", 0) or 0))

    def _sync_style(self, initial=False):
        style = self.style
        if style is None:
            return
        if getattr(getattr(style, "overflow", None), "value", getattr(style, "overflow", None)) == "fade":
            raise NotImplementedError("TextStyle overflow FADE needs a renderer mask")
        for name in ("word_spacing", "height", "decoration", "decoration_color", "decoration_thickness"):
            value = getattr(style, name, None)
            if value not in (None, 0, 0.0) and not (name == "decoration" and getattr(value, "value", value) == "none"):
                raise NotImplementedError(f"TextStyle.{name} is not supported by desktop text shaping")
        snapshot = tuple(getattr(style, name, None) for name in
                         ("size", "color", "weight", "italic", "font_family", "bgcolor", "overflow"))
        if snapshot == self._style_snapshot:
            return
        names = ("size", "color", "weight", "italic", "font_family", "bgcolor", "overflow")
        if not initial and self._style_snapshot is not None:
            for name, old, new in zip(names, self._style_snapshot, snapshot):
                if getattr(self, name) == old and new is not None:
                    setattr(self, name, new)
        elif not initial:
            for name, new in zip(names, snapshot):
                if new is not None:
                    setattr(self, name, new)
        self._style_snapshot = snapshot

    @property
    def _handles_tap(self):
        return bool(self.selectable or self.on_tap or self.tooltip)

    @property
    def _focusable(self):
        return bool(self.selectable)

    @_focusable.setter
    def _focusable(self, value):
        pass  # Focus follows selectable, including property changes after mounting.

    def _family(self):
        primary = family_for(self.value, self.font_family)
        return ((primary, *self.font_family_fallback)
                if self.font_family_fallback else primary)

    @property
    def selection(self):
        return TextSelection(self._selection_anchor, self._caret)

    def _selection_changed(self):
        current = (self._selection_anchor, self._caret, self.value)
        if current != self._last_selection:
            self._last_selection = current
            selection = self.selection
            dispatch_event(self, "selection_change", TextSelectionChangeEvent(
                "selection_change", self, selection=selection,
                text=self.value[selection.start:selection.end]))
            self.repaint()

    def _position_index(self, x, y):
        scale = self.page._app.renderer.scale if self.page else 1.0
        row = max(0, min(len(self._lines) - 1,
                         int((y - self._rect[1]) / max(1, self._line_h))))
        line = self._lines[row] if self._lines else ""
        offset = self._aligned_offset(line, self._rect[2], scale)
        px = x - self._rect[0] - offset
        index = 0
        for i in range(len(line)):
            before = self._line_position(line, i, self._rect[2], scale, row)
            after = self._line_position(line, i + 1, self._rect[2], scale, row)
            if px < (before + after) / 2:
                break
            index = i + 1
        cursor = 0
        for previous in self._lines[:row]:
            found = self.value.find(previous, cursor)
            cursor = max(cursor, found) + len(previous)
        start = self.value.find(line, cursor)
        return max(cursor, start) + index

    def _pointer_down(self, x, y, clicks=1):
        if not self.selectable or not self.enable_interactive_selection:
            return
        index = self._position_index(x, y)
        self._caret = self._selection_anchor = index
        if clicks % 3 == 2:
            while self._selection_anchor > 0 and self.value[self._selection_anchor - 1].isalnum():
                self._selection_anchor -= 1
            while self._caret < len(self.value) and self.value[self._caret].isalnum():
                self._caret += 1
        elif clicks % 3 == 0:
            self._selection_anchor = 0
            self._caret = len(self.value)
        self._selection_changed()

    def _drag_start(self, x, y):
        self._selection_dragging = bool(self.selectable and self.enable_interactive_selection)

    def _drag(self, x, y):
        if self._selection_dragging:
            self._caret = self._position_index(x, y)
            self._selection_changed()

    def _drag_end(self):
        self._selection_dragging = False

    def _key(self, event):
        import pygame
        from .inputs import _clipboard_copy
        shortcut = event.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)
        if shortcut and event.key == pygame.K_a and self.enable_interactive_selection:
            self._selection_anchor, self._caret = 0, len(self.value)
        elif shortcut and event.key == pygame.K_c:
            selection = self.selection
            _clipboard_copy(self.value[selection.start:selection.end])
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_HOME, pygame.K_END):
            old = self._caret
            target = (old - 1 if event.key == pygame.K_LEFT else old + 1 if event.key == pygame.K_RIGHT
                      else 0 if event.key == pygame.K_HOME else len(self.value))
            self._caret = max(0, min(len(self.value), target))
            if not (event.mod & pygame.KMOD_SHIFT and self.enable_interactive_selection):
                self._selection_anchor = self._caret
        self._selection_changed()

    def _aligned_offset(self, line, width, scale):
        lw = line_width(line, self.size, **self._style(scale))
        align = getattr(self.text_align, "value", self.text_align) or "start"
        if align == "center":
            return (width - lw) / 2
        if align in ("right", "end"):
            return width - lw
        return 0.0

    def _line_position(self, line, index, width, scale, row):
        prefix = line[:index]
        natural = line_width(prefix, self.size, **self._style(scale))
        if (getattr(self.text_align, "value", self.text_align) == "justify"
                and row < len(self._lines) - 1 and " " in line):
            extra = max(0, width - line_width(line, self.size, **self._style(scale))) / line.count(" ")
            return natural + prefix.count(" ") * extra
        return natural

    def _ellipsized(self, line, width, scale):
        if line_width(line, self.size, **self._style(scale)) <= width:
            return line
        lo, hi = 0, len(line)
        while lo < hi:
            middle = (lo + hi + 1) // 2
            if line_width(line[:middle] + "…", self.size, **self._style(scale)) <= width:
                lo = middle
            else:
                hi = middle - 1
        return line[:lo] + "…" if width >= line_width("…", self.size, **self._style(scale)) else ""

    # -- layout hooks (flex engine drives these) ---------------------------
    def _intrinsic(self, max_w, max_h, scale):
        if self.style is not None:
            self._sync_style()
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
            family = self._family() if state["font_family_fallback"] else state["font_family"]
            no_wrap, max_lines = state["no_wrap"], state["max_lines"]
            fixed_w, fixed_h = state["_width"], state["_height"]
            cache = state["_measure_cache"]
            spacing = float(getattr(state["style"], "letter_spacing", 0) or 0)
        else:
            value, size = self.value, self.size
            weight, italic, family = self.weight, self.italic, self._family()
            no_wrap, max_lines = self.no_wrap, self.max_lines
            fixed_w, fixed_h, cache = self._width, self._height, self._measure_cache
            spacing = float(getattr(self.style, "letter_spacing", 0) or 0)
        key = (value, size, weight, italic, family,
               font_state.default_family, font_state.font_revision,
               no_wrap, max_lines, max_w, scale, fixed_w, fixed_h, spacing)
        cached = cache.get(key)
        if cached is not None:
            cache.move_to_end(key)
            return cached
        kw = dict(scale=scale, weight=weight_num(weight), italic=italic,
                  family=family if isinstance(family, tuple) else family_for(value, family),
                  letter_spacing=spacing)
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
            weight, italic, family = state["weight"], state["italic"], self._family() if state["font_family_fallback"] else state["font_family"]
            cache = state["_wrap_cache"]
        else:
            value, size, max_lines = self.value, self.size, self.max_lines
            weight, italic, family = self.weight, self.italic, self._family()
            cache = self._wrap_cache
        key = (value, size, weight, italic, family, font_state.default_family,
               font_state.font_revision, max_lines, width, scale,
               kw.get("letter_spacing", 0))
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
        self._sync_style()
        color = colors.parse_color(self.color or colors.Colors.ON_SURFACE)
        w, h = self._rect[2:]
        self._paint_offset = (x - self._rect[0], y - self._rect[1])
        overflow = getattr(self.overflow, "value", self.overflow)
        if self.bgcolor is not None:
            r.fill_rect(x, y, w, h, colors.parse_color(self.bgcolor))
        clipped = overflow != "visible"
        if clipped:
            r.clip_push(x, y, w, h)
        cursor = 0
        selection = self.selection
        for row, original in enumerate(self._lines):
            line = self._ellipsized(original, w, r.scale) if overflow == "ellipsis" else original
            if overflow == "ellipsis" and self.max_lines and row == self.max_lines - 1:
                remainder = self.value.find(original, cursor) + len(original)
                if remainder < len(self.value):
                    line = self._ellipsized(original + "…", w, r.scale)
            ox = self._aligned_offset(line, w, r.scale)
            start = max(cursor, self.value.find(original, cursor))
            end = start + len(original)
            if self.selectable and selection.start < end and selection.end > start:
                a, b = max(0, selection.start - start), min(len(original), selection.end - start)
                left = self._line_position(original, a, w, r.scale, row)
                right = self._line_position(original, b, w, r.scale, row)
                r.fill_rect(x + ox + left, y, right - left, self._line_h,
                            colors.parse_color(colors.with_opacity(.35, colors.Colors.PRIMARY)))
            if getattr(self.text_align, "value", self.text_align) == "justify" and row < len(self._lines) - 1 and " " in line:
                index = 0
                for word in line.split(" "):
                    wx = self._line_position(line, index, w, r.scale, row)
                    surf = render_line_cached(word, self.size, color=color, **self._style(r.scale))
                    r.blit_cached(surf, x + wx, y)
                    index += len(word) + 1
            else:
                surf = render_line_cached(line, self.size, color=color, **self._style(r.scale))
                r.blit_cached(surf, x + ox, y)
            if self.selectable and self.show_selection_cursor and self._focused and start <= self._caret <= end:
                left = self._line_position(original, self._caret - start, w, r.scale, row)
                ch = self.selection_cursor_height or self._line_h
                r.fill_rect(x + ox + left, y + (self._line_h - ch) / 2,
                            self.selection_cursor_width, ch,
                            colors.parse_color(self.selection_cursor_color or colors.Colors.PRIMARY))
            cursor = end
            y += self._line_h
        if clipped:
            r.clip_pop()
