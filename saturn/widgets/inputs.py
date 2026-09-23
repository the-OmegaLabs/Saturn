"""Input controls: TextField, Checkbox, Switch, Radio/RadioGroup, Slider,
Dropdown (+ legacy Option alias).
"""
from __future__ import annotations

import math
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
from ..event import fire
from ..text import get_font, get_icon_font
from ..painting import draw_notched_outline
from ..types import (Alignment, AnimationCurve, LabelPosition,
                     OutlineInputBorder, Padding, as_border_radius)

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


class TextField(Control):
    def __init__(self, value: str = "", *, label=None, hint_text=None,
                 password: bool = False, multiline: bool = False,
                 max_lines: int | None = None, read_only: bool = False,
                 max_length: int | None = None, shift_enter: bool = False,
                 show_cursor: bool = True,
                 obscuring_character: str = "•",
                 text_size: float | None = None, on_change=None, on_submit=None,
                 on_focus=None, on_blur=None, on_click=None,
                 filled: bool = False, bgcolor=None, border_color=None,
                 cursor_color=None, border_radius: float | None = None,
                 border=None, text_style=None,
                 can_reveal_password: bool = False, on_hover=None, **base):
        super().__init__(**base)
        if max_length is not None and (max_length == 0 or max_length < -1):
            raise ValueError("max_length must be positive or -1")
        if len(obscuring_character) != 1:
            raise ValueError("obscuring_character must be one character")
        self.value = value
        self.label = label
        self.hint_text = hint_text
        self.password = password
        self.multiline = multiline
        self.max_lines = max_lines
        self.read_only = read_only
        self.max_length = max_length
        self.shift_enter = shift_enter
        self.show_cursor = show_cursor
        self.obscuring_character = obscuring_character
        self.text_size = text_size or 16.0
        self.on_change = on_change
        self.on_submit = on_submit
        self.on_focus = on_focus
        self.on_blur = on_blur
        self.on_click = on_click
        self.on_hover = on_hover
        self.filled = filled
        self.bgcolor = bgcolor
        self.border_color = border_color
        self.cursor_color = cursor_color
        self.border_radius = border_radius
        self.border = border
        self.text_style = text_style
        self.can_reveal_password = can_reveal_password
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
        self._focusable = True
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
        self._paint_offset = (0.0, 0.0)

    def _style(self):
        """(family, value size, value color) from the flet text_style."""
        ts = self.text_style
        if ts is None:
            return None, self.text_size, colors.Colors.ON_SURFACE
        return (ts.font_family,
                ts.size or self.text_size,
                ts.color if ts.color is not None else colors.Colors.ON_SURFACE)

    def _render_cached(self, slot, text, size, scale, family, color):
        """Reuse immutable text rasters across short state animations."""
        color = tuple(_parse(color))
        key = (slot, text, float(size), float(scale), family, color,
               txt.default_family, txt.font_revision)
        surface = self._line_cache.get(key)
        if surface is None:
            surface = txt.render_line(
                text, size, scale=scale, family=family, color=color)
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
    def _intrinsic(self, max_w, max_h, scale):
        w = self._width if self._width is not None else min(300.0, max_w or 300.0)
        if self.multiline:
            lines = max(1, self.max_lines or 3)
            h = _FIELD_PAD * 2 + txt.line_height(self.text_size, scale=scale) * lines
        else:
            h = _FIELD_H
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
        if not self.visible or self.disabled:
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
                        text=self.value or self.hint_text or self.label)

    def _index_at(self, x) -> int:
        """Return the nearest text boundary for a page-space x coordinate."""
        scale = self.page._app.renderer.scale if self.page else 1.0
        family, vsize, _ = self._style()
        px = x - (self._rect[0] + self._paint_offset[0] + _FIELD_PAD) \
            + self._scroll_x
        vis = self._visible_text()
        acc, idx = 0.0, 0
        for i, ch in enumerate(vis):
            w = txt.line_width(vis[:i + 1], vsize, scale=scale,
                               family=family) - acc
            if acc + w / 2 >= px:
                idx = i
                break
            acc += w
            idx = i + 1
        return idx

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
        index = self._index_at(x)
        clicks = max(1, int(clicks or 1))
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
        self._restart_cursor_blink()
        self._update_ime_rect()
        self.update()

    def _caret_at(self, x):
        """Compatibility hook: place the caret with a single click."""
        self._pointer_down(x, self._rect[1], 1)

    def _drag_start(self, x, _y):
        if (self.password and self.can_reveal_password
                and x >= self._rect[0] + self._rect[2] - 48):
            self._selection_dragging = False
            return
        self._selection_dragging = True

    def _drag(self, x, _y):
        if not self._selection_dragging:
            return
        index = self._index_at(x)
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
        self._restart_cursor_blink()
        self._update_ime_rect()
        self.update()

    def _drag_end(self):
        self._selection_dragging = False

    def _text_viewport(self):
        """Return the horizontal content viewport, excluding adornments."""
        x, _y, w, _h = self._rect
        trailing = 36.0 if self.password and self.can_reveal_password else 0.0
        return x + _FIELD_PAD, max(0.0, w - 2 * _FIELD_PAD - trailing)

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
        caret_x = txt.line_width(
            caret_text, vsize, scale=scale, family=family)
        content_w = txt.line_width(
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
        self._restart_cursor_blink()
        self.update()

    def _text_input(self, t):
        if self.read_only:
            return
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
        cx = text_left - self._scroll_x + txt.line_width(
            caret_text, vsize, scale=scale, family=family)
        cx = max(text_left, min(text_left + viewport_w, cx))
        text_y = (self._rect[1] + self._paint_offset[1]
                  + (self._rect[3] - vsize) / 2)
        if self.filled and self.label and not isinstance(self.border, OutlineInputBorder):
            text_y += 8 * self._label_progress
        # SDL's Windows backend treats this as both the current composition
        # point and an exclusion area. Start at the visual caret but extend to
        # the field bottom so the candidate UI sits below, never over the next
        # line or control.
        anchor_x = cx + _IME_OFFSET_X
        anchor_y = text_y + _IME_OFFSET_Y
        field_bottom = (self._rect[1] + self._paint_offset[1]
                        + self._rect[3] + _IME_OFFSET_Y)
        rect = pygame.Rect(
            round(anchor_x), round(anchor_y), 1,
            max(1, round(field_bottom - anchor_y)),
        )
        if rect != self._last_ime_rect:
            self.page._app.set_text_input_rect(rect)
            self._last_ime_rect = rect

    def _key(self, e):
        k = e.key
        modifiers = getattr(e, "mod", 0)
        shortcut = bool(modifiers & (pygame.KMOD_CTRL | pygame.KMOD_META))
        extend = bool(modifiers & pygame.KMOD_SHIFT)

        if shortcut and k == pygame.K_a:
            self._clear_composition(update=False)
            self._select_range(0, len(self.value))
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
        self._paint_offset = (x - rx, y - ry)
        scale = r.scale
        outline = self.border if isinstance(self.border, OutlineInputBorder) else None
        filled_style = self.filled and outline is None
        radius_value = (outline.border_radius if outline is not None
                        else self.border_radius)
        radius = as_border_radius(
            _RADIUS if radius_value is None else radius_value).top_left
        focus = self._focus_progress
        hover = self._hover_progress
        if self.filled or self.bgcolor is not None:
            field_bg = _parse(
                self.bgcolor or colors.Colors.SURFACE_CONTAINER_HIGHEST)
            if hover:
                field_bg = _mix(field_bg, colors.Colors.ON_SURFACE,
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
        if outline is not None:
            side = outline.side
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
        label_progress = max(0.0, min(1.0, self._label_progress)) if self.label else 0.0
        family, vsize, vcolor = self._style()
        if self.label:
            inactive_color = _parse(colors.Colors.ON_SURFACE_VARIANT)
            active_color = _parse(colors.Colors.PRIMARY)
            inline_label = self._render_cached(
                "label-inline", self.label, vsize, scale, family, inactive_color)
            floating_inactive = self._render_cached(
                "label-floating-inactive", self.label, 12.0, scale, family, inactive_color)
            floating_active = self._render_cached(
                "label-floating-active", self.label, 12.0, scale, family, active_color)
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
                if self.label and draw_width > 0 and label_progress > 0:
                    # The cutout grows with the current label's width AND line
                    # height, using the same progress as its size and position.
                    gap = draw_width * label_progress + 8.0
                    draw_notched_outline(r, (x, y, w, h), border_draw_color,
                                         border_width, radius, _FIELD_PAD - 4, gap,
                                         depth=label_line_height * label_progress / 2)
                else:
                    r.stroke_rect(x, y, w, h, border_draw_color,
                                  width=border_width, radius=radius)
        ty, th = y, h
        if filled_style and self.label:
            ty += 16 * label_progress
            th -= 16 * label_progress
        if self.label:
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
        draw_x = text_left - self._scroll_x
        hint_progress = 0.0
        if displayed:
            surf = self._render_cached(
                "value", displayed, vsize, scale, family, _parse(vcolor))
            text_y = (ty + (th - surf.get_height() / scale) / 2
                      + _text_ink_offset(family, vsize, scale))
            r.clip_push(text_left, y, viewport_w, h)
            selected = self._selection()
            if selected is not None and not composition:
                start, end = selected
                selected_x = draw_x + txt.line_width(
                    shown[:start], vsize, scale=scale, family=family)
                selected_w = txt.line_width(
                    shown[start:end], vsize, scale=scale, family=family)
                r.fill_rect(
                    selected_x, text_y, max(1.0, selected_w),
                    surf.get_height() / scale,
                    _parse(colors.with_opacity(0.36, colors.Colors.PRIMARY)),
                    radius=2)
            r.blit_cached(surf, draw_x, text_y)
            if composition:
                comp_x = draw_x + txt.line_width(
                    prefix, vsize, scale=scale, family=family)
                comp_w = txt.line_width(
                    composition, vsize, scale=scale, family=family)
                underline_y = min(y + h - 2,
                                  text_y + surf.get_height() / scale)
                r.fill_rect(comp_x, underline_y, max(1, comp_w), 1,
                            _parse(colors.Colors.ON_SURFACE_VARIANT))
                if self._composition_length:
                    selected = composition[
                        self._composition_start:
                        self._composition_start + self._composition_length]
                    selected_x = comp_x + txt.line_width(
                        composition[:self._composition_start], vsize,
                        scale=scale, family=family)
                    selected_w = txt.line_width(
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
                "hint", self.hint_text, self.text_size, scale, family,
                _parse(colors.Colors.ON_SURFACE_VARIANT))
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
        if self._focused and self._cursor_visible and self.show_cursor:
            ime_cursor = min(len(composition),
                             self._composition_start + self._composition_length)
            caret_text = prefix + composition[:ime_cursor]
            cx = draw_x + txt.line_width(
                caret_text, vsize, scale=scale, family=family)
            r.clip_push(text_left, y, viewport_w, h)
            r.fill_rect(cx, ty + (th - vsize) / 2, 2, vsize,
                        _parse(self.cursor_color or colors.Colors.PRIMARY))
            r.clip_pop()
            self._update_ime_rect()


class _Toggle(Control):
    """Shared click-to-toggle plumbing for Checkbox/Switch."""

    def __init__(self, label: str = "", *, value=False, active_color=None,
                 label_position=LabelPosition.RIGHT, on_change=None, **base):
        super().__init__(**base)
        self.label = label
        self.value = bool(value)
        self.active_color = active_color
        self.label_position = label_position
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

    def _intrinsic(self, max_w, max_h, scale):
        box = self._box_size()
        lw, lh = txt.measure(self.label, 14, scale=scale) if self.label else (0, 0)
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
        box = self._box_size()
        cy = y + h / 2
        first_is_box = self.label_position is not LabelPosition.LEFT
        bw = box
        lw = (w - bw - 8) if self.label else 0.0
        bx = x if first_is_box else x + lw + 8
        lx = x + bw + 8 if first_is_box else x
        self._draw_state(r, bx, cy, box)
        self._draw_box(r, bx, cy - box / 2, box)
        if self.label:
            surf = txt.render_line_cached(
                self.label, 14, scale=r.scale,
                color=_parse(colors.Colors.ON_SURFACE))
            r.blit_cached(surf, lx, cy - surf.get_height() / (2 * r.scale))

    def _hit_test(self, x, y):
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _draw_state(self, r, bx, cy, box):
        size = 40.0
        state_color = (self.active_color or colors.Colors.PRIMARY
                       if self.value else colors.Colors.ON_SURFACE)
        draw_state_layer(self, r,
                         (bx + box / 2 - size / 2, cy - size / 2,
                          size, size), state_color, size / 2)

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
    def _box_size(self):
        return 18.0

    def _draw_box(self, r, x, y, box):
        progress = self._value_progress
        if progress > 0:
            selected_box = box * (0.6 + 0.4 * progress)
            selected_x = x + (box - selected_box) / 2
            selected_y = y + (box - selected_box) / 2
            r.opacity_push(min(1.0, progress * 3.0))
            r.fill_rect(selected_x, selected_y, selected_box, selected_box,
                        _parse(self.active_color or colors.Colors.PRIMARY), radius=2)
            f = get_icon_font(round(14 * r.scale))
            surf = f.render(chr(int(Icons.CHECK)), True,
                            _parse(colors.Colors.ON_PRIMARY))
            icon_w = surf.get_width() / r.scale * (0.6 + 0.4 * progress)
            icon_h = surf.get_height() / r.scale * (0.6 + 0.4 * progress)
            r.blit_scaled(surf, x + (box - icon_w) / 2,
                          y + (box - icon_h) / 2, icon_w, icon_h)
            r.opacity_pop()
        if progress < 1:
            r.opacity_push(1 - progress)
            r.stroke_rect(x, y, box, box,
                          _parse(colors.Colors.ON_SURFACE_VARIANT),
                          width=2, radius=2)
            r.opacity_pop()


class Switch(_Toggle):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        lw, _ = txt.measure(self.label, 14, scale=scale) if self.label else (0, 0)
        w = 52.0 + (8.0 + lw if self.label else 0.0)
        return (self._width if self._width is not None else w,
                self._height if self._height is not None else 40.0)

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
        active = _parse(self.active_color or colors.Colors.PRIMARY)
        inactive = _parse(colors.Colors.SURFACE_CONTAINER_HIGHEST)
        track_c = tuple(round(a + (b - a) * color_progress)
                        for a, b in zip(inactive, active))
        r.fill_rect(x, track_y, w, h, track_c, radius=h / 2)
        if color_progress < 1.0:
            r.opacity_push(1.0 - color_progress)
            r.stroke_rect(x, track_y, w, h,
                          _parse(colors.Colors.OUTLINE), width=2,
                          radius=h / 2)
            r.opacity_pop()
        thumb_r = 8.0 + 4.0 * size_progress
        # Flet's Material switch snaps its handle to the 28px pressed size;
        # this is intentionally independent of the slower state-layer alpha.
        thumb_r += (14.0 - thumb_r) * self._thumb_press_progress
        tx = x + 16.0 + (w - 32.0) * progress
        on_thumb = _parse(colors.Colors.ON_PRIMARY)
        off_thumb = _parse(colors.Colors.OUTLINE)
        tc = tuple(round(a + (b - a) * color_progress)
                   for a, b in zip(off_thumb, on_thumb))
        r.circle(tx, track_y + h / 2, thumb_r, tc)

    def _draw_state(self, r, bx, cy, box):
        size = 40.0
        tx = bx + 16.0 + (box - 32.0) * self._value_progress
        state_color = (self.active_color or colors.Colors.PRIMARY
                       if self.value else colors.Colors.ON_SURFACE)
        draw_state_layer(self, r, (tx - size / 2, cy - size / 2,
                                   size, size), state_color, size / 2)

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
        self.value = radio.value
        self._last_value = self.value
        for item in self._radios():
            item._set_selected(item.value == self.value)
        self.update()
        fire(self, "change", radio.value)

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
    def __init__(self, value=None, *, label: str = "",
                 label_position=LabelPosition.RIGHT, active_color=None, **base):
        super().__init__(**base)
        self.value = value
        self.label = label
        self.label_position = label_position
        self.active_color = active_color
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

    def _intrinsic(self, max_w, max_h, scale):
        lw, lh = txt.measure(self.label, 14, scale=scale) if self.label else (0, 0)
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
        active = _parse(self.active_color or colors.Colors.PRIMARY)
        inactive = _parse(colors.Colors.ON_SURFACE_VARIANT)
        outline = tuple(round(a + (b - a) * progress)
                        for a, b in zip(inactive, active))
        draw_state_layer(self, r, (x - 10, cy - 20, 40, 40),
                         active if selected else colors.Colors.ON_SURFACE,
                         20)
        r.arc(x + 10, cy, 10, 0, 2 * math.pi, outline, width=2)
        if progress > 0:
            r.circle(x + 10, cy, 5 * progress, active)
        if self.label:
            surf = txt.render_line_cached(
                self.label, 14, scale=r.scale,
                color=_parse(colors.Colors.ON_SURFACE))
            r.blit_cached(surf, x + 28, cy - surf.get_height() / (2 * r.scale))

    def _group_value(self):
        g = self.parent
        while g is not None and not isinstance(g, RadioGroup):
            g = g.parent
        return g.value if g is not None else None

    def _hit_test(self, x, y):
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
    def __init__(self, value=None, *, min: float = 0.0, max: float = 1.0,
                 divisions: int | None = None, label=None, round: int = 0,
                 active_color=None, inactive_color=None, thumb_color=None,
                 on_change=None, on_change_start=None, on_change_end=None, **base):
        super().__init__(**base)
        self.value = value if value is not None else min
        self.min = min
        self.max = max
        self.divisions = divisions
        self.label = label
        self.round = round
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.thumb_color = thumb_color
        self.on_change = on_change
        self.on_change_start = on_change_start
        self.on_change_end = on_change_end
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
        if self.divisions:
            step = (self.max - self.min) / self.divisions
            v = self.min + round((v - self.min) / step) * step
        v = max(self.min, min(self.max, v))
        return round(v, self.round) if self.round else v

    def _track(self):
        x, y, w, h = self._rect
        return x + 2.0, max(0.0, w - 4.0)  # 4dp handle stays inside the bounds

    def _drag_start(self, x, y):
        fire(self, "change_start")
        self._apply(self._value_from_x(x))

    def _drag(self, x, y):
        self._apply(self._value_from_x(x))

    def _drag_end(self):
        fire(self, "change_end")

    def _apply(self, v):
        if v != self.value:
            self.value = v
            self.update()
            fire(self, "change", v)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        cy = y + h / 2
        track_x, track_w = x + 2.0, max(0.0, w - 4.0)
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
        if self.divisions and self.divisions > 1:
            for step in range(1, self.divisions):
                tick_x = track_x + track_w * step / self.divisions
                if abs(tick_x - thumb_x) > gap:
                    r.circle(tick_x, cy, 2,
                             inactive if tick_x < thumb_x else active)

        if not self.disabled:
            draw_state_layer(self, r, (thumb_x - 20, cy - 20, 40, 40),
                             self.thumb_color or self.active_color or default_color,
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

    def __init__(self, key=None, *, text=None, content=None, **base):
        super().__init__(**base)
        self.key = key if key is not None else (text if text is not None else
                                                str(content))
        self.text = text
        self.content = content


Option = DropdownOption  # legacy flet name


class _DropdownMenu(Control):
    """One clipped Material menu surface containing all option rows."""

    def __init__(self, owner, items):
        super().__init__()
        self.owner = owner
        self.items = items

    def _attach(self, page, parent=None):
        super()._attach(page, parent)
        for item in self.items:
            item._attach(page, self)

    def _children(self):
        return self.items

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        for index, item in enumerate(self.items):
            item._place(x, y + index * _ITEM_H, w, _ITEM_H, scale)

    def _draw_all(self, r, ox=0.0, oy=0.0):
        progress = self.owner._menu_progress
        timeline = self.owner._menu_timeline
        if progress <= 0.0 or not self.items:
            return
        x, y, w, full_h = self._rect
        visible_h = full_h * progress
        if self.owner._menu_closing:
            surface_alpha = min(1.0, timeline * 3.0)
        else:
            surface_alpha = min(1.0, timeline * 10.0)
        r.opacity_push(surface_alpha)
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
        if self.owner._menu_closing:
            return None
        visible_h = self._rect[3] * self.owner._menu_progress
        if not (self._rect[0] <= x < self._rect[0] + self._rect[2]
                and self._rect[1] <= y < self._rect[1] + visible_h):
            return None
        return super()._hit_test(x, y)

    def _hit_test_hover(self, x, y):
        if self.owner._menu_closing:
            return None
        return super()._hit_test_hover(x, y)


class Dropdown(Control):
    def __init__(self, value=None, *, options=None, hint_text=None, label=None,
                 on_select=None, text_size: float = 16.0, filled=False,
                 fill_color=None, bgcolor=None, border=None,
                 border_radius=None, **base):
        super().__init__(**base)
        self.value = value
        self.options = list(options or [])
        self.hint_text = hint_text
        self.label = label
        self.on_select = on_select
        self.text_size = text_size
        self.filled = filled
        self.fill_color = fill_color
        self.bgcolor = bgcolor
        self.border = border
        self.border_radius = border_radius
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
        for o in self.options:
            if o.key == self.value:
                return o.text or o.key
        return ""

    def _intrinsic(self, max_w, max_h, scale):
        w = self._width if self._width is not None else min(300.0, max_w or 300.0)
        return (w, self._height if self._height is not None else _FIELD_H)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
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
        for i, opt in enumerate(self.options):
            key = opt.key

            def pick(e=None, _key=key):
                self.value = _key
                self._close_menu()
                self.update()
                fire(self, "select", _key)

            item = Container(Text(opt.text or opt.key, size=self.text_size,
                                  color=colors.Colors.ON_SURFACE),
                             bgcolor=colors.Colors.SURFACE_CONTAINER,
                             padding=Padding.symmetric(horizontal=_FIELD_PAD),
                             alignment=Alignment.CENTER_LEFT,
                             border_radius=4, ink=True,
                             on_click=pick)
            self._menu.append(item)
        self._menu_surface = _DropdownMenu(self, self._menu)
        self._menu_surface._attach(page, self)
        self._position_menu()
        page.overlay.append(self._menu_surface)

    def _position_menu(self):
        x, y, w, h = self._rect
        x += self._paint_offset[0]
        y += self._paint_offset[1]
        if self._menu_surface is not None:
            self._menu_surface._place(
                x, y + h + 4.0, w, len(self._menu) * _ITEM_H,
                self.page._app.renderer.scale)

    def _draw(self, r, x, y):
        rx, ry, w, h = self._rect
        paint_offset = (x - rx, y - ry)
        if paint_offset != self._paint_offset:
            self._paint_offset = paint_offset
            if self._menu_surface is not None:
                self._position_menu()
        radius = as_border_radius(
            _RADIUS if self.border_radius is None else self.border_radius).top_left
        if self.filled or self.fill_color is not None or self.bgcolor is not None:
            r.fill_rect(
                x, y, w, h,
                _parse(self.fill_color or self.bgcolor or
                       colors.Colors.SURFACE_CONTAINER_HIGHEST),
                radius=radius)
        draw_state_layer(self, r, (x, y, w, h),
                         colors.Colors.ON_SURFACE, radius)
        border_color = (colors.Colors.PRIMARY
                        if self.open or self._menu_closing
                        else colors.Colors.OUTLINE)
        r.stroke_rect(x, y, w, h, _parse(border_color),
                      width=1 + min(1.0, self._menu_timeline), radius=radius)
        shown = self._selected_text() or self.hint_text or ""
        c = _parse(colors.Colors.ON_SURFACE if self._selected_text()
                   else colors.Colors.ON_SURFACE_VARIANT)
        surf = txt.render_line_cached(
            shown, self.text_size, scale=r.scale, color=c)
        r.clip_push(x, y, w, h)
        r.blit_cached(surf, x + _FIELD_PAD,
               y + (h - surf.get_height() / r.scale) / 2)
        r.clip_pop()
        af = get_icon_font(round(24 * r.scale))
        arrow_icon = (Icons.KEYBOARD_ARROW_UP
                      if self._menu_timeline >= 0.5
                      else Icons.KEYBOARD_ARROW_DOWN)
        arrow = af.render(chr(int(arrow_icon)), True,
                          _parse(colors.Colors.ON_SURFACE_VARIANT))
        r.blit(arrow, x + w - 32, y + (h - arrow.get_height() / r.scale) / 2)

    def _hit_test(self, x, y):
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
