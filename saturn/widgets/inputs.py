"""Input controls: TextField, Checkbox, Switch, Radio/RadioGroup, Slider,
Dropdown (+ legacy Option alias).
"""
from __future__ import annotations

import math
import re
import threading
import time
from functools import lru_cache

import pygame
import pyperclip

from .containers import Container, Row
from ._material import (draw_state_layer, init_state_layer, press,
                        release, set_hover, tick_state_layer)
from .text import Text
from .. import colors, motion, text as txt
from .._gen.icons import Icons
from ..control import Control
from ..event import fire, dispatch_event, TextSelectionChangeEvent
from ..text import get_font, get_icon_font
from ..painting import draw_notched_outline
from ..types import (Alignment, AnimationCurve, LabelPosition,
                     OutlineInputBorder, Padding, TextAlign, TextSelection, TextCapitalization,
                     InputFilter, as_border_radius, as_padding)

_FIELD_H = 56.0
_FIELD_PAD = 16.0
_RADIUS = 4.0
_ITEM_H = 48.0
_IME_OFFSET_X = -6.0
_IME_OFFSET_Y = -4.0
_FIELD_TRANSITION_MS = 150
_FIELD_TRANSITION_CURVE = AnimationCurve.EASE_IN_OUT_CUBIC_EMPHASIZED


@lru_cache(maxsize=128)
def _font_ink_offset(family, size, scale, default_family, font_revision):
    """Center stable reference ink on the caret without per-value jumps."""
    sample = txt.render_line(
        "0123456789", size, scale=scale, family=family,
        color=(255, 255, 255, 255))
    ink = sample.get_bounding_rect(min_alpha=24)
    if not ink.height:
        return 0.0
    return (sample.get_height() / 2 - (ink.y + ink.height / 2)) / scale


def _text_ink_offset(family, size, scale):
    return _font_ink_offset(
        family, float(size), float(scale), txt.default_family,
        txt.font_revision)


def _parse(c):
    return colors.parse_color(c)


def _mix(a, b, progress: float):
    """Blend two RGBA colors using an animation progress value."""
    a, b = _parse(a), _parse(b)
    progress = max(0.0, min(1.0, progress))
    return tuple(round(x + (y - x) * progress) for x, y in zip(a, b))


def _clipboard_copy(value: str) -> bool:
    try:
        pyperclip.copy(value)
        return True
    except (OSError, RuntimeError, pyperclip.PyperclipException):
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT,
                              value.encode("utf-8") + b"\0")
            return True
        except (pygame.error, UnicodeError):
            return False


def _clipboard_paste() -> str | None:
    try:
        return str(pyperclip.paste())
    except (OSError, RuntimeError, pyperclip.PyperclipException):
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            value = pygame.scrap.get(pygame.SCRAP_TEXT)
            return (value.decode("utf-8", errors="replace").rstrip("\0")
                    if value is not None else None)
        except (pygame.error, UnicodeError):
            return None


def _enum_value(value):
    return getattr(value, "value", value)


def _state_value(control, value, fallback=None):
    if not isinstance(value, dict):
        return value if value is not None else fallback
    states = ("disabled" if control.disabled else None,
              "pressed" if getattr(control, "_pressed", False) else None,
              "hovered" if getattr(control, "_hovered", False) else None,
              "focused" if getattr(control, "_focused", False) else None,
              "selected" if getattr(control, "value", False) else None, "")
    for state in states:
        if state is None:
            continue
        for key, result in value.items():
            if _enum_value(key) in (state, "default" if state == "" else state):
                return result
    return fallback


def _style_values(style, size=14, color=None):
    return (getattr(style, "size", None) or size,
            getattr(style, "font_family", None),
            getattr(style, "color", None) or color or colors.Colors.ON_SURFACE)


def _adornment(value, style=None, size=16):
    if value is None:
        return None
    if isinstance(value, Control):
        return value
    return Text(str(value), size=size, style=style, no_wrap=True)


def _icon_control(value):
    if value is None or isinstance(value, Control):
        return value
    from .basic import Icon
    return Icon(value, size=24)


def _filtered(value, input_filter):
    if input_filter is None:
        return value
    pattern = re.compile(input_filter.regex_string)
    replacement = input_filter.replacement_string
    if not input_filter.allow:
        return pattern.sub(replacement, value)
    out, position = [], 0
    for match in pattern.finditer(value):
        if match.start() > position:
            out.append(replacement)
        out.append(match.group())
        position = match.end()
    if position < len(value):
        out.append(replacement)
    return "".join(out)


