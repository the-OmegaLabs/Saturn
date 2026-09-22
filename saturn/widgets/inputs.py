"""Input controls: TextField, Checkbox, Switch, Radio/RadioGroup, Slider,
Dropdown (+ legacy Option alias).
"""
from __future__ import annotations

import pygame

from .containers import Container, Row
from .text import Text
from .. import colors, text as txt
from .._gen.icons import Icons
from ..control import Control
from ..event import fire
from ..text import get_font, get_icon_font
from ..types import LabelPosition, OutlineInputBorder, as_border_radius

_FIELD_H = 48.0
_FIELD_PAD = 12.0
_RADIUS = 8.0
_ITEM_H = 36.0


def _parse(c):
    return colors.parse_color(c)


class TextField(Control):
    def __init__(self, value: str = "", *, label=None, hint_text=None,
                 password: bool = False, multiline: bool = False,
                 max_lines: int | None = None, read_only: bool = False,
                 text_size: float | None = None, on_change=None, on_submit=None,
                 on_focus=None, on_blur=None, on_click=None,
                 filled: bool = False, bgcolor=None, border_color=None,
                 cursor_color=None, border_radius: float | None = None,
                 border=None, text_style=None,
                 can_reveal_password: bool = False, **base):
        super().__init__(**base)
        self.value = value
        self.label = label
        self.hint_text = hint_text
        self.password = password
        self.multiline = multiline
        self.max_lines = max_lines
        self.read_only = read_only
        self.text_size = text_size or 14.0
        self.on_change = on_change
        self.on_submit = on_submit
        self.on_focus = on_focus
        self.on_blur = on_blur
        self.on_click = on_click
        self.filled = filled          # flet flag; saturn always draws filled
        self.bgcolor = bgcolor
        self.border_color = border_color
        self.cursor_color = cursor_color
        self.border_radius = border_radius
        self.border = border
        self.text_style = text_style
        self.can_reveal_password = can_reveal_password
        self._password_revealed = False
        self._caret = len(value)
        self._focused = False
        self._focusable = True

    def _style(self):
        """(family, value size, value color) from the flet text_style."""
        ts = self.text_style
        if ts is None:
            return None, self.text_size, colors.Colors.ON_SURFACE
        return (ts.font_family,
                ts.size or self.text_size,
                ts.color if ts.color is not None else colors.Colors.ON_SURFACE)

    # -- layout --------------------------------------------------------------
    def _intrinsic(self, max_w, max_h, scale):
        w = self._width if self._width is not None else (max_w or 280)
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
        return ("•" * len(self.value)
                if self.password and not self._password_revealed else self.value)

    def _pressed_hook(self, x, y):
        if self.password and self.can_reveal_password:
            rx, _, rw, _ = self._rect
            if x >= rx + rw - 48:
                self._password_revealed = not self._password_revealed
                self.update()

    def _font(self, scale):
        family, vsize, _ = self._style()
        return get_font(vsize, scale=scale, family=family,
                        text=self.value or self.hint_text or self.label)

    def _caret_at(self, x):
        """Place the caret from a pointer x position."""
        scale = self.page._app.renderer.scale if self.page else 1.0
        family, vsize, _ = self._style()
        px = x - (self._rect[0] + _FIELD_PAD)
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
        self._caret = idx
        self.update()

    # -- editing ----------------------------------------------------------------
    def _changed(self):
        self.update()
        fire(self, "change", self.value)

    def _text_input(self, t):
        if self.read_only:
            return
        v = self.value
        self.value = v[:self._caret] + t + v[self._caret:]
        self._caret += len(t)
        self._changed()

    def _key(self, e):
        k = e.key
        v, c = self.value, self._caret
        if k == pygame.K_BACKSPACE and c > 0 and not self.read_only:
            self.value, self._caret = v[:c - 1] + v[c:], c - 1
            self._changed()
        elif k == pygame.K_DELETE and c < len(v) and not self.read_only:
            self.value = v[:c] + v[c + 1:]
            self._changed()
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.multiline and not self.read_only:
                self.value = v[:c] + "\n" + v[c:]
                self._caret = c + 1
                self._changed()
            else:
                fire(self, "submit", self.value)
        elif k == pygame.K_LEFT:
            self._caret = max(0, c - 1)
            self.update()
        elif k == pygame.K_RIGHT:
            self._caret = min(len(v), c + 1)
            self.update()
        elif k == pygame.K_HOME:
            self._caret = 0
            self.update()
        elif k == pygame.K_END:
            self._caret = len(v)
            self.update()

    # -- drawing ------------------------------------------------------------------
    def _draw(self, r, x, y):
        x, y, w, h = self._rect
        scale = r.scale
        outline = self.border if isinstance(self.border, OutlineInputBorder) else None
        radius_value = (outline.border_radius if outline is not None
                        else self.border_radius)
        radius = as_border_radius(
            _RADIUS if radius_value is None else radius_value).top_left
        r.fill_rect(x, y, w, h,
                    _parse(self.bgcolor or colors.Colors.SURFACE_CONTAINER_HIGHEST),
                    radius=radius)
        if outline is not None:
            side = outline.side
            if side.width > 0:
                r.stroke_rect(x, y, w, h,
                              _parse(side.color or colors.Colors.OUTLINE),
                              width=side.width, radius=radius)
        elif self.border_color is not None:
            r.stroke_rect(x, y, w, h, _parse(self.border_color),
                          width=2 if self._focused else 1, radius=radius)
        elif self._focused:
            r.stroke_rect(x, y, w, h, _parse(colors.Colors.PRIMARY),
                          width=2, radius=radius)
        has_label = bool(self.label) and (self._focused or bool(self.value))
        ty = y + 6.0 if has_label else y
        th = h - 12.0 if has_label else h
        family, vsize, vcolor = self._style()
        if has_label:
            r.blit(txt.render_line(self.label, 10, scale=scale, family=family,
                                   color=_parse(colors.Colors.PRIMARY)),
                   x + _FIELD_PAD, y + 6)
        shown = self._visible_text()
        if shown:
            surf = txt.render_line(shown, vsize, scale=scale, family=family,
                                   color=_parse(vcolor))
            r.clip_push(x, y, w, h)
            r.blit(surf, x + _FIELD_PAD, ty + (th - surf.get_height() / scale) / 2)
            r.clip_pop()
        elif self.hint_text:
            surf = txt.render_line(self.hint_text, self.text_size, scale=scale,
                                   family=family,
                                   color=_parse(colors.Colors.ON_SURFACE_VARIANT))
            r.blit(surf, x + _FIELD_PAD, ty + (th - surf.get_height() / scale) / 2)
        if self.password and self.can_reveal_password:
            icon = Icons.VISIBILITY_OFF if self._password_revealed else Icons.VISIBILITY
            af = get_icon_font(round(24 * scale))
            eye = af.render(chr(int(icon)), True,
                            _parse(colors.Colors.ON_SURFACE_VARIANT))
            r.blit(eye, x + w - 32,
                   y + (h - eye.get_height() / scale) / 2)
        if self._focused:
            cx = x + _FIELD_PAD + txt.line_width(shown[:self._caret], vsize,
                                                 scale=scale, family=family)
            r.fill_rect(cx, ty + (th - vsize) / 2, 2, vsize,
                        _parse(self.cursor_color or colors.Colors.PRIMARY))


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

    def _toggle(self, e=None):
        self.value = not self.value
        self._animate_internal("_value_progress", 1.0 if self.value else 0.0,
                               200)
        self.update()
        fire(self, "change", "true" if self.value else "false")

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
        x, y, w, h = self._rect
        box = self._box_size()
        cy = y + h / 2
        first_is_box = self.label_position is not LabelPosition.LEFT
        bw = box
        lw = (w - bw - 8) if self.label else 0.0
        bx = x if first_is_box else x + lw + 8
        lx = x + bw + 8 if first_is_box else x
        self._draw_box(r, bx, cy - box / 2, box)
        if self.label:
            surf = txt.render_line(self.label, 14, scale=r.scale,
                                   color=_parse(colors.Colors.ON_SURFACE))
            r.blit(surf, lx, cy - surf.get_height() / (2 * r.scale))

    def _hit_test(self, x, y):
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)


