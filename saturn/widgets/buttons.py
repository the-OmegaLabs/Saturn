"""Buttons: Button base + Filled/FilledTonal/Elevated/Outlined/Text + IconButton.

flet 1.0 API: label via content= (str or Control), icon=, on_click, on_hover,
color/bgcolor, disabled.
"""
from __future__ import annotations

from .. import colors, motion, text as txt
from ..control import Control
from ..event import fire
from ..text import render_icon_cached
from ._material import (draw_state_layer, init_state_layer, press,
                        release, set_hover, tick_state_layer)

# M3 button metrics
_HEIGHT = 40.0
_PAD_H = 24.0
_GAP = 8.0
_LABEL_SIZE = 14.0
_LABEL_WEIGHT = 500
_ICON_SIZE = 18.0


def _blend(fg, bg, k: float):
    """Linear blend two RGBA tuples; k = amount of fg over bg."""
    return tuple(round(b + (f - b) * k) for f, b in zip(fg, bg))


class Button(Control):
    variant_bg = None     # class defaults, resolved at draw (theme-aware)
    variant_fg = None
    variant_border = None
    variant_elevation = 0.0

    def __init__(self, content=None, *, icon=None, icon_color=None, color=None,
                 bgcolor=None, elevation: float = 1, style=None, on_click=None,
                 on_hover=None, on_long_press=None, on_focus=None, on_blur=None,
                 autofocus=False, url=None, **base):
        super().__init__(**base)
        self.content = content      # str or Control
        self.icon = icon
        self.icon_color = icon_color
        self.color = color
        self.bgcolor = bgcolor
        self.elevation = elevation
        self.style = style
        self.on_click = on_click
        self.on_hover = on_hover
        self.on_long_press = on_long_press
        self.on_focus = on_focus
        self.on_blur = on_blur
        self.autofocus = autofocus
        self.url = url
        self._hovered = False
        self._pressed = False
        self._elevation_progress = self.variant_elevation
        init_state_layer(self)

    # -- metrics -----------------------------------------------------------
    def _label(self) -> str:
        return self.content if isinstance(self.content, str) else ""

    def _intrinsic(self, max_w, max_h, scale):
        w, h = 0.0, _HEIGHT
        if label := self._label():
            lw, lh = txt.measure(label, _LABEL_SIZE, scale=scale,
                                 weight=_LABEL_WEIGHT)
            w += lw
            h = max(h, lh + 20)
        elif isinstance(self.content, Control):
            cw, ch = self.content._intrinsic(max_w, max_h, scale)
            w += cw
            h = max(h, ch + 20)
        if self.icon is not None:
            w += _ICON_SIZE + (_GAP if w else 0)
        # Material buttons with a leading icon use 16px at the start and
        # 24px at the end. Text-only buttons use 24px on both sides.
        w += (16.0 if self.icon is not None else _PAD_H) + _PAD_H
        if self._width is not None:
            w = self._width
        if self._height is not None:
            h = self._height
        return w, h

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        if isinstance(self.content, Control):
            # center the child control at its intrinsic size
            cw, ch = self.content._intrinsic(w, h, scale)
            self.content._place(x + (w - cw) / 2, y + (h - ch) / 2, cw, ch, scale)

    # -- colors ------------------------------------------------------------
    def _resolve(self, name, fallback):
        v = getattr(self, name)
        if v is None:
            v = fallback
        return colors.parse_color(v) if v is not None else None

    def _bg(self):
        if self.bgcolor is not None:
            base = colors.parse_color(self.bgcolor)
        elif self.variant_bg is not None:
            base = colors.parse_color(self.variant_bg)
        else:
            return None
        return base

    def _fg_raw(self):
        return self.color or self.variant_fg or colors.Colors.ON_SURFACE

    def _fg(self):
        fg = colors.parse_color(self._fg_raw())
        if self.disabled:
            return _blend(fg, (128, 128, 128, 255), 0.62)
        return fg

    # -- drawing -----------------------------------------------------------
    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        bg = self._bg()
        elevation = self._elevation_progress
        if elevation > 0 and not self.disabled:
            shadow_alpha = round(18 + 8 * elevation)
            r.overlay_rect(x - elevation, y + elevation,
                           w + 2 * elevation, h + elevation,
                           (0, 0, 0, shadow_alpha), radius=h / 2 + elevation)
        if bg is not None:
            r.fill_rect(x, y, w, h, bg, radius=h / 2)
        if self.variant_border is not None and not self.disabled:
            r.stroke_rect(x, y, w, h, colors.parse_color(self.variant_border),
                          width=1, radius=h / 2)
        if not self.disabled:
            draw_state_layer(self, r, (x, y, w, h), self._fg_raw(), h / 2)
        # content: [icon] gap [label/control]
        scale = r.scale
        icon_surf = label_surf = None
        label_w = icon_w = 0.0
        if self.icon is not None:
            icon_surf = render_icon_cached(
                self.icon, round(_ICON_SIZE * scale), self._fg())
            icon_w = icon_surf.get_width() / scale
        if label := self._label():
            label_surf = txt.render_line_cached(
                label, _LABEL_SIZE, scale=scale, weight=_LABEL_WEIGHT,
                color=self._fg())
            label_w = label_surf.get_width() / scale
        elif isinstance(self.content, Control):
            label_w = self.content._rect[2]
        total = icon_w + ((_GAP) if icon_w and label_w else 0) + label_w
        pad_start = 16.0 if self.icon is not None else _PAD_H
        content_w = w - pad_start - _PAD_H
        cx = x + pad_start + (content_w - total) / 2
        cy = y + h / 2
        if icon_surf is not None:
            r.blit(icon_surf, cx, cy - icon_surf.get_height() / (2 * scale))
            cx += icon_w + _GAP
        if label_surf is not None:
            r.blit(label_surf, cx, cy - label_surf.get_height() / (2 * scale))

    def _draw_all(self, r, ox: float = 0.0, oy: float = 0.0):
        if not self.visible:
            return
        self._effects_begin(r)
        try:
            self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
            if isinstance(self.content, Control):
                self.content._draw_all(r, ox, oy)
        finally:
            self._effects_end(r)

    # -- pointer hooks (page routes through here) --------------------------
    def _hit_test(self, x, y):
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        if self.variant_elevation:
            self._animate_internal(
                "_elevation_progress", 2.0 if on else self.variant_elevation,
                motion.SHORT3, motion.EMPHASIZED)
        self.update()
        fire(self, "hover", "true" if on else "false")

    def _pressed_hook(self, x, y):
        press(self, x, y, ripple_duration=motion.SHORT4,
              press_duration=75)
        if self.variant_elevation:
            self._animate_internal("_elevation_progress", 1.0, motion.SHORT3,
                                   motion.EMPHASIZED)

    def _released_hook(self, _x, _y):
        release(self, minimum_ms=0, fade_duration=motion.SHORT2)
        if self.variant_elevation:
            self._animate_internal(
                "_elevation_progress",
                2.0 if self._hovered else self.variant_elevation,
                motion.SHORT3, motion.EMPHASIZED)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        return super()._tick_animations(now) or waiting