class TextField(Control):
    __unsupported_parameters__ = {
        "autocorrect", "enable_suggestions", "smart_dashes_type", "smart_quotes_type",
        "enable_ime_personalized_learning", "enable_stylus_handwriting",
        "autofill_hints", "keyboard_brightness", "animate_cursor_opacity",
        "always_call_on_tap", "scroll_padding", "strut_style", "clip_behavior",
        "align_label_with_hint", "hint_fade_duration", "hint_max_lines",
        "helper_max_lines", "error_max_lines", "prefix_icon_size_constraints",
        "suffix_icon_size_constraints", "size_constraints", "fit_parent_size"}

    def __init__(self, value: str = "", *, label=None, hint_text=None,
                 password: bool = False, multiline: bool = False,
                 min_lines: int | None = None, max_lines: int | None = None,
                 read_only: bool = False, max_length: int | None = None,
                 shift_enter: bool = False, ignore_up_down_keys=False,
                 show_cursor: bool = True, obscuring_character: str = "•",
                 text_size: float | None = None, on_change=None, on_submit=None,
                 on_focus=None, on_blur=None, on_click=None, on_tap_outside=None,
                 on_selection_change=None, selection=None, autofocus=False,
                 text_align=None, text_vertical_align=None,
                 can_request_focus=True, ignore_pointers=False,
                 enable_interactive_selection=True, input_filter=None,
                 capitalization=None, keyboard_type=None,
                 cursor_color=None, cursor_error_color=None, cursor_width=2.0,
                 cursor_height=None, cursor_radius=None, selection_color=None,
                 filled: bool = False, bgcolor=None, border_color=None,
                 border_radius: float | None = None, border_width=None,
                 focused_border_color=None, focused_border_width=None,
                 border=None, text_style=None, color=None, focused_color=None,
                 focused_bgcolor=None, fill_color=None, focus_color=None, hover_color=None, content_padding=None,
                 dense=None, collapsed=None, label_style=None, hint_style=None,
                 helper=None, helper_style=None, counter=None, counter_style=None,
                 error=None, error_style=None, prefix=None, prefix_style=None,
                 suffix=None, suffix_style=None, icon=None, prefix_icon=None,
                 suffix_icon=None, can_reveal_password: bool = False,
                 on_hover=None, autocorrect=True, enable_suggestions=True,
                 smart_dashes_type=True, smart_quotes_type=True,
                 enable_ime_personalized_learning=True,
                 enable_stylus_handwriting=True, autofill_hints=None,
                 keyboard_brightness=None, **base):
        unsupported = dict(autocorrect=(autocorrect, True),
                           enable_suggestions=(enable_suggestions, True),
                           smart_dashes_type=(smart_dashes_type, True),
                           smart_quotes_type=(smart_quotes_type, True),
                           enable_ime_personalized_learning=(enable_ime_personalized_learning, True),
                           enable_stylus_handwriting=(enable_stylus_handwriting, True),
                           autofill_hints=(autofill_hints, None),
                           keyboard_brightness=(keyboard_brightness, None))
        for name, (actual, default) in unsupported.items():
            if actual != default:
                raise NotImplementedError(f"{name} is not available in the SDL desktop backend")
        super().__init__(**base)
        if max_length is not None and (max_length == 0 or max_length < -1):
            raise ValueError("max_length must be positive or -1")
        if len(obscuring_character) != 1:
            raise ValueError("obscuring_character must be one character")
        if min_lines is not None and min_lines < 1 or max_lines is not None and max_lines < 1:
            raise ValueError("min_lines and max_lines must be positive")
        if min_lines and max_lines and min_lines > max_lines:
            raise ValueError("min_lines must not exceed max_lines")
        if cursor_width <= 0 or cursor_height is not None and cursor_height <= 0:
            raise ValueError("cursor dimensions must be positive")
        if keyboard_type is not None and _enum_value(keyboard_type) not in ("text", "multiline", "visiblePassword", "none"):
            raise NotImplementedError("keyboard_type cannot select a native desktop keyboard; use input_filter for validation")
        values = locals().copy()
        for name in ("value label hint_text password multiline min_lines max_lines read_only max_length shift_enter ignore_up_down_keys show_cursor obscuring_character on_change on_submit on_focus on_blur on_click on_tap_outside on_selection_change autofocus text_align text_vertical_align can_request_focus ignore_pointers enable_interactive_selection input_filter capitalization keyboard_type cursor_color cursor_error_color cursor_width cursor_height cursor_radius selection_color filled bgcolor border_color border_radius border_width focused_border_color focused_border_width border text_style color focused_color focused_bgcolor fill_color focus_color hover_color content_padding dense collapsed label_style hint_style helper helper_style counter counter_style error error_style prefix prefix_style suffix suffix_style icon prefix_icon suffix_icon can_reveal_password on_hover").split():
            setattr(self, name, values[name])
        self.value = str(value)
        self.text_size = text_size or 16.0
        self._password_revealed = False
        self._caret = len(value)
        self._selection_anchor = None
        self._selection_dragging = False
        self._selection_drag_mode = "character"
        self._drag_selection_origin = (self._caret, self._caret)
        self._composition = ""
        self._composition_start = 0
        self._composition_length = 0
        self._last_ime_rect = None
        self._focused = False
        self._focusable = bool(can_request_focus)
        self._hovered = False
        self._focus_progress = 0.0
        self._label_progress = 1.0 if value else 0.0
        self._hover_progress = 0.0
        self._cursor_visible = True
        self._cursor_timer = None
        self._cursor_generation = 0
        self._line_cache = {}
        self._last_value = value
        self._scroll_x = 0.0
        self._scroll_y = 0.0
        self._paint_offset = (0.0, 0.0)
        self._last_selection_event = None
        self._adornments = {}
        self._multiline_cache = None
        if selection is not None:
            self.selection = selection

    @property
    def selection(self):
        return TextSelection(self._caret if self._selection_anchor is None
                             else self._selection_anchor, self._caret)

    @selection.setter
    def selection(self, value):
        if value is None:
            self._clear_selection()
        else:
            self._select_range(value.base_offset, value.extent_offset)
        self._notify_selection()
        self.update()

    def _notify_selection(self):
        selection = self.selection
        state = (selection.base_offset, selection.extent_offset, self.value)
        if state == self._last_selection_event:
            return
        self._last_selection_event = state
        dispatch_event(self, "selection_change", TextSelectionChangeEvent(
            name="selection_change", control=self, selection=selection,
            text=self.value[selection.start:selection.end]))

    def _children(self):
        result = []
        for name in ("label", "helper", "counter", "error", "prefix", "suffix", "icon", "prefix_icon", "suffix_icon"):
            value = getattr(self, name, None)
            if isinstance(value, Control):
                result.append(value)
        return result

    def _padding(self):
        return as_padding(self.content_padding if self.content_padding is not None
                          else (8 if self.dense else 0 if self.collapsed else _FIELD_PAD))

    def _support_height(self):
        return 22.0 if self.helper is not None or self.error is not None or self.counter is not None else 0.0

    def _field_height(self):
        return max(0.0, self._rect[3] - self._support_height())

    def _style(self):
        """(family, value size, value color) from text_style."""
        ts = self.text_style
        for name in ("word_spacing", "height", "decoration", "decoration_color", "decoration_thickness"):
            value = getattr(ts, name, None)
            if value not in (None, 0, 0.0) and not (name == "decoration" and _enum_value(value) == "none"):
                raise NotImplementedError(f"TextStyle.{name} is not supported by desktop input shaping")
        if ts is None:
            return None, self.text_size, (self.focused_color if self._focused and self.focused_color is not None else self.color) or colors.Colors.ON_SURFACE
        return (ts.font_family,
                ts.size or self.text_size,
                (self.focused_color if self._focused and self.focused_color is not None else self.color) or ts.color or colors.Colors.ON_SURFACE)

    def _spacing(self) -> float:
        return float(getattr(self.text_style, "letter_spacing", 0) or 0)

    def _line_width(self, value, size, *, scale=1.0, family=None):
        style = self.text_style
        return txt.line_width(value, size, scale=scale, family=family,
                              weight=txt.weight_num(getattr(style, "weight", None)),
                              italic=getattr(style, "italic", False),
                              letter_spacing=self._spacing())

    def _render_cached(self, slot, text, size, scale, family, color):
        """Reuse immutable text rasters across short state animations."""
        color = tuple(_parse(color))
        style = (self.hint_style if slot == "hint" else self.label_style if slot.startswith("label") else self.text_style)
        weight, italic = txt.weight_num(getattr(style, "weight", None)), getattr(style, "italic", False)
        spacing = self._spacing()
        key = (slot, text, float(size), float(scale), family, color, weight, italic,
               spacing, txt.default_family, txt.font_revision)
        surface = self._line_cache.get(key)
        if surface is None:
            surface = txt.render_line(
                text, size, scale=scale, family=family, color=color, weight=weight,
                italic=italic, letter_spacing=spacing)
            self._line_cache[key] = surface
            if len(self._line_cache) > 32:
                self._line_cache.pop(next(iter(self._line_cache)))
        return surface

    def _prepare_animations(self, now: float):
        super()._prepare_animations(now)
        if self.value != self._last_value:
            self._last_value = self.value
            self._caret = min(self._caret, len(self.value))
            if self._selection_anchor is not None:
                self._selection_anchor = min(
                    self._selection_anchor, len(self.value))
            self._animate_internal(
                "_label_progress",
                1.0 if self._focused or bool(self.value) else 0.0,
                _FIELD_TRANSITION_MS, _FIELD_TRANSITION_CURVE, now=now)

    # -- layout --------------------------------------------------------------
    def _draw_all(self, r, ox=0.0, oy=0.0):
        if self.visible:
            self._effects_begin(r, ox, oy)
            try:
                self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
            finally:
                self._effects_end(r)

    def _intrinsic(self, max_w, max_h, scale):
        w = self._width if self._width is not None else min(300.0, max_w or 300.0)
        if self.multiline:
            lines = max(self.min_lines or 1, min(self.max_lines or 3, self.value.count("\n") + 1))
            p = self._padding()
            h = p.top + p.bottom + txt.line_height(self._style()[1], scale=scale) * lines
        else:
            h = (40.0 if self.dense else _FIELD_H) if not self.collapsed else txt.line_height(self._style()[1], scale=scale)
        h += self._support_height()
        return (self._width if self._width is not None else w,
                self._height if self._height is not None else h)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    # -- text helpers ----------------------------------------------------------
    def _visible_text(self) -> str:
        return (self.obscuring_character * len(self.value)
                if self.password and not self._password_revealed else self.value)

    def _visible_composition(self) -> str:
        if self.password and not self._password_revealed:
            return self.obscuring_character * len(self._composition)
        return self._composition

    def _pressed_hook(self, x, y):
        if self.password and self.can_reveal_password:
            rx, _, rw, _ = self._rect
            if x >= rx + rw - 48:
                self._password_revealed = not self._password_revealed
                self.update()

    def _hit_test_hover(self, x, y):
        x, y = self._hit_point(x, y)
        if not self.visible or self.disabled or self.ignore_pointers:
            return None
        return self if self._contains(x, y) else None

    def _set_hover(self, on: bool):
        self._hovered = bool(on)
        self._animate_internal("_hover_progress", 1.0 if on else 0.0,
                               _FIELD_TRANSITION_MS,
                               _FIELD_TRANSITION_CURVE)
        self.update()
        fire(self, "hover", "true" if on else "false")

    def _set_focused(self, focused: bool):
        self._focused = bool(focused)
        self._animate_internal("_focus_progress", 1.0 if focused else 0.0,
                               _FIELD_TRANSITION_MS,
                               _FIELD_TRANSITION_CURVE)
        self._animate_internal(
            "_label_progress", 1.0 if focused or bool(self.value) else 0.0,
            _FIELD_TRANSITION_MS, _FIELD_TRANSITION_CURVE)
        if focused:
            self._restart_cursor_blink()
        else:
            self._stop_cursor_blink()
        self.update()

    def _stop_cursor_blink(self):
        self._cursor_generation += 1
        timer, self._cursor_timer = self._cursor_timer, None
        if timer is not None:
            timer.cancel()
        self._cursor_visible = False

    def _restart_cursor_blink(self):
        self._cursor_generation += 1
        generation = self._cursor_generation
        timer = self._cursor_timer
        if timer is not None:
            timer.cancel()
        self._cursor_timer = None
        if not self.show_cursor:
            self._cursor_visible = False
            return
        self._cursor_visible = True

        def blink():
            if not self._focused or generation != self._cursor_generation:
                return
            self._cursor_visible = not self._cursor_visible
            self.update()
            next_timer = threading.Timer(0.5, blink)
            next_timer.daemon = True
            self._cursor_timer = next_timer
            next_timer.start()

        timer = threading.Timer(0.5, blink)
        timer.daemon = True
        self._cursor_timer = timer
        timer.start()

    def _font(self, scale):
        family, vsize, _ = self._style()
        return get_font(vsize, scale=scale, family=family,
                        text=self.value or self.hint_text or (self.label if isinstance(self.label, str) else ""))

    def _index_at(self, x, y=None) -> int:
        """Return the nearest text boundary for a page-space x coordinate."""
        scale = self.page._app.renderer.scale if self.page else 1.0
        family, vsize, _ = self._style()
        viewport_x, viewport_w = self._text_viewport()
        px = x - viewport_x + self._scroll_x
        if self.multiline:
            lines = self._display_lines(self._visible_text(), viewport_w, scale)
            lh = txt.line_height(vsize, scale=scale, family=family)
            row = max(0, min(len(lines) - 1, int(((y if y is not None else self._rect[1])
                                               - self._rect[1] - self._padding().top + self._scroll_y) / lh)))
            start, vis = lines[row]
        else:
            start, vis = 0, self._visible_text()
        px -= self._alignment_offset(vis, viewport_w, scale)
        acc, idx = 0.0, 0
        for i, ch in enumerate(vis):
            w = self._line_width(vis[:i + 1], vsize, scale=scale,
                               family=family) - acc
            if acc + w / 2 >= px:
                idx = i
                break
            acc += w
            idx = i + 1
        return start + idx

    def _selection(self):
        anchor = self._selection_anchor
        if anchor is None or anchor == self._caret:
            return None
        return (min(anchor, self._caret), max(anchor, self._caret))

    def _selected_text(self) -> str:
        selected = self._selection()
        return self.value[selected[0]:selected[1]] if selected else ""

    def _clear_selection(self):
        self._selection_anchor = None

    def _select_range(self, start: int, end: int):
        length = len(self.value)
        self._selection_anchor = max(0, min(length, start))
        self._caret = max(0, min(length, end))

    def _word_bounds(self, index: int):
        value = self.value
        if not value:
            return (0, 0)
        index = max(0, min(len(value) - 1, index))

        def char_class(char):
            if char.isalnum() or char == "_":
                return "word"
            if char.isspace():
                return "space"
            return "punctuation"

        kind = char_class(value[index])
        start, end = index, index + 1
        while start > 0 and char_class(value[start - 1]) == kind:
            start -= 1
        while end < len(value) and char_class(value[end]) == kind:
            end += 1
        return (start, end)

    def _line_bounds(self, index: int):
        index = max(0, min(len(self.value), index))
        start = self.value.rfind("\n", 0, index) + 1
        newline = self.value.find("\n", index)
        end = len(self.value) if newline < 0 else newline + 1
        return (start, end)

    def _pointer_down(self, x, _y, clicks=1):
        """Position or select text using desktop single/double/triple click."""
        if (self.password and self.can_reveal_password
                and x >= self._rect[0] + self._rect[2] - 48):
            self._selection_dragging = False
            return
        index = self._index_at(x, _y)
        clicks = max(1, int(clicks or 1)) if self.enable_interactive_selection else 1
        if clicks % 3 == 0:
            start, end = self._line_bounds(index)
            self._select_range(start, end)
            self._selection_drag_mode = "line"
        elif clicks % 3 == 2:
            word_index = min(index, max(0, len(self.value) - 1))
            start, end = self._word_bounds(word_index)
            self._select_range(start, end)
            self._selection_drag_mode = "word"
        else:
            self._caret = index
            self._clear_selection()
            start = end = index
            self._selection_drag_mode = "character"
        self._drag_selection_origin = (start, end)
        self._clear_composition(update=False)
        self._notify_selection()
        self._restart_cursor_blink()
        self._update_ime_rect()
        self.update()

    def _caret_at(self, x):
        """Compatibility hook: place the caret with a single click."""
        self._pointer_down(x, self._rect[1], 1)

    def _drag_start(self, x, _y):
        if not self.enable_interactive_selection:
            return
        if (self.password and self.can_reveal_password
                and x >= self._rect[0] + self._rect[2] - 48):
            self._selection_dragging = False
            return
        self._selection_dragging = True

    def _drag(self, x, _y):
        if not self._selection_dragging:
            return
        index = self._index_at(x, _y)
        start, end = self._drag_selection_origin
        if self._selection_drag_mode == "word":
            next_start, next_end = self._word_bounds(
                min(index, max(0, len(self.value) - 1)))
            if index < start:
                self._select_range(end, next_start)
            else:
                self._select_range(start, next_end)
        elif self._selection_drag_mode == "line":
            next_start, next_end = self._line_bounds(index)
            if index < start:
                self._select_range(end, next_start)
            else:
                self._select_range(start, next_end)
        else:
            self._selection_anchor = start
            self._caret = index
        self._notify_selection()
        self._restart_cursor_blink()
        self._update_ime_rect()
        self.update()

    def _drag_end(self):
        self._selection_dragging = False

    def _adornment_control(self, name):
        value = getattr(self, name)
        style = getattr(self, name + "_style", None)
        key = (id(value), repr(value) if not isinstance(value, Control) else None, repr(style))
        cached = self._adornments.get(name)
        if cached is None or cached[0] != key:
            control = _icon_control(value) if "icon" in name else _adornment(value, style, self.text_size)
            cached = self._adornments[name] = (key, control)
            if control is not None and self.page is not None:
                control._attach(self.page, self)
        return cached[1]

    def _adornment_width(self, name):
        control = self._adornment_control(name)
        if control is None:
            return 0.0
        scale = self.page._app.renderer.scale if self.page else 1.0
        return control._intrinsic(self._rect[2], self._field_height(), scale)[0] + 8.0

    def _text_viewport(self):
        """Return the horizontal content viewport, excluding adornments."""
        x, _y, w, _h = self._rect
        p = self._padding()
        leading = sum(self._adornment_width(name) for name in ("icon", "prefix_icon", "prefix"))
        trailing = sum(self._adornment_width(name) for name in ("suffix", "suffix_icon"))
        trailing += 36.0 if self.password and self.can_reveal_password else 0.0
        return x + p.left + leading, max(0.0, w - p.left - p.right - leading - trailing)

    def _alignment_offset(self, value, width, scale):
        family, size, _ = self._style()
        content_width = self._line_width(value, size, scale=scale, family=family)
        align = _enum_value(self.text_align)
        if content_width < width:
            if align == "center":
                return (width - content_width) / 2
            if align in ("end", "right"):
                return width - content_width
        return 0.0

    def _display_lines(self, value, width, scale):
        family, size, _ = self._style()
        key = (value, width, scale, family, size, repr(self.text_style), txt.font_revision)
        if self._multiline_cache is not None and self._multiline_cache[0] == key:
            return self._multiline_cache[1]
        lines, start = [], 0
        for paragraph in value.split("\n"):
            if not paragraph:
                lines.append((start, ""))
            while paragraph:
                lo, hi = 1, len(paragraph)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if self._line_width(paragraph[:mid], size, scale=scale, family=family) <= width:
                        lo = mid
                    else:
                        hi = mid - 1
                cut = lo
                if cut < len(paragraph):
                    space = paragraph.rfind(" ", 0, cut + 1)
                    if space > 0:
                        cut = space + 1
                lines.append((start, paragraph[:cut]))
                start += cut
                paragraph = paragraph[cut:]
            start += 1
        self._multiline_cache = (key, lines)
        return lines

    def _draw_adornments(self, r, x, y, w, h):
        p = self._padding()
        left = x + p.left
        for name in ("icon", "prefix_icon", "prefix"):
            control = self._adornment_control(name)
            if control is None:
                continue
            cw, ch = control._intrinsic(w, h, r.scale)
            control._place(left, y + (h - ch) / 2, cw, ch, r.scale)
            control._draw_all(r)
            left += cw + 8
        right = x + w - p.right - (36 if self.password and self.can_reveal_password else 0)
        for name in ("suffix_icon", "suffix"):
            control = self._adornment_control(name)
            if control is None:
                continue
            cw, ch = control._intrinsic(w, h, r.scale)
            control._place(right - cw, y + (h - ch) / 2, cw, ch, r.scale)
            control._draw_all(r)
            right -= cw + 8
        support = self.error if self.error is not None else self.helper
        style = self.error_style if self.error is not None else self.helper_style
        if support is not None:
            control = _adornment(support, style, 12)
            if self.error is not None and isinstance(control, Text) and getattr(style, "color", None) is None:
                control.color = colors.Colors.ERROR
            cw, ch = control._intrinsic(w - p.left - p.right, 22, r.scale)
            control._place(x + p.left, y + h + 4, cw, ch, r.scale)
            control._draw_all(r)
        if self.counter is not None:
            control = _adornment(self.counter, self.counter_style, 12)
            cw, ch = control._intrinsic(w, 22, r.scale)
            control._place(x + w - p.right - cw, y + h + 4, cw, ch, r.scale)
            control._draw_all(r)

    def _sync_horizontal_scroll(self, scale):
        """Keep the active caret visible inside a single-line field."""
        if self.multiline:
            self._scroll_x = 0.0
            return
        family, vsize, _ = self._style()
        shown = self._visible_text()
        composition = self._visible_composition()
        ime_cursor = min(len(composition),
                         self._composition_start + self._composition_length)
        caret_text = shown[:self._caret] + composition[:ime_cursor]
        displayed = shown[:self._caret] + composition + shown[self._caret:]
        caret_x = self._line_width(
            caret_text, vsize, scale=scale, family=family)
        content_w = self._line_width(
            displayed, vsize, scale=scale, family=family)
        _left, viewport_w = self._text_viewport()
        if viewport_w <= 0:
            self._scroll_x = 0.0
            return
        max_scroll = max(0.0, content_w + 2.0 - viewport_w)
        if not self._focused:
            # Keep the current view on blur; a freshly created field starts
            # at the beginning until its caret actually receives focus.
            self._scroll_x = max(0.0, min(self._scroll_x, max_scroll))
            return
        if caret_x < self._scroll_x:
            self._scroll_x = caret_x
        elif caret_x + 2.0 > self._scroll_x + viewport_w:
            self._scroll_x = caret_x + 2.0 - viewport_w
        self._scroll_x = max(0.0, min(self._scroll_x, max_scroll))

    # -- editing ----------------------------------------------------------------
    def _changed(self):
        self._last_value = self.value
        self._animate_internal(
            "_label_progress", 1.0 if self._focused or bool(self.value) else 0.0,
            _FIELD_TRANSITION_MS, _FIELD_TRANSITION_CURVE)
        self._restart_cursor_blink()
        self._update_ime_rect()
        self.update()
        self._notify_selection()
        fire(self, "change", self.value)

    def _delete_selection(self) -> bool:
        selected = self._selection()
        if selected is None:
            return False
        start, end = selected
        self.value = self.value[:start] + self.value[end:]
        self._caret = start
        self._clear_selection()
        return True

    def _replace_selection(self, value: str):
        value = _filtered(value, self.input_filter)
        capitalization = _enum_value(self.capitalization)
        if capitalization == "characters":
            value = value.upper()
        elif capitalization == "words":
            before = self.value[:self._caret]
            value = "".join(ch.upper() if i == 0 and (not before or before[-1].isspace()) or i > 0 and value[i - 1].isspace() else ch
                            for i, ch in enumerate(value))
        elif capitalization == "sentences":
            before = self.value[:self._caret].rstrip()
            if not before or before[-1] in ".!?":
                value = value[:1].upper() + value[1:]
            value = re.sub(r"([.!?]\s+)(\w)", lambda m: m[1] + m[2].upper(), value)
        selected = self._selection()
        start, end = selected if selected is not None else (
            self._caret, self._caret)
        if self.max_length is not None and self.max_length >= 0:
            available = max(0, self.max_length - (len(self.value) - (end - start)))
            value = value[:available]
        next_value = self.value[:start] + value + self.value[end:]
        if next_value == self.value:
            if selected is not None:
                self._caret = start + len(value)
                self._clear_selection()
            return False
        self.value = next_value
        self._caret = start + len(value)
        self._clear_selection()
        return True

    def _previous_word_boundary(self, index: int) -> int:
        value = self.value
        index = max(0, min(len(value), index))
        while index > 0 and value[index - 1].isspace():
            index -= 1
        if index > 0:
            index = self._word_bounds(index - 1)[0]
        return index

    def _next_word_boundary(self, index: int) -> int:
        value = self.value
        index = max(0, min(len(value), index))
        while index < len(value) and value[index].isspace():
            index += 1
        if index < len(value):
            index = self._word_bounds(index)[1]
        return index

    def _move_caret(self, target: int, *, extend: bool):
        target = max(0, min(len(self.value), target))
        if extend:
            if self._selection_anchor is None:
                self._selection_anchor = self._caret
        else:
            self._clear_selection()
        self._caret = target
        self._notify_selection()
        self._restart_cursor_blink()
        self.update()

    def _text_input(self, t):
        if self.read_only or _enum_value(self.keyboard_type) == "none":
            return
        if not self.multiline:
            t = t.replace("\n", "").replace("\r", "")
        self._clear_composition(update=False)
        if self._replace_selection(t):
            self._update_ime_rect()
            self._changed()

    def _text_editing(self, text: str, start: int = 0, length: int = 0):
        """Update SDL IME preedit state without committing it to ``value``."""
        if self.read_only:
            return
        self._composition = text or ""
        self._composition_start = max(0, min(len(self._composition), int(start)))
        self._composition_length = max(
            0, min(len(self._composition) - self._composition_start,
                   int(length)))
        self._restart_cursor_blink()
        self._update_ime_rect()
        self.update()

    def _clear_composition(self, *, update=True):
        changed = bool(self._composition)
        self._composition = ""
        self._composition_start = 0
        self._composition_length = 0
        if changed and update:
            self.update()

    def _update_ime_rect(self):
        if not self._focused or self.page is None:
            return
        scale = self.page._app.renderer.scale
        family, vsize, _ = self._style()
        self._sync_horizontal_scroll(scale)
        shown = self._visible_text()
        prefix = shown[:self._caret]
        composition = self._visible_composition()
        ime_cursor = min(len(composition),
                         self._composition_start + self._composition_length)
        caret_text = prefix + composition[:ime_cursor]
        text_left, viewport_w = self._text_viewport()
        text_left += self._paint_offset[0]
        cx = text_left - self._scroll_x + self._alignment_offset(shown, viewport_w, scale) + self._line_width(
            caret_text, vsize, scale=scale, family=family)
        cx = max(text_left, min(text_left + viewport_w, cx))
        text_y = (self._rect[1] + self._paint_offset[1]
                  + (self._rect[3] - vsize) / 2)
        if self.filled and self.label and not isinstance(self.border, OutlineInputBorder):
            text_y += 8 * self._label_progress
        if self.multiline:
            lines = self._display_lines(shown, viewport_w, scale)
            row = max(i for i, (start, line) in enumerate(lines) if start <= self._caret)
            start, line = lines[row]
            cx = text_left + self._alignment_offset(line, viewport_w, scale) + self._line_width(
                line[:self._caret - start], vsize, scale=scale, family=family)
            text_y = (self._rect[1] + self._paint_offset[1] + self._padding().top
                      + row * txt.line_height(vsize, scale=scale, family=family) - self._scroll_y)
        # SDL's Windows backend treats this as both the current composition
        # point and an exclusion area. Start at the visual caret but extend to
        # the field bottom so the candidate UI sits below, never over the next
        # line or control.
        anchor_x = cx + _IME_OFFSET_X
        anchor_y = text_y + _IME_OFFSET_Y
        field_bottom = (self._rect[1] + self._paint_offset[1]
                        + self._rect[3] + _IME_OFFSET_Y)
        px, py = self._paint_offset
        screen_x, screen_y = self._screen_point(anchor_x - px, anchor_y - py)
        bottom_x, bottom_y = self._screen_point(anchor_x + 1 - px, field_bottom - py)
        rect = pygame.Rect(round(min(screen_x, bottom_x)), round(min(screen_y, bottom_y)),
                           max(1, round(abs(bottom_x - screen_x))),
                           max(1, round(abs(bottom_y - screen_y))))
        if rect != self._last_ime_rect:
            self.page._app.set_text_input_rect(rect)
            self._last_ime_rect = rect

    def _key(self, e):
        k = e.key
        modifiers = getattr(e, "mod", 0)
        shortcut = bool(modifiers & (pygame.KMOD_CTRL | pygame.KMOD_META))
        extend = bool(modifiers & pygame.KMOD_SHIFT) and self.enable_interactive_selection

        if shortcut and k == pygame.K_a and self.enable_interactive_selection:
            self._clear_composition(update=False)
            self._select_range(0, len(self.value))
            self._notify_selection()
            self._restart_cursor_blink()
            self._update_ime_rect()
            self.update()
            return
        if shortcut and k == pygame.K_c:
            selected = self._selected_text()
            if selected:
                _clipboard_copy(selected)
            return
        if shortcut and k == pygame.K_x:
            if not self.read_only:
                selected = self._selected_text()
                if selected and _clipboard_copy(selected):
                    self._delete_selection()
                    self._changed()
            return
        if shortcut and k == pygame.K_v:
            if not self.read_only:
                pasted = _clipboard_paste()
                if pasted is not None:
                    pasted = pasted.replace("\r\n", "\n").replace("\r", "\n")
                    if not self.multiline:
                        pasted = pasted.replace("\n", "")
                    self._clear_composition(update=False)
                    if self._replace_selection(pasted):
                        self._changed()
            return
        if self._composition:
            # The platform IME owns editing/navigation keys until it emits a
            # TEXTINPUT commit or clears the TEXTEDITING preedit string.
            return
        v, c = self.value, self._caret
        if k == pygame.K_BACKSPACE and not self.read_only:
            if self._delete_selection():
                self._changed()
            elif c > 0:
                start = self._previous_word_boundary(c) if shortcut else c - 1
                self.value, self._caret = v[:start] + v[c:], start
                self._changed()
        elif k == pygame.K_DELETE and not self.read_only:
            if self._delete_selection():
                self._changed()
            elif c < len(v):
                end = self._next_word_boundary(c) if shortcut else c + 1
                self.value = v[:c] + v[end:]
                self._changed()
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.multiline and not self.read_only and (
                    not self.shift_enter or extend):
                if self._replace_selection("\n"):
                    self._changed()
            else:
                fire(self, "submit", self.value)
        elif k == pygame.K_LEFT:
            selected = self._selection()
            if selected and not extend and not shortcut:
                target = selected[0]
            else:
                target = (self._previous_word_boundary(c) if shortcut
                          else c - 1)
            self._move_caret(target, extend=extend)
        elif k == pygame.K_RIGHT:
            selected = self._selection()
            if selected and not extend and not shortcut:
                target = selected[1]
            else:
                target = (self._next_word_boundary(c) if shortcut
                          else c + 1)
            self._move_caret(target, extend=extend)
        elif k in (pygame.K_UP, pygame.K_DOWN) and self.multiline and not self.ignore_up_down_keys:
            scale = self.page._app.renderer.scale if self.page else 1.0
            _, width = self._text_viewport()
            lines = self._display_lines(self.value, width, scale)
            row = max(i for i, (start, line) in enumerate(lines) if start <= c)
            column = c - lines[row][0]
            target_row = max(0, min(len(lines) - 1, row + (-1 if k == pygame.K_UP else 1)))
            target_start, target_line = lines[target_row]
            self._move_caret(target_start + min(column, len(target_line)), extend=extend)
        elif k == pygame.K_HOME:
            target = (0 if shortcut or not self.multiline
                      else self._line_bounds(c)[0])
            self._move_caret(target, extend=extend)
        elif k == pygame.K_END:
            target = (len(v) if shortcut or not self.multiline
                      else self._line_bounds(c)[1])
            self._move_caret(target, extend=extend)
        self._update_ime_rect()

    # -- drawing ------------------------------------------------------------------
    def _draw(self, r, x, y):
        rx, ry, w, h = self._rect
        h = self._field_height()
        self._paint_offset = (x - rx, y - ry)
        scale = r.scale
        border = _state_value(self, self.border)
        outline = border if isinstance(border, OutlineInputBorder) or type(border).__name__ == "OutlineInputBorder" else None
        no_border = type(border).__name__ == "NoInputBorder" or _enum_value(border) == "none"
        underline = type(border).__name__ == "UnderlineInputBorder" or _enum_value(border) == "underline"
        filled_style = (self.filled and outline is None) or underline
        radius_value = getattr(border, "border_radius", self.border_radius)
        radius = as_border_radius(
            _RADIUS if radius_value is None else radius_value).top_left
        focus = self._focus_progress
        hover = self._hover_progress
        if self.filled or self.bgcolor is not None or self.fill_color is not None or self.focused_bgcolor is not None or self.focus_color is not None:
            resting_bg = self.fill_color or self.bgcolor or colors.Colors.SURFACE_CONTAINER_HIGHEST
            field_bg = _mix(resting_bg, self.focused_bgcolor or self.focus_color or resting_bg, focus)
            if hover:
                field_bg = _mix(field_bg, self.hover_color or colors.Colors.ON_SURFACE,
                                0.04 * hover)
            if filled_style:
                r.clip_push(x, y, w, h / 2)
                r.fill_rect(x, y, w, h, field_bg, radius=radius)
                r.clip_pop()
                r.clip_push(x, y + h / 2, w, h / 2)
                r.fill_rect(x, y, w, h, field_bg)
                r.clip_pop()
            else:
                r.fill_rect(x, y, w, h, field_bg, radius=radius)
        border_width = 0.0
        border_draw_color = None
        if hasattr(border, "side"):
            side = border.side
            if side.width > 0:
                border_color = side.color
                if border_color is None:
                    inactive = _mix(colors.Colors.OUTLINE,
                                    colors.Colors.ON_SURFACE, 0.25 * hover)
                    border_color = _mix(inactive, colors.Colors.PRIMARY, focus)
                border_draw_color = _parse(
                    border_color or colors.Colors.OUTLINE)
                border_width = side.width + focus
        elif self.border_color is not None:
            border_draw_color = _parse(self.border_color)
            border_width = 1 + focus
        else:
            inactive = _mix(colors.Colors.OUTLINE,
                            colors.Colors.ON_SURFACE, 0.25 * hover)
            border_draw_color = _mix(
                inactive, colors.Colors.PRIMARY, focus)
            border_width = 1 + focus
        if self.border_width is not None:
            border_width = self.border_width
        if self.focused_border_width is not None:
            border_width += (self.focused_border_width - border_width) * focus
        if self.focused_border_color is not None:
            border_draw_color = _mix(border_draw_color or colors.Colors.OUTLINE, self.focused_border_color, focus)
        if self.error is not None:
            border_draw_color = _parse(colors.Colors.ERROR)
        if no_border:
            border_width = 0.0
        label_progress = max(0.0, min(1.0, self._label_progress)) if self.label else 0.0
        family, vsize, vcolor = self._style()
        if self.label and not isinstance(self.label, Control):
            inactive_color = _parse(getattr(self.label_style, "color", None) or colors.Colors.ON_SURFACE_VARIANT)
            active_color = _parse(getattr(self.label_style, "color", None) or colors.Colors.PRIMARY)
            label_size = getattr(self.label_style, "size", None) or vsize
            label_family = getattr(self.label_style, "font_family", None) or family
            floating_size = label_size * .75 if getattr(self.label_style, "size", None) else 12.0
            inline_label = self._render_cached(
                "label-inline", self.label, label_size, scale, label_family, inactive_color)
            floating_inactive = self._render_cached(
                "label-floating-inactive", self.label, floating_size, scale, label_family, inactive_color)
            floating_active = self._render_cached(
                "label-floating-active", self.label, floating_size, scale, label_family, active_color)
            inline_width = inline_label.get_width() / scale
            inline_height = inline_label.get_height() / scale
            floating_width = floating_active.get_width() / scale
            floating_height = floating_active.get_height() / scale
            draw_width = inline_width + (floating_width - inline_width) * label_progress
            draw_height = inline_height + (floating_height - inline_height) * label_progress
            label_line_height = 24.0 + (16.0 - 24.0) * label_progress
        if border_width > 0:
            if filled_style:
                r.fill_rect(x, y + h - border_width, w, border_width,
                            border_draw_color)
            else:
                if self.label and not isinstance(self.label, Control) and draw_width > 0 and label_progress > 0:
                    # The cutout grows with the current label's width AND line
                    # height, using the same progress as its size and position.
                    gap = draw_width * label_progress + 8.0
                    draw_notched_outline(r, (x, y, w, h), border_draw_color,
                                         border_width, radius, _FIELD_PAD - 4, gap,
                                         depth=label_line_height * label_progress / 2)
                else:
                    r.stroke_rect(x, y, w, h, border_draw_color,
                                  width=border_width, radius=radius)
        content_pad = self._padding()
        ty, th = y + content_pad.top, max(vsize, h - content_pad.top - content_pad.bottom)
        if filled_style and self.label:
            ty += 16 * label_progress
            th -= 16 * label_progress
        vertical = _enum_value(self.text_vertical_align)
        if vertical in ("top", "start") or vertical == -1:
            ty = y + self._padding().top
            th = vsize
        elif vertical in ("bottom", "end") or vertical == 1:
            ty = y + h - self._padding().bottom - vsize
            th = vsize
        elif isinstance(vertical, (int, float)):
            ty += (th - vsize) * max(-1, min(1, vertical)) / 2
        if isinstance(self.label, Control):
            cw, ch = self.label._intrinsic(w - 32, h, scale)
            self.label._place(x + self._padding().left, y - ch / 2 if label_progress else y + (h - ch) / 2, cw, ch, scale)
            self.label._draw_all(r)
        elif self.label:
            if label_progress <= 0.0 or floating_width <= 0.0:
                inline_y = y + (h - inline_label.get_height() / scale) / 2
                r.blit_cached(inline_label, x + _FIELD_PAD, inline_y)
            else:
                # Scale cached label rasters, keeping placement and cutout on
                # the same geometry rather than on the focus target state.
                if filled_style:
                    resting_y = y + (h - inline_height) / 2
                    draw_y = resting_y + (y + 8 - resting_y) * label_progress
                else:
                    draw_y = y + h / 2 * (1 - label_progress) - draw_height / 2
                r.blit_scaled(
                    floating_inactive, x + _FIELD_PAD, draw_y,
                    draw_width, draw_height, alpha=1.0 - focus)
                r.blit_scaled(
                    floating_active, x + _FIELD_PAD, draw_y,
                    draw_width, draw_height, alpha=focus)
        shown = self._visible_text()
        composition = self._visible_composition()
        prefix, suffix = shown[:self._caret], shown[self._caret:]
        displayed = prefix + composition + suffix
        self._sync_horizontal_scroll(scale)
        text_left, viewport_w = self._text_viewport()
        text_left += self._paint_offset[0]
        draw_x = text_left - self._scroll_x + self._alignment_offset(displayed, viewport_w, scale)
        hint_progress = (1.0 if not self.label else max(0.0, min(1.0, (min(label_progress, focus) - 4 / 9) / (5 / 9)))) if not displayed else 0.0
        if self.multiline:
            self._draw_multiline(r, displayed, text_left, viewport_w, y, h)
        elif displayed:
            surf = self._render_cached(
                "value", displayed, vsize, scale, family, _parse(vcolor))
            text_y = (ty + (th - surf.get_height() / scale) / 2
                      + _text_ink_offset(family, vsize, scale))
            r.clip_push(text_left, y, viewport_w, h)
            selected = self._selection()
            if selected is not None and not composition:
                start, end = selected
                selected_x = draw_x + self._line_width(
                    shown[:start], vsize, scale=scale, family=family)
                selected_w = self._line_width(
                    shown[start:end], vsize, scale=scale, family=family)
                r.fill_rect(
                    selected_x, text_y, max(1.0, selected_w),
                    surf.get_height() / scale,
                    _parse(self.selection_color or colors.with_opacity(0.36, colors.Colors.PRIMARY)),
                    radius=2)
            r.blit_cached(surf, draw_x, text_y)
            if composition:
                comp_x = draw_x + self._line_width(
                    prefix, vsize, scale=scale, family=family)
                comp_w = self._line_width(
                    composition, vsize, scale=scale, family=family)
                underline_y = min(y + h - 2,
                                  text_y + surf.get_height() / scale)
                r.fill_rect(comp_x, underline_y, max(1, comp_w), 1,
                            _parse(colors.Colors.ON_SURFACE_VARIANT))
                if self._composition_length:
                    selected = composition[
                        self._composition_start:
                        self._composition_start + self._composition_length]
                    selected_x = comp_x + self._line_width(
                        composition[:self._composition_start], vsize,
                        scale=scale, family=family)
                    selected_w = self._line_width(
                        selected, vsize, scale=scale, family=family)
                    r.fill_rect(selected_x, underline_y - 1,
                                max(1, selected_w), 2,
                                _parse(colors.Colors.PRIMARY))
            r.clip_pop()
        else:
            # Material's content reveal starts after 4/9 of the 150ms field
            # transition and occupies the remaining 5/9.
            hint_progress = (1.0 if not self.label else max(
                0.0, min(1.0, (min(label_progress, focus) - 4 / 9) / (5 / 9))))
        if not displayed and self.hint_text and hint_progress > 0.0:
            surf = self._render_cached(
                "hint", self.hint_text, getattr(self.hint_style, "size", None) or self.text_size, scale, getattr(self.hint_style, "font_family", None) or family,
                _parse(getattr(self.hint_style, "color", None) or colors.Colors.ON_SURFACE_VARIANT))
            r.clip_push(text_left, y, viewport_w, h)
            r.blit_cached(surf, text_left,
                   ty + (th - surf.get_height() / scale) / 2
                   + _text_ink_offset(family, self.text_size, scale),
                   alpha=hint_progress)
            r.clip_pop()
        if self.password and self.can_reveal_password:
            icon = Icons.VISIBILITY_OFF if self._password_revealed else Icons.VISIBILITY
            af = get_icon_font(round(24 * scale))
            eye = af.render(chr(int(icon)), True,
                            _parse(colors.Colors.ON_SURFACE_VARIANT))
            r.blit(eye, x + w - 32,
                   y + (h - eye.get_height() / scale) / 2)
        self._draw_adornments(r, x, y, w, h)
        if self._focused and self._cursor_visible and self.show_cursor and not self.multiline:
            ime_cursor = min(len(composition),
                             self._composition_start + self._composition_length)
            caret_text = prefix + composition[:ime_cursor]
            cx = draw_x + self._line_width(
                caret_text, vsize, scale=scale, family=family)
            r.clip_push(text_left, y, viewport_w, h)
            cursor_h = self.cursor_height or vsize
            r.fill_rect(cx, ty + (th - cursor_h) / 2, self.cursor_width, cursor_h,
                        _parse((self.cursor_error_color if self.error is not None else self.cursor_color) or colors.Colors.PRIMARY),
                        radius=self.cursor_radius or 0)
            r.clip_pop()
            self._update_ime_rect()


    def _draw_multiline(self, r, value, left, width, y, height):
        family, size, color = self._style()
        lh = txt.line_height(size, scale=r.scale, family=family)
        lines = self._display_lines(value, width, r.scale)
        caret = self._caret + min(len(self._composition), self._composition_start + self._composition_length)
        row = 0
        for i, (start, line) in enumerate(lines):
            if start <= caret:
                row = i
        visible_rows = max(1, int((height - self._padding().top - self._padding().bottom) / lh))
        scroll_rows = max(0, row - visible_rows + 1) if self._focused else 0
        self._scroll_y = scroll_rows * lh
        text_y = y + self._padding().top - self._scroll_y
        r.clip_push(left, y, width, height)
        selection = self._selection()
        for i, (start, line) in enumerate(lines):
            cy = text_y + i * lh
            ox = self._alignment_offset(line, width, r.scale)
            surf = self._render_cached("multiline", line, size, r.scale, family, color)
            if selection is not None:
                a, b = max(0, selection[0] - start), min(len(line), selection[1] - start)
                if b > a:
                    sx = self._line_width(line[:a], size, scale=r.scale, family=family)
                    sw = self._line_width(line[a:b], size, scale=r.scale, family=family)
                    r.fill_rect(left + ox + sx, cy, sw, lh,
                                _parse(self.selection_color or colors.with_opacity(.36, colors.Colors.PRIMARY)))
            r.blit_cached(surf, left + ox, cy)
            if i == row and self._focused and self._cursor_visible and self.show_cursor:
                cx = self._line_width(line[:max(0, caret - start)], size, scale=r.scale, family=family)
                ch = self.cursor_height or size
                r.fill_rect(left + ox + cx, cy + (lh - ch) / 2,
                            self.cursor_width, ch, _parse(self.cursor_color or colors.Colors.PRIMARY),
                            radius=self.cursor_radius or 0)
        r.clip_pop()