class Checkbox(_Toggle):
    def _box_size(self):
        return 18.0

    def _draw_box(self, r, x, y, box):
        progress = self._value_progress
        if progress > 0:
            r.opacity_push(progress)
            r.fill_rect(x, y, box, box,
                        _parse(self.active_color or colors.Colors.PRIMARY), radius=2)
            f = get_icon_font(round(14 * r.scale))
            surf = f.render(chr(int(Icons.CHECK)), True, (255, 255, 255, 255))
            r.blit(surf, x + (box - surf.get_width() / r.scale) / 2,
                   y + (box - surf.get_height() / r.scale) / 2)
            r.opacity_pop()
        if progress < 1:
            r.opacity_push(1 - progress)
            r.stroke_rect(x, y, box, box,
                          _parse(colors.Colors.ON_SURFACE_VARIANT),
                          width=2, radius=2)
            r.opacity_pop()


class Switch(_Toggle):
    def _box_size(self):
        return 40.0  # track width

    def _draw_box(self, r, x, y, w):
        h = 20.0
        cy = y + w / 2 if False else y + h / 2  # y already top of track box
        progress = self._value_progress
        active = _parse(self.active_color or colors.Colors.PRIMARY)
        inactive = _parse(colors.Colors.SURFACE_CONTAINER_HIGHEST)
        track_c = tuple(round(a + (b - a) * progress)
                        for a, b in zip(inactive, active))
        r.fill_rect(x, cy, w, h, track_c, radius=h / 2)
        thumb_r = 8.0 + 4.0 * progress
        tx = x + 10.0 + (w - 20.0) * progress
        on_thumb = _parse(colors.Colors.ON_PRIMARY)
        off_thumb = _parse(colors.Colors.OUTLINE)
        tc = tuple(round(a + (b - a) * progress)
                   for a, b in zip(off_thumb, on_thumb))
        r.circle(tx, cy + h / 2, thumb_r, tc)