class FilledButton(Button):
    variant_bg = colors.Colors.PRIMARY
    variant_fg = colors.Colors.ON_PRIMARY


class FilledTonalButton(Button):
    variant_bg = colors.Colors.SECONDARY_CONTAINER
    variant_fg = colors.Colors.ON_SECONDARY_CONTAINER


class ElevatedButton(Button):
    variant_bg = colors.Colors.SURFACE_CONTAINER_LOW
    variant_fg = colors.Colors.PRIMARY
    variant_elevation = 1.0


class OutlinedButton(Button):
    variant_bg = None
    variant_fg = colors.Colors.PRIMARY
    variant_border = colors.Colors.OUTLINE


class TextButton(Button):
    variant_bg = None
    variant_fg = colors.Colors.PRIMARY


# Flet 1.0 renamed ElevatedButton to Button. Its defaults remain the Material
# elevated-button surface/elevation rather than a high-emphasis filled button.
class _ConcreteButton(Button):
    variant_bg = colors.Colors.SURFACE_CONTAINER_LOW
    variant_fg = colors.Colors.PRIMARY
    variant_elevation = 1.0


Button = _ConcreteButton


class IconButton(Control):
    def __init__(self, icon, *, icon_size: float = 24, icon_color=None,
                 selected_icon=None, selected=False, bgcolor=None,
                 hover_color=None, tooltip=None, on_click=None, on_hover=None,
                 **base):
        super().__init__(tooltip=tooltip, **base)
        self.icon = icon
        self.icon_size = icon_size
        self.icon_color = icon_color
        self.selected_icon = selected_icon
        self.selected = selected
        self.bgcolor = bgcolor
        self.hover_color = hover_color
        self.on_click = on_click
        self.on_hover = on_hover
        self._hovered = False
        self._pressed = False
        init_state_layer(self)

    def _intrinsic(self, max_w, max_h, scale):
        s = self._width if self._width is not None else 40.0
        h = self._height if self._height is not None else 40.0
        return s, h

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _current_icon(self):
        if self.selected and self.selected_icon is not None:
            return self.selected_icon
        return self.icon

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        fg = colors.parse_color(
            self.icon_color or colors.Colors.ON_SURFACE_VARIANT)
        if self.bgcolor is not None:
            r.fill_rect(x, y, w, h, colors.parse_color(self.bgcolor),
                        radius=min(w, h) / 2)
        state_color = (self.hover_color or self.icon_color or
                       colors.Colors.ON_SURFACE_VARIANT)
        draw_state_layer(self, r, (x, y, w, h), state_color, min(w, h) / 2)
        surf = render_icon_cached(
            self._current_icon(), round(self.icon_size * r.scale), fg)
        r.blit(surf, x + (w - surf.get_width() / r.scale) / 2,
               y + (h - surf.get_height() / r.scale) / 2)

    def _hit_test(self, x, y):
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        self.update()
        fire(self, "hover", "true" if on else "false")

    def _pressed_hook(self, x, y):
        press(self, x, y, ripple_duration=motion.SHORT4,
              press_duration=75)

    def _released_hook(self, _x, _y):
        release(self, minimum_ms=0, fade_duration=motion.SHORT2)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        return super()._tick_animations(now) or waiting