class _Toggle(Control):
    """Shared click-to-toggle plumbing for Checkbox/Switch."""

    def __init__(self, label: str = "", *, value=False, active_color=None,
                 label_position=LabelPosition.RIGHT, label_style=None,
                 autofocus=False, on_focus=None, on_blur=None,
                 overlay_color=None, hover_color=None, focus_color=None,
                 splash_radius=None, on_change=None, **base):
        super().__init__(**base)
        self.label = label
        self.value = bool(value)
        self.active_color = active_color
        self.label_position = label_position
        self.label_style = label_style
        self.autofocus = autofocus
        self.on_focus, self.on_blur = on_focus, on_blur
        self.overlay_color, self.hover_color, self.focus_color = overlay_color, hover_color, focus_color
        self.splash_radius = splash_radius
        self._focusable, self._focused = True, False
        self.on_change = on_change
        self.on_click = self._toggle  # internal routing
        self._hovered = False
        self._pressed = False
        self._value_progress = 1.0 if self.value else 0.0
        self._last_value = self.value
        init_state_layer(self)

    def _toggle(self, e=None):
        self.value = not self.value
        self._last_value = self.value
        self._animate_value(self.value)
        self.update()
        fire(self, "change", "true" if self.value else "false")

    def _key(self, event):
        if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._toggle()

    def _children(self):
        return [self.label] if isinstance(self.label, Control) else []

    def _label_measure(self, scale):
        if not self.label:
            return 0.0, 0.0
        if isinstance(self.label, Control):
            return self.label._intrinsic(None, None, scale)
        size, family, color = _style_values(self.label_style)
        return txt.measure(self.label, size, scale=scale, family=family)

    def _draw_label(self, r, x, cy):
        if isinstance(self.label, Control):
            w, h = self._label_measure(r.scale)
            self.label._place(x, cy - h / 2, w, h, r.scale)
            self.label._draw_all(r)
        elif self.label:
            size, family, color = _style_values(self.label_style)
            surf = txt.render_line_cached(self.label, size, scale=r.scale,
                                          family=family, color=_parse(color))
            r.blit_cached(surf, x, cy - surf.get_height() / (2 * r.scale))

    def _state_color(self, fallback):
        value = _state_value(self, self.overlay_color)
        if value is None:
            value = (self.focus_color if self._focused else self.hover_color if self._hovered else None)
        return value or fallback

    def _animate_value(self, selected: bool):
        self._animate_internal(
            "_value_progress", 1.0 if selected else 0.0,
            motion.MEDIUM3 if selected else motion.SHORT3,
            motion.EMPHASIZED_DECELERATE if selected
            else motion.EMPHASIZED_ACCELERATE)

    def _prepare_animations(self, now: float):
        super()._prepare_animations(now)
        selected = bool(self.value)
        if selected != self._last_value:
            self._last_value = selected
            self._animate_value(selected)

    def _draw_all(self, r, ox=0.0, oy=0.0):
        if self.visible:
            self._effects_begin(r, ox, oy)
            try:
                self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
            finally:
                self._effects_end(r)

    def _intrinsic(self, max_w, max_h, scale):
        box = self._box_size()
        lw, lh = self._label_measure(scale)
        gap = 8.0 if self.label else 0.0
        w = box + gap + lw
        h = max(box, lh)
        return (self._width if self._width is not None else w,
                self._height if self._height is not None else h)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _box_size(self) -> float:  # noqa: ANN201
        raise NotImplementedError

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        p = as_padding(getattr(self, "padding", None) or 0)
        x, y, w, h = x + p.left, y + p.top, w - p.left - p.right, h - p.top - p.bottom
        box = self._box_size()
        cy = y + h / 2
        first_is_box = _enum_value(self.label_position) != "left"
        bw = box
        lw = (w - bw - 8) if self.label else 0.0
        bx = x if first_is_box else x + lw + 8
        lx = x + bw + 8 if first_is_box else x
        self._draw_state(r, bx, cy, box)
        self._draw_box(r, bx, cy - box / 2, box)
        if self.label:
            self._draw_label(r, lx, cy)

    def _hit_test(self, x, y):
        x, y = self._hit_point(x, y)
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _draw_state(self, r, bx, cy, box):
        size = 2 * self.splash_radius if self.splash_radius is not None else 40.0
        state_color = (self.active_color or colors.Colors.PRIMARY
                       if self.value else colors.Colors.ON_SURFACE)
        if self._focused:
            r.fill_rect(bx + box / 2 - size / 2, cy - size / 2, size, size,
                        _parse(colors.with_opacity(.12, self._state_color(state_color))), radius=size / 2)
        draw_state_layer(self, r,
                         (bx + box / 2 - size / 2, cy - size / 2,
                          size, size), self._state_color(state_color), size / 2)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        self.update()

    def _pressed_hook(self, x, y):
        press(self, x, y)

    def _released_hook(self, _x, _y):
        release(self)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        return super()._tick_animations(now) or waiting