class RadioGroup(Control):
    def __init__(self, content=None, *, value=None, on_change=None, **base):
        super().__init__(**base)
        self.content = content
        self.value = value
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
        self.update()
        fire(self, "change", radio.value)

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
        x, y, w, h = self._rect
        cy = y + h / 2
        selected = self._group_value() == self.value
        c = _parse(self.active_color or colors.Colors.PRIMARY)
        if selected:
            r.circle(x + 10, cy, 10, c, fill=False)
            r.circle(x + 10, cy, 5, c)
        else:
            r.circle(x + 10, cy, 10, _parse(colors.Colors.ON_SURFACE_VARIANT),
                     fill=False)
        if self.label:
            surf = txt.render_line(self.label, 14, scale=r.scale,
                                   color=_parse(colors.Colors.ON_SURFACE))
            r.blit(surf, x + 28, cy - surf.get_height() / (2 * r.scale))

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

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else (max_w or 300),
                self._height if self._height is not None else 40.0)

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
            v = round(v / step) * step
        v = max(self.min, min(self.max, v))
        return round(v, self.round) if self.round else v

    def _track(self):
        x, y, w, h = self._rect
        return x, w  # track spans full width

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
        x, y, w, h = self._rect
        cy = y + h / 2
        r.fill_rect(x, cy - 2, w, 4,
                    _parse(self.inactive_color or colors.Colors.SURFACE_CONTAINER_HIGHEST),
                    radius=2)
        k = self._k()
        if k > 0:
            r.fill_rect(x, cy - 2, w * k, 4,
                        _parse(self.active_color or colors.Colors.PRIMARY), radius=2)
        r.circle(x + w * k, cy, 10,
                 _parse(self.thumb_color or colors.Colors.PRIMARY))

    def _hit_test(self, x, y):
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)


class DropdownOption(Control):
    """Options hold key/text data; the Dropdown renders them as a menu."""

    def __init__(self, key=None, *, text=None, content=None, **base):
        super().__init__(**base)
        self.key = key if key is not None else (text if text is not None else
                                                str(content))
        self.text = text
        self.content = content


Option = DropdownOption  # legacy flet name


class Dropdown(Control):
    def __init__(self, value=None, *, options=None, hint_text=None, label=None,
                 on_select=None, text_size: float = 14.0, **base):
        super().__init__(**base)
        self.value = value
        self.options = list(options or [])
        self.hint_text = hint_text
        self.label = label
        self.on_select = on_select
        self.text_size = text_size
        self.open = False
        self._menu: list[Control] = []
        self.on_click = self._toggle_menu  # internal routing
        self._hovered = False
        self._pressed = False

    def _selected_text(self):
        for o in self.options:
            if o.key == self.value:
                return o.text or o.key
        return ""

    def _intrinsic(self, max_w, max_h, scale):
        w = self._width if self._width is not None else (max_w or 280)
        return (w, self._height if self._height is not None else _FIELD_H)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        if self.open:
            self._position_menu()

    def _toggle_menu(self, e=None):
        self.open = not self.open
        page = self.page
        if page is not None:
            for it in self._menu:
                if it in page.overlay:
                    page.overlay.remove(it)
            self._menu = []
            if self.open:
                self._build_menu(page)
        self.update()

    def _close_menu(self):
        if not self.open:
            return
        self.open = False
        page = self.page
        if page is not None:
            for it in self._menu:
                if it in page.overlay:
                    page.overlay.remove(it)
        self._menu = []
        self.update()

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
                             padding=8, on_click=pick)
            item._attach(page, self)
            self._menu.append(item)
        self._position_menu()
        page.overlay.extend(self._menu)

    def _position_menu(self):
        x, y, w, h = self._rect
        for i, item in enumerate(self._menu):
            item._rect = (x, y + h + 4 + i * _ITEM_H, w, _ITEM_H)

    def _draw(self, r, x, y):
        x, y, w, h = self._rect
        r.fill_rect(x, y, w, h,
                    _parse(colors.Colors.SURFACE_CONTAINER_HIGHEST), radius=_RADIUS)
        if self.open:
            r.stroke_rect(x, y, w, h, _parse(colors.Colors.PRIMARY),
                          width=2, radius=_RADIUS)
        shown = self._selected_text() or self.hint_text or ""
        c = _parse(colors.Colors.ON_SURFACE if self._selected_text()
                   else colors.Colors.ON_SURFACE_VARIANT)
        surf = txt.render_line(shown, self.text_size, scale=r.scale, color=c)
        r.clip_push(x, y, w, h)
        r.blit(surf, x + _FIELD_PAD,
               y + (h - surf.get_height() / r.scale) / 2)
        r.clip_pop()
        af = get_icon_font(round(24 * r.scale))
        arrow = af.render(chr(int(Icons.KEYBOARD_ARROW_DOWN)), True,
                          _parse(colors.Colors.ON_SURFACE_VARIANT))
        r.blit(arrow, x + w - 32, y + (h - arrow.get_height() / r.scale) / 2)

    def _hit_test(self, x, y):
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)