class Checkbox(_Toggle):
    __unsupported_parameters__ = {"shape", "visual_density"}

    def __init__(self, label="", *, value=False, label_position=LabelPosition.RIGHT,
                 label_style=None, tristate=False, autofocus=False, fill_color=None,
                 overlay_color=None, check_color=None, active_color=None,
                 hover_color=None, focus_color=None, splash_radius=None,
                 border_side=None, error=False, shape=None, visual_density=None,
                 on_change=None, on_focus=None, on_blur=None, **base):
        if shape is not None or visual_density is not None:
            raise NotImplementedError("Checkbox shape and visual_density are not supported")
        if value is None and not tristate:
            raise ValueError("Checkbox value=None requires tristate=True")
        super().__init__(label, value=value, label_position=label_position,
                         label_style=label_style, autofocus=autofocus,
                         active_color=active_color, overlay_color=overlay_color,
                         hover_color=hover_color, focus_color=focus_color,
                         splash_radius=splash_radius, on_change=on_change,
                         on_focus=on_focus, on_blur=on_blur, **base)
        self.tristate = tristate
        self.value = value
        self.fill_color, self.check_color = fill_color, check_color
        self.border_side, self.error = border_side, error
        self._value_progress = 1.0 if value or value is None else 0.0

    def _toggle(self, e=None):
        self.value = (True if self.value is False else None if self.value is True else False) if self.tristate else not self.value
        self._last_value = self.value
        self._animate_value(self.value is not False)
        self.update()
        fire(self, "change", "null" if self.value is None else "true" if self.value else "false")

    def _prepare_animations(self, now):
        Control._prepare_animations(self, now)
        if self.value != self._last_value:
            self._last_value = self.value
            self._animate_value(self.value is not False)

    def _box_size(self):
        return 18.0

    def _draw_box(self, r, x, y, box):
        progress = self._value_progress
        unselected_fill = _state_value(self, self.fill_color)
        if progress < 1 and unselected_fill is not None:
            r.fill_rect(x, y, box, box, _parse(unselected_fill), radius=2)
        if progress > 0:
            selected_box = box * (0.6 + 0.4 * progress)
            selected_x = x + (box - selected_box) / 2
            selected_y = y + (box - selected_box) / 2
            r.opacity_push(min(1.0, progress * 3.0))
            r.fill_rect(selected_x, selected_y, selected_box, selected_box,
                        _parse(_state_value(self, self.fill_color, self.active_color or (colors.Colors.ERROR if self.error else colors.Colors.PRIMARY))), radius=2)
            f = get_icon_font(round(14 * r.scale))
            surf = f.render(chr(int(Icons.REMOVE if self.value is None else Icons.CHECK)), True,
                            _parse(self.check_color or colors.Colors.ON_PRIMARY))
            icon_w = surf.get_width() / r.scale * (0.6 + 0.4 * progress)
            icon_h = surf.get_height() / r.scale * (0.6 + 0.4 * progress)
            r.blit_scaled(surf, x + (box - icon_w) / 2,
                          y + (box - icon_h) / 2, icon_w, icon_h)
            r.opacity_pop()
        if progress < 1:
            r.opacity_push(1 - progress)
            side = _state_value(self, self.border_side)
            r.stroke_rect(x, y, box, box,
                          _parse(getattr(side, "color", None) or (colors.Colors.ERROR if self.error else colors.Colors.ON_SURFACE_VARIANT)),
                          width=getattr(side, "width", 2), radius=2)
            r.opacity_pop()


class Switch(_Toggle):
    def __init__(self, label="", *, value=False, label_position=LabelPosition.RIGHT,
                 label_text_style=None, autofocus=False, active_color=None,
                 active_track_color=None, inactive_thumb_color=None,
                 inactive_track_color=None, thumb_color=None, thumb_icon=None,
                 track_color=None, track_outline_color=None, track_outline_width=None,
                 overlay_color=None, focus_color=None, hover_color=None,
                 splash_radius=None, padding=None, on_change=None, on_focus=None, on_blur=None,
                 **base):
        # label_style remains an existing Saturn convenience alias.
        label_style = base.pop("label_style", label_text_style)
        super().__init__(label, value=value, label_position=label_position,
                         label_style=label_style, autofocus=autofocus,
                         active_color=active_color, overlay_color=overlay_color,
                         hover_color=hover_color, focus_color=focus_color,
                         splash_radius=splash_radius, on_change=on_change,
                         on_focus=on_focus, on_blur=on_blur, **base)
        self.label_text_style = label_text_style
        self.padding = padding
        self.active_track_color, self.inactive_track_color = active_track_color, inactive_track_color
        self.inactive_thumb_color, self.thumb_color, self.thumb_icon = inactive_thumb_color, thumb_color, thumb_icon
        self.track_color, self.track_outline_color, self.track_outline_width = track_color, track_outline_color, track_outline_width
        initial = 1.0 if self.value else 0.0
        self._color_progress = initial
        self._size_progress = initial
        self._thumb_press_progress = 0.0
        self._switch_drag_start_x = 0.0
        self._switch_drag_start_progress = initial
        self._switch_dragged = False
        self._consume_click = False

    def _box_size(self):
        return 52.0  # Material 3 track width

    def _intrinsic(self, max_w, max_h, scale):
        lw, _ = self._label_measure(scale)
        p = as_padding(self.padding or 0)
        w = 52.0 + (8.0 + lw if self.label else 0.0) + p.left + p.right
        return (self._width if self._width is not None else w,
                self._height if self._height is not None else 40.0 + p.top + p.bottom)

    def _animate_value(self, selected: bool):
        target = 1.0 if selected else 0.0
        self._animate_internal("_value_progress", target, motion.MEDIUM2,
                               motion.SWITCH_OVERSHOOT)
        self._animate_internal("_color_progress", target, 67,
                               AnimationCurve.LINEAR)
        self._animate_internal("_size_progress", target, motion.MEDIUM1,
                               motion.STANDARD)

    def _drag_start(self, x, _y):
        self._switch_drag_start_x = x
        self._switch_drag_start_progress = float(self._value_progress)
        self._switch_dragged = False

    def _drag(self, x, _y):
        delta = x - self._switch_drag_start_x
        if abs(delta) < 2.0 and not self._switch_dragged:
            return
        self._switch_dragged = True
        progress = max(0.0, min(
            1.0, self._switch_drag_start_progress + delta / 20.0))
        self._animate_internal("_value_progress", progress, 0)
        self._animate_internal("_color_progress", progress, 0)
        self._animate_internal("_size_progress", progress, 0)
        self.update()

    def _drag_end(self):
        if not self._switch_dragged:
            return
        selected = self._value_progress >= 0.5
        changed = selected != self.value
        self.value = selected
        self._last_value = selected
        self._animate_value(selected)
        self._consume_click = True
        self._switch_dragged = False
        self.update()
        if changed:
            fire(self, "change", "true" if selected else "false")

    def _draw_box(self, r, x, y, w):
        h = 32.0
        track_y = y + (w - h) / 2
        progress = self._value_progress
        color_progress = self._color_progress
        size_progress = self._size_progress
        active = _parse(self.active_track_color or self.active_color or colors.Colors.PRIMARY)
        inactive = _parse(self.inactive_track_color or colors.Colors.SURFACE_CONTAINER_HIGHEST)
        track_c = tuple(round(a + (b - a) * color_progress)
                        for a, b in zip(inactive, active))
        track_c = _parse(_state_value(self, self.track_color, track_c))
        r.fill_rect(x, track_y, w, h, track_c, radius=h / 2)
        if color_progress < 1.0:
            r.opacity_push(1.0 - color_progress)
            r.stroke_rect(x, track_y, w, h,
                          _parse(_state_value(self, self.track_outline_color, colors.Colors.OUTLINE)), width=_state_value(self, self.track_outline_width, 2),
                          radius=h / 2)
            r.opacity_pop()
        thumb_r = 8.0 + 4.0 * size_progress
        # The Material switch snaps its handle to the 28px pressed size;
        # this is intentionally independent of the slower state-layer alpha.
        thumb_r += (14.0 - thumb_r) * self._thumb_press_progress
        tx = x + 16.0 + (w - 32.0) * progress
        on_thumb = _parse(self.active_color or colors.Colors.ON_PRIMARY)
        off_thumb = _parse(self.inactive_thumb_color or colors.Colors.OUTLINE)
        tc = tuple(round(a + (b - a) * color_progress)
                   for a, b in zip(off_thumb, on_thumb))
        tc = _parse(_state_value(self, self.thumb_color, tc))
        r.circle(tx, track_y + h / 2, thumb_r, tc)
        thumb_icon = _state_value(self, self.thumb_icon)
        if thumb_icon is not None:
            icon = txt.render_icon_cached(thumb_icon, round(16 * r.scale), _parse(colors.Colors.PRIMARY))
            r.blit_cached(icon, tx - icon.get_width() / (2 * r.scale),
                          track_y + h / 2 - icon.get_height() / (2 * r.scale))

    def _draw_state(self, r, bx, cy, box):
        size = 40.0
        tx = bx + 16.0 + (box - 32.0) * self._value_progress
        state_color = (self.active_color or colors.Colors.PRIMARY
                       if self.value else colors.Colors.ON_SURFACE)
        if self._focused:
            r.fill_rect(tx - size / 2, cy - size / 2, size, size,
                        _parse(colors.with_opacity(.12, self._state_color(state_color))), radius=size / 2)
        draw_state_layer(self, r, (tx - size / 2, cy - size / 2,
                                   size, size), self._state_color(state_color), size / 2)

    def _pressed_hook(self, x, y):
        press(self, x, y, ripple_duration=motion.SHORT4,
              press_duration=75)
        self._animate_internal("_thumb_press_progress", 1.0,
                               75, motion.STANDARD_ACCELERATE)

    def _released_hook(self, _x, _y):
        release(self, minimum_ms=0, fade_duration=motion.SHORT2)
        self._animate_internal("_thumb_press_progress", 0.0,
                               motion.SHORT2, motion.STANDARD_DECELERATE)


class RadioGroup(Control):
    def __init__(self, content=None, *, value=None, on_change=None, **base):
        super().__init__(**base)
        self.content = content
        self.value = value
        self._last_value = value
        self.on_change = on_change

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

    def _select(self, radio):
        self.value = None if radio.toggleable and self.value == radio.value else radio.value
        self._last_value = self.value
        for item in self._radios():
            item._set_selected(item.value == self.value)
        self.update()
        fire(self, "change", self.value)

    def _prepare_animations(self, now: float):
        super()._prepare_animations(now)
        if self.value != self._last_value:
            self._last_value = self.value
            for item in self._radios():
                item._set_selected(item.value == self.value)

    def _radios(self):
        stack = [self.content] if self.content is not None else []
        while stack:
            control = stack.pop()
            if isinstance(control, Radio):
                yield control
            stack.extend(control._children())

    def _draw(self, r, x, y):
        pass  # content draws itself


class Radio(Control):
    __unsupported_parameters__ = {"visual_density"}
    def __init__(self, value=None, *, label: str = "",
                 label_position=LabelPosition.RIGHT, label_style=None,
                 autofocus=False, active_color=None, fill_color=None,
                 overlay_color=None, hover_color=None, focus_color=None,
                 splash_radius=None, toggleable=False, visual_density=None,
                 on_focus=None, on_blur=None, **base):
        super().__init__(**base)
        self.value = value
        self.label = label
        self.label_position = label_position
        self.active_color = active_color
        if visual_density is not None:
            raise NotImplementedError("Radio visual_density is not supported")
        self.label_style, self.autofocus = label_style, autofocus
        self.fill_color, self.overlay_color = fill_color, overlay_color
        self.hover_color, self.focus_color = hover_color, focus_color
        self.splash_radius, self.toggleable = splash_radius, toggleable
        self.on_focus, self.on_blur = on_focus, on_blur
        self._focusable, self._focused = True, False
        self.on_click = self._pick  # internal routing
        self._hovered = False
        self._pressed = False
        self._selection_progress = 0.0
        self._selection_initialized = False
        init_state_layer(self)

    def _pick(self, e=None):
        g = self.parent
        while g is not None and not isinstance(g, RadioGroup):
            g = g.parent
        if g is not None:
            g._select(self)

    def _key(self, event):
        if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._pick()
        elif event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN):
            group = self.parent
            while group is not None and not isinstance(group, RadioGroup):
                group = group.parent
            if group is not None:
                items = [item for item in reversed(list(group._radios())) if item.visible and not item.disabled]
                if self in items:
                    target = items[(items.index(self) + (-1 if event.key in (pygame.K_LEFT, pygame.K_UP) else 1)) % len(items)]
                    group._select(target)
                    if self.page is not None:
                        self.page.focus(target)

    def _intrinsic(self, max_w, max_h, scale):
        size, family, color = _style_values(self.label_style)
        lw, lh = txt.measure(self.label, size, scale=scale, family=family) if self.label else (0, 0)
        return (self._width or 20 + (8 + lw if self.label else 0),
                self._height or max(20, lh))

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        cy = y + h / 2
        selected = self._group_value() == self.value
        if not self._selection_initialized:
            self._selection_progress = 1.0 if selected else 0.0
            self._animation_targets["_selection_progress"] = \
                self._selection_progress
            self._selection_initialized = True
        progress = self._selection_progress
        active = _parse(_state_value(self, self.fill_color, self.active_color or colors.Colors.PRIMARY))
        inactive = _parse(colors.Colors.ON_SURFACE_VARIANT)
        outline = tuple(round(a + (b - a) * progress)
                        for a, b in zip(inactive, active))
        size, family, label_color = _style_values(self.label_style)
        label_w = txt.line_width(self.label, size, scale=r.scale, family=family) if self.label else 0
        left_label = _enum_value(self.label_position) == "left"
        bx = x + label_w + 8 if left_label else x
        lx = x if left_label else x + 28
        state_color = _state_value(self, self.overlay_color) or (self.focus_color if self._focused else self.hover_color if self._hovered else None)
        diameter = self.splash_radius * 2 if self.splash_radius else 40
        if self._focused:
            r.fill_rect(bx + 10 - diameter / 2, cy - diameter / 2, diameter, diameter,
                        _parse(colors.with_opacity(.12, state_color or active)), radius=diameter / 2)
        draw_state_layer(self, r, (bx + 10 - diameter / 2, cy - diameter / 2, diameter, diameter),
                         state_color or (active if selected else colors.Colors.ON_SURFACE), diameter / 2)
        r.arc(bx + 10, cy, 10, 0, 2 * math.pi, outline, width=2)
        if progress > 0:
            r.circle(bx + 10, cy, 5 * progress, active)
        if self.label:
            surf = txt.render_line_cached(self.label, size, scale=r.scale,
                                          family=family, color=_parse(label_color))
            r.blit_cached(surf, lx, cy - surf.get_height() / (2 * r.scale))

    def _group_value(self):
        g = self.parent
        while g is not None and not isinstance(g, RadioGroup):
            g = g.parent
        return g.value if g is not None else None

    def _hit_test(self, x, y):
        x, y = self._hit_point(x, y)
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _set_selected(self, selected: bool):
        self._selection_initialized = True
        self._animate_internal(
            "_selection_progress", 1.0 if selected else 0.0,
            motion.MEDIUM2 if selected else motion.SHORT1,
            motion.EMPHASIZED_DECELERATE if selected
            else AnimationCurve.LINEAR)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        self.update()

    def _pressed_hook(self, x, y):
        press(self, x, y)

    def _released_hook(self, _x, _y):
        release(self)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        return super()._tick_animations(now) or waiting


class Slider(Control):
    __unsupported_parameters__ = {"year_2023"}
    def __init__(self, value=None, *, min: float = 0.0, max: float = 1.0,
                 divisions: int | None = None, label=None, round: int = 0,
                 active_color=None, inactive_color=None, thumb_color=None,
                 autofocus=False, interaction=None, secondary_active_color=None,
                 secondary_track_value=None, overlay_color=None, padding=None,
                 year_2023=None, on_change=None, on_change_start=None,
                 on_change_end=None, on_focus=None, on_blur=None, **base):
        if max < min:
            raise ValueError("Slider max must not be less than min")
        if divisions is not None and divisions < 1:
            raise ValueError("Slider divisions must be positive")
        if value is not None and not min <= value <= max:
            raise ValueError("Slider value must be within min and max")
        if secondary_track_value is not None and not min <= secondary_track_value <= max:
            raise ValueError("Slider secondary_track_value must be within min and max")
        if year_2023 is not None:
            raise NotImplementedError("Slider year_2023 selects a deprecated Flutter appearance")
        super().__init__(**base)
        self.value = value if value is not None else min
        self.min, self.max, self.divisions = min, max, divisions
        self.label, self.round = label, round
        self.active_color, self.inactive_color, self.thumb_color = active_color, inactive_color, thumb_color
        self.autofocus, self.interaction = autofocus, interaction
        self.secondary_active_color, self.secondary_track_value = secondary_active_color, secondary_track_value
        self.overlay_color, self.padding = overlay_color, padding
        self.on_change, self.on_change_start, self.on_change_end = on_change, on_change_start, on_change_end
        self.on_focus, self.on_blur = on_focus, on_blur
        self._focusable, self._focused = True, False
        self._drag_allowed = False
        self._draggable = True
        self._hovered = False
        self._pressed = False
        self._label_progress = 0.0
        self._thumb_press_progress = 0.0
        init_state_layer(self)

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None
                else min(300.0, max_w or 300.0),
                self._height if self._height is not None else 48.0)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _k(self) -> float:
        if self.max <= self.min:
            return 0.0
        return max(0.0, min(1.0, (self.value - self.min) / (self.max - self.min)))

    def _value_from_x(self, x) -> float:
        tx, tw = self._track()
        k = max(0.0, min(1.0, (x - tx) / max(1.0, tw)))
        v = self.min + k * (self.max - self.min)
        if self.divisions and self.max > self.min:
            step = (self.max - self.min) / self.divisions
            v = self.min + round((v - self.min) / step) * step
        v = max(self.min, min(self.max, v))
        return round(v, self.round) if self.round else v

    def _track(self):
        x, y, w, h = self._rect
        p = as_padding(self.padding or 0)
        return x + p.left + 2.0, max(0.0, w - p.left - p.right - 4.0)  # 4dp handle stays inside the bounds

    def _drag_start(self, x, y):
        interaction = _enum_value(self.interaction) or "tapAndSlide"
        tx, tw = self._track()
        self._drag_allowed = interaction != "slideThumb" or abs(x - (tx + tw * self._k())) <= 24
        if not self._drag_allowed:
            return
        fire(self, "change_start", self.value)
        if interaction != "slideOnly":
            self._apply(self._value_from_x(x))

    def _drag(self, x, y):
        if self._drag_allowed and _enum_value(self.interaction) != "tapOnly":
            self._apply(self._value_from_x(x))

    def _drag_end(self):
        if self._drag_allowed:
            fire(self, "change_end", self.value)
        self._drag_allowed = False

    def _key(self, event):
        if event.key not in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_HOME, pygame.K_END):
            return
        step = (self.max - self.min) / (self.divisions or 20)
        value = (self.min if event.key == pygame.K_HOME else self.max if event.key == pygame.K_END else
                 self.value + (-step if event.key in (pygame.K_LEFT, pygame.K_DOWN) else step))
        fire(self, "change_start", self.value)
        self._apply(max(self.min, min(self.max, value)))
        fire(self, "change_end", self.value)

    def _apply(self, v):
        if v != self.value:
            self.value = v
            self.update()
            fire(self, "change", v)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        cy = y + h / 2
        track_x, track_w = self._track()
        track_x += x - self._rect[0]
        k = self._k()
        thumb_x = track_x + track_w * k
        handle_w = max(2.0, min(4.0, 4.0 - 2.0 * self._thumb_press_progress))
        gap = handle_w / 2 + 6.0
        default_color = (colors.Colors.ON_SURFACE if self.disabled
                         else colors.Colors.PRIMARY)
        active = _parse(self.active_color or default_color)
        inactive = _parse(self.inactive_color or
                          (colors.Colors.ON_SURFACE if self.disabled else
                           colors.Colors.SECONDARY_CONTAINER))
        handle = _parse(self.thumb_color or self.active_color or default_color)
        if self.disabled:
            active = (*active[:3], round(active[3] * 0.38))
            inactive = (*inactive[:3], round(inactive[3] * 0.12))
            handle = (*handle[:3], round(handle[3] * 0.38))

        active_end = max(track_x, thumb_x - gap)
        active_w = active_end - track_x
        if active_w > 8.0:
            r.fill_rect(track_x, cy - 8, active_w, 16, active,
                        radius=min(8, active_w / 2))
            if active_w >= 20.0 and active[3] == 255:
                r.fill_rect(active_end - 10, cy - 8, 10, 16, active, radius=2)
        inactive_x = min(track_x + track_w, thumb_x + gap)
        inactive_w = track_x + track_w - inactive_x
        if inactive_w > 8.0:
            r.fill_rect(inactive_x, cy - 8, inactive_w, 16, inactive,
                        radius=min(8, inactive_w / 2))
            if inactive_w >= 20.0 and inactive[3] == 255:
                r.fill_rect(inactive_x, cy - 8, 10, 16, inactive, radius=2)
            r.circle(track_x + track_w - 8, cy, 2, active)
        if self.secondary_track_value is not None and self.max > self.min:
            end = track_x + track_w * max(0, min(1, (self.secondary_track_value - self.min) / (self.max - self.min)))
            start = max(thumb_x + gap, track_x)
            if end > start:
                r.fill_rect(start, cy - 8, end - start, 16,
                            _parse(self.secondary_active_color or colors.Colors.PRIMARY_CONTAINER), radius=8)
        if self.divisions and self.divisions > 1:
            for step in range(1, self.divisions):
                tick_x = track_x + track_w * step / self.divisions
                if abs(tick_x - thumb_x) > gap:
                    r.circle(tick_x, cy, 2,
                             inactive if tick_x < thumb_x else active)

        if not self.disabled:
            if self._focused:
                r.fill_rect(thumb_x - 20, cy - 20, 40, 40,
                            _parse(colors.with_opacity(.12, _state_value(self, self.overlay_color, self.thumb_color or self.active_color or default_color))), radius=20)
            draw_state_layer(self, r, (thumb_x - 20, cy - 20, 40, 40),
                             _state_value(self, self.overlay_color, self.thumb_color or self.active_color or default_color),
                             20)
        r.fill_rect(thumb_x - handle_w / 2, cy - 22, handle_w, 44,
                    handle, radius=handle_w / 2)
        if self.label is not None and self._label_progress > 0:
            raw = str(self.label)
            value = f"{self.value:.{self.round}f}" if self.round else str(self.value)
            label = raw.replace("{value}", value) if "{value}" in raw else value
            surface = txt.render_line_cached(
                label, 12, scale=r.scale,
                color=_parse(colors.Colors.ON_PRIMARY))
            label_w = max(28.0, surface.get_width() / r.scale + 12.0)
            label_h = 28.0
            label_y = cy - 36.0
            r.opacity_push(self._label_progress)
            r.fill_rect(thumb_x - label_w / 2, label_y - label_h,
                        label_w, label_h, _parse(colors.Colors.PRIMARY),
                        radius=label_h / 2)
            r.blit_cached(surface, thumb_x - surface.get_width() / (2 * r.scale),
                   label_y - label_h / 2 - surface.get_height() / (2 * r.scale))
            r.opacity_pop()

    def _hit_test(self, x, y):
        x, y = self._hit_point(x, y)
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        self._animate_internal("_label_progress", 1.0 if on else 0.0,
                               motion.SHORT2, motion.EMPHASIZED)
        self.update()

    def _pressed_hook(self, x, y):
        press(self, x, y)
        self._animate_internal("_thumb_press_progress", 1.0,
                               motion.SHORT2,
                               motion.EMPHASIZED_DECELERATE)
        self._animate_internal("_label_progress", 1.0, motion.SHORT2,
                               motion.EMPHASIZED)

    def _released_hook(self, _x, _y):
        release(self)
        self._animate_internal("_thumb_press_progress", 0.0,
                               motion.SHORT2,
                               motion.EMPHASIZED_ACCELERATE)
        self._animate_internal("_label_progress",
                               1.0 if self._hovered else 0.0,
                               motion.SHORT2, motion.EMPHASIZED)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        return super()._tick_animations(now) or waiting


class DropdownOption(Control):
    """Options hold key/text data; the Dropdown renders them as a menu."""

    def __init__(self, key=None, *, text=None, content=None,
                 leading_icon=None, trailing_icon=None, style=None, **base):
        super().__init__(**base)
        self.key = key if key is not None else (text if text is not None else
                                                str(content))
        self.text = text
        self.content = content
        self.leading_icon, self.trailing_icon, self.style = leading_icon, trailing_icon, style


Option = DropdownOption  # Convenience alias


class _DropdownMenu(Control):
    """One clipped Material menu surface containing all option rows."""

    def __init__(self, owner, items):
        super().__init__()
        self.owner = owner
        self.items = items
        self._scroll_offset = 0.0

    def _attach(self, page, parent=None):
        super()._attach(page, parent)
        for item in self.items:
            item._attach(page, self)

    def _children(self):
        return self.items

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        for index, item in enumerate(self.items):
            item._place(x, y + index * _ITEM_H - self._scroll_offset, w, _ITEM_H, scale)

    def _owner_available(self):
        return (self.page is not None and self.owner.page is self.page
                and self.page._control_enabled(self.owner))

    def _draw_all(self, r, ox=0.0, oy=0.0):
        progress = self.owner._menu_progress
        timeline = self.owner._menu_timeline
        if progress <= 0.0 or not self.items or not self._owner_available():
            return
        x, y, w, full_h = self._rect
        visible_h = full_h * progress
        if self.owner._menu_closing:
            surface_alpha = min(1.0, timeline * 3.0)
        else:
            surface_alpha = min(1.0, timeline * 10.0)
        r.opacity_push(surface_alpha)
        from ..painting import draw_shadow
        draw_shadow(r, (x, y, w, visible_h), 4,
                    _state_value(self.owner, self.owner.elevation, 8))
        r.fill_rect(x, y, w, visible_h,
                    _parse(colors.Colors.SURFACE_CONTAINER), radius=4)
        r.opacity_pop()
        r.clip_push(x, y, w, visible_h)
        count = len(self.items)
        for index, item in enumerate(self.items):
            if self.owner._menu_closing:
                elapsed_ms = (1.0 - timeline) * 150.0
                reverse_index = count - 1 - index
                delay_ms = 50.0 + 50.0 * reverse_index / count
                alpha = 1.0 - max(
                    0.0, min(1.0, (elapsed_ms - delay_ms) / 50.0))
            else:
                delay = 0.5 * index / count
                alpha = max(0.0, min(1.0, (timeline - delay) / 0.5))
            r.opacity_push(alpha)
            item._draw_all(r, ox, oy)
            r.opacity_pop()
        r.clip_pop()

    def _hit_test(self, x, y):
        if self.owner._menu_closing or not self._owner_available():
            return None
        visible_h = self._rect[3] * self.owner._menu_progress
        if not (self._rect[0] <= x < self._rect[0] + self._rect[2]
                and self._rect[1] <= y < self._rect[1] + visible_h):
            return None
        return super()._hit_test(x, y)

    def _hit_test_hover(self, x, y):
        if self.owner._menu_closing or not self._owner_available() or not self._contains(x, y):
            return None
        return super()._hit_test_hover(x, y)

    def _find_scrollable(self, x, y):
        return self if self._contains(x, y) and self.owner.open and self._owner_available() else None

    def _wheel(self, delta):
        if not self._owner_available():
            return
        maximum = max(0, len(self.items) * _ITEM_H - self._rect[3])
        self._scroll_offset = max(0, min(maximum, self._scroll_offset + delta))
        self._place(*self._rect, self.page._app.renderer.scale)
        self.repaint()


class Dropdown(Control):
    __unsupported_parameters__ = {"menu_style", "expanded_insets"}

    def __init__(self, value=None, *, options=None, text=None, hint_text=None, label=None,
                 on_select=None, on_text_change=None, on_focus=None, on_blur=None,
                 autofocus=False, text_size: float = 16.0, text_style=None,
                 text_align=TextAlign.START, elevation=8, enable_filter=False,
                 enable_search=True, editable=False, menu_height=None, menu_width=None,
                 menu_style=None, expanded_insets=None, selected_suffix=None,
                 input_filter=None, capitalization=None, trailing_icon=None,
                 leading_icon=None, selected_trailing_icon=None,
                 filled=False, fill_color=None, bgcolor=None, border=None,
                 border_radius=None, border_width=None, border_color=None,
                 focused_border_width=None, focused_border_color=None,
                 color=None, content_padding=None, dense=False, hover_color=None,
                 label_style=None, hint_style=None, helper_text=None, helper_style=None,
                 error_text=None, error_style=None, **base):
        if menu_style is not None or expanded_insets is not None:
            raise NotImplementedError("Dropdown menu_style and expanded_insets are not supported")
        if menu_height is not None and menu_height <= 0 or menu_width is not None and menu_width <= 0:
            raise ValueError("Dropdown menu dimensions must be positive")
        super().__init__(**base)
        values = locals().copy()
        for name in ("value text hint_text label on_select on_text_change on_focus on_blur autofocus text_size text_style text_align elevation enable_filter enable_search editable menu_height menu_width selected_suffix input_filter capitalization trailing_icon leading_icon selected_trailing_icon filled fill_color bgcolor border border_radius border_width border_color focused_border_width focused_border_color color content_padding dense hover_color label_style hint_style helper_text helper_style error_text error_style").split():
            setattr(self, name, values[name])
        self.options = list(options or [])
        initial_text = text if editable and text is not None else self._selected_text()
        self._field = TextField(initial_text, label=label, read_only=not editable, can_request_focus=False)
        self._focusable, self._focused = True, False
        self._menu_index = 0
        self._filtered_options = []
        self.open = False
        self._menu: list[Control] = []
        self._menu_surface = None
        self._menu_progress = 0.0
        self._menu_timeline = 0.0
        self._menu_closing = False
        self._menu_close_deadline = None
        self._paint_offset = (0.0, 0.0)
        self.on_click = self._toggle_menu  # internal routing
        self._hovered = False
        self._pressed = False
        init_state_layer(self)

    def _selected_text(self):
        for option in self.options:
            if option.key == self.value:
                return option.text or str(option.key)
        return ""

    def _children(self):
        return [self._field]

    def _sync_field(self):
        for name in ("label", "label_style", "hint_text", "hint_style", "text_size", "text_style",
                     "text_align", "filled", "fill_color", "bgcolor", "border", "border_radius",
                     "border_width", "border_color", "focused_border_width", "focused_border_color",
                     "color", "content_padding", "dense", "input_filter", "capitalization", "hover_color"):
            setattr(self._field, name, getattr(self, name))
        self._field.read_only = not self.editable
        self._field.helper, self._field.helper_style = self.helper_text, self.helper_style
        self._field.error, self._field.error_style = self.error_text, self.error_style
        self._field.prefix_icon = self.leading_icon
        self._field.suffix = self.selected_suffix
        self._field.suffix_icon = (self.selected_trailing_icon if self.open and self.selected_trailing_icon is not None
                                   else self.trailing_icon if self.trailing_icon is not None
                                   else Icons.KEYBOARD_ARROW_UP if self.open else Icons.KEYBOARD_ARROW_DOWN)
        self._field.value = self.text if self.editable and self.text is not None else self._selected_text()
        if self._field.value != self._field._last_value:
            self._field._prepare_animations(time.perf_counter())
        self._field._caret = min(self._field._caret, len(self._field.value))

    def _set_focused(self, focused):
        self._focused = focused
        self._field._set_focused(focused)

    def _text_changed(self):
        self.text = self._field.value
        fire(self, "text_change", self.text)
        if self.open and self.enable_filter:
            self._rebuild_menu()
        self.update()

    def _text_input(self, value):
        if self.editable:
            self._sync_field()
            previous = self._field.value
            self._field._text_input(value)
            if self._field.value != previous:
                self._text_changed()
        elif self.enable_search:
            query = value.casefold()
            options = [option for option in self.options if option.visible and not option.disabled]
            start = next((i for i, option in enumerate(options) if option.key == self.value), -1)
            for offset in range(1, len(options) + 1):
                option = options[(start + offset) % len(options)]
                if (option.text or str(option.key)).casefold().startswith(query):
                    self._pick_option(option)
                    break

    def _pointer_down(self, x, y, clicks=1):
        if self.editable:
            self._sync_field()
            self._field._pointer_down(x, y, clicks)

    def _key(self, event):
        if event.key == pygame.K_ESCAPE:
            self._close_menu()
        elif event.key in (pygame.K_UP, pygame.K_DOWN):
            if not self.open:
                self._toggle_menu()
            if self._filtered_options:
                direction = -1 if event.key == pygame.K_UP else 1
                for _ in self._filtered_options:
                    self._menu_index = (self._menu_index + direction) % len(self._filtered_options)
                    if not self._filtered_options[self._menu_index].disabled:
                        break
                if self._menu_surface is not None:
                    index = self._menu_index
                    top = index * _ITEM_H
                    bottom = top + _ITEM_H
                    surface = self._menu_surface
                    if top < surface._scroll_offset:
                        surface._wheel(top - surface._scroll_offset)
                    elif bottom > surface._scroll_offset + surface._rect[3]:
                        surface._wheel(bottom - surface._rect[3] - surface._scroll_offset)
            self.update()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.open and self._filtered_options:
                self._pick_option(self._filtered_options[self._menu_index])
            else:
                self._toggle_menu()
        elif self.editable:
            previous = self._field.value
            self._field._key(event)
            if self._field.value != previous:
                self._text_changed()

    def _pick_option(self, option):
        if option.disabled:
            return
        self.value = option.key
        self.text = option.text or str(option.key)
        self._field.value = self.text
        self._field._caret = len(self.text)
        self._close_menu()
        self.update()
        fire(self, "select", option.key)

    def _rebuild_menu(self):
        if self._menu_surface is not None and self.page is not None:
            if self._menu_surface in self.page.overlay:
                self.page.overlay.remove(self._menu_surface)
        self._menu, self._menu_surface = [], None
        self._build_menu(self.page)

    def _intrinsic(self, max_w, max_h, scale):
        self._sync_field()
        w, h = self._field._intrinsic(max_w, max_h, scale)
        return (self._width if self._width is not None else w,
                self._height if self._height is not None else h)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        self._field._place(x, y, w, h, scale)
        if self.open:
            self._position_menu()

    def _toggle_menu(self, e=None):
        if self.open:
            self._close_menu()
            return
        self.open = True
        self._menu_closing = False
        self._menu_close_deadline = None
        page = self.page
        if page is not None and self._menu_surface is None:
            self._build_menu(page)
        self._animate_internal("_menu_progress", 1.0, motion.MEDIUM2,
                               motion.EMPHASIZED)
        self._animate_internal("_menu_timeline", 1.0, motion.MEDIUM2,
                               AnimationCurve.LINEAR)
        self.update()

    def _close_menu(self):
        if not self.open or self._menu_closing:
            return
        self.open = False
        self._menu_closing = True
        now = time.perf_counter()
        self._menu_close_deadline = now + motion.SHORT3 / 1000.0
        self._animate_internal("_menu_progress", 0.35, motion.SHORT3,
                               motion.EMPHASIZED_ACCELERATE, now=now)
        self._animate_internal("_menu_timeline", 0.0, motion.SHORT3,
                               AnimationCurve.LINEAR, now=now)
        self.update()

    def _finish_menu_close(self):
        page = self.page
        if page is not None and self._menu_surface in page.overlay:
            page.overlay.remove(self._menu_surface)
        self._menu = []
        self._menu_surface = None
        self._menu_closing = False
        self._menu_close_deadline = None
        self._menu_progress = 0.0
        self._menu_timeline = 0.0
        self._animation_targets["_menu_progress"] = 0.0
        self._animation_targets["_menu_timeline"] = 0.0

    def _build_menu(self, page):
        query = (self.text or "").casefold() if self.enable_filter and self.editable else ""
        self._filtered_options = [option for option in self.options if option.visible and
                                  (not query or query in (option.text or str(option.key)).casefold())]
        self._menu_index = min(self._menu_index, max(0, len(self._filtered_options) - 1))
        for option in self._filtered_options:
            style = option.style
            text_style = getattr(style, "text_style", None)
            color = _state_value(option, getattr(style, "color", None), colors.Colors.ON_SURFACE)
            content = option.content or Text(option.text or str(option.key), size=self.text_size,
                                              color=color, style=text_style)
            children = [part for part in (_icon_control(option.leading_icon), content,
                                         _icon_control(option.trailing_icon)) if part is not None]
            item = Container(Row(*children, spacing=8),
                             bgcolor=_state_value(option, getattr(style, "bgcolor", None), colors.Colors.SURFACE_CONTAINER),
                             padding=getattr(style, "padding", None) or Padding.symmetric(horizontal=_FIELD_PAD),
                             alignment=Alignment.CENTER_LEFT, border_radius=4, ink=True,
                             disabled=option.disabled,
                             on_click=lambda event=None, selected=option: self._pick_option(selected))
            self._menu.append(item)
        self._menu_surface = _DropdownMenu(self, self._menu)
        if page is not None:
            # Overlay geometry is in window coordinates, independent of the field tree.
            self._menu_surface._attach(page, None)
            self._position_menu()
            page.overlay.append(self._menu_surface)

    def _position_menu(self):
        if self._menu_surface is None or self.page is None:
            return
        x, y, w, h = self._rect
        corners = [self._screen_point(px, py) for px, py in
                   ((x, y), (x + w, y), (x, y + h), (x + w, y + h))]
        anchor_left = min(px for px, py in corners)
        anchor_top = min(py for px, py in corners)
        anchor_right = max(px for px, py in corners)
        anchor_bottom = max(py for px, py in corners)
        width = min(self.menu_width or anchor_right - anchor_left,
                    max(0, self.page.width))
        height = min(len(self._menu) * _ITEM_H, self.menu_height or 320,
                     max(0, self.page.height - 8))
        left = min(max(0, anchor_left), max(0, self.page.width - width))
        top = anchor_bottom + 4
        if top + height > self.page.height:
            top = max(0, anchor_top - height - 4)
        self._menu_surface._place(left, top, width, height, self.page._app.renderer.scale)

    def _draw_all(self, r, ox=0.0, oy=0.0):
        if self.visible:
            self._effects_begin(r, ox, oy)
            try:
                self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
            finally:
                self._effects_end(r)

    def _draw(self, r, x, y):
        rx, ry, w, h = self._rect
        paint_offset = (x - rx, y - ry)
        self._paint_offset = paint_offset
        # Rotation/scale animation can move the anchor without changing the layout rect.
        if self._menu_surface is not None:
            self._position_menu()
        self._sync_field()
        self._field._draw(r, x, y)

    def _hit_test(self, x, y):
        x, y = self._hit_point(x, y)
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        self.update()

    def _pressed_hook(self, x, y):
        press(self, x, y)

    def _released_hook(self, _x, _y):
        release(self)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        if (self._menu_close_deadline is not None
                and now >= self._menu_close_deadline):
            self._finish_menu_close()
        closing = self._menu_close_deadline is not None
        return super()._tick_animations(now) or waiting or closing
