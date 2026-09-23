"""Buttons: Button base + Filled/FilledTonal/Elevated/Outlined/Text + IconButton.

flet 1.0 API: label via content= (str or Control), icon=, on_click, on_hover,
color/bgcolor, disabled.
"""
from __future__ import annotations

from .. import colors, motion, text as txt
from ..control import Control
from ..event import fire
from ..text import render_icon_cached
from ..painting import draw_shadow
from ._material import (draw_state_layer, init_state_layer, press,
                        release, set_hover, tick_state_layer)

# M3 button metrics
_HEIGHT = 40.0
_PAD_H = 24.0
_GAP = 8.0
_LABEL_SIZE = 14.0
_LABEL_WEIGHT = 500
_ICON_SIZE = 18.0

# Expressive button dimensions. Each entry is
# (height, horizontal padding, icon, gap, text size, weight,
#  square corner, pressed corner). Extra-small padding/spacing is 12/4.
_EXPRESSIVE_SIZES = {
    "xsmall": (32.0, 12.0, 20.0, 4.0, 14.0, 500, 12.0, 8.0),
    "small": (40.0, 16.0, 20.0, 8.0, 14.0, 500, 12.0, 8.0),
    "medium": (56.0, 24.0, 24.0, 8.0, 16.0, 500, 16.0, 12.0),
    "large": (96.0, 48.0, 32.0, 12.0, 24.0, 400, 28.0, 16.0),
    "xlarge": (136.0, 64.0, 40.0, 16.0, 32.0, 400, 28.0, 16.0),
}


class Button(Control):
    variant_bg = None     # class defaults, resolved at draw (theme-aware)
    variant_fg = None
    variant_border = None
    variant_elevation = 0.0

    def __init__(self, content=None, *, icon=None, icon_color=None, color=None,
                 bgcolor=None, elevation: float = 1, style=None, on_click=None,
                 on_hover=None, on_long_press=None, on_focus=None, on_blur=None,
                 autofocus=False, url=None, expressive=False, size=None,
                 shape="round", **base):
        super().__init__(**base)
        self.expressive = bool(expressive or size is not None)
        self.button_size = (size or "small").replace("_", "").lower()
        if self.expressive and self.button_size not in _EXPRESSIVE_SIZES:
            raise ValueError(f"invalid expressive button size: {size!r}")
        if shape not in ("round", "square"):
            raise ValueError(f"invalid expressive button shape: {shape!r}")
        self.button_shape = shape
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
        self._shape_progress = 0.0
        init_state_layer(self)

    def _metrics(self):
        return (_EXPRESSIVE_SIZES[self.button_size] if self.expressive else
                (_HEIGHT, _PAD_H, _ICON_SIZE, _GAP, _LABEL_SIZE,
                 _LABEL_WEIGHT, _HEIGHT / 2, _HEIGHT / 2))

    def _radius(self, height):
        if not self.expressive:
            return height / 2
        _, _, _, _, _, _, square, pressed = self._metrics()
        normal = height / 2 if self.button_shape == "round" else square
        return normal + (pressed - normal) * self._shape_progress

    # -- metrics -----------------------------------------------------------
    def _label(self) -> str:
        return self.content if isinstance(self.content, str) else ""

    def _intrinsic(self, max_w, max_h, scale):
        token_h, pad, icon_size, gap, label_size, label_weight, _, _ = self._metrics()
        w, h = 0.0, token_h
        if label := self._label():
            lw, lh = txt.measure(label, label_size, scale=scale,
                                 weight=label_weight)
            w += lw
            if not self.expressive:
                h = max(h, lh + 20)
        elif isinstance(self.content, Control):
            cw, ch = self.content._intrinsic(max_w, max_h, scale)
            w += cw
            h = max(h, ch + 20)
        if self.icon is not None:
            w += icon_size + (gap if w else 0)
        # Baseline leading-icon buttons use 16/24; Expressive sizes have
        # symmetric content padding from ButtonDefaults.contentPaddingFor.
        start = pad if self.expressive or self.icon is None else 16.0
        w += start + pad
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
        if self.disabled and (self.bgcolor is not None or self.variant_bg is not None):
            r, g, b, _ = colors.parse_color(colors.Colors.ON_SURFACE)
            return r, g, b, round(255 * 0.10)
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
        if self.disabled:
            return colors.parse_color(colors.Colors.ON_SURFACE_VARIANT)
        return colors.parse_color(self._fg_raw())

    # -- drawing -----------------------------------------------------------
    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        _, pad, icon_size, gap, label_size, label_weight, _, _ = self._metrics()
        radius = self._radius(h)
        bg = self._bg()
        elevation = self._elevation_progress
        if elevation > 0 and not self.disabled:
            draw_shadow(r, (x, y, w, h), radius, elevation)
        if bg is not None:
            r.fill_rect(x, y, w, h, bg, radius=radius)
        if self.variant_border is not None:
            border = (colors.Colors.OUTLINE_VARIANT if self.disabled
                      else self.variant_border)
            r.stroke_rect(x, y, w, h, colors.parse_color(border),
                          width=1, radius=radius)
        if not self.disabled:
            draw_state_layer(self, r, (x, y, w, h), self._fg_raw(), radius)
        # content: [icon] gap [label/control]
        scale = r.scale
        icon_surf = label_surf = None
        label_w = icon_w = 0.0
        if self.icon is not None:
            icon_surf = render_icon_cached(
                self.icon, round(icon_size * scale),
                colors.parse_color(self.icon_color)
                if self.icon_color and not self.disabled else self._fg())
            icon_w = icon_surf.get_width() / scale
        if label := self._label():
            label_surf = txt.render_line_cached(
                label, label_size, scale=scale, weight=label_weight,
                color=self._fg())
            label_w = label_surf.get_width() / scale
        elif isinstance(self.content, Control):
            label_w = self.content._rect[2]
        total = icon_w + (gap if icon_w and label_w else 0) + label_w
        pad_start = pad if self.expressive or self.icon is None else 16.0
        content_w = w - pad_start - pad
        cx = x + pad_start + (content_w - total) / 2
        cy = y + h / 2
        if icon_surf is not None:
            r.blit_cached(icon_surf, cx, cy - icon_surf.get_height() / (2 * scale),
                   alpha=0.38 if self.disabled else 1.0)
            cx += icon_w + (gap if label_w else 0)
        if label_surf is not None:
            r.blit_cached(label_surf, cx, cy - label_surf.get_height() / (2 * scale),
                   alpha=0.38 if self.disabled else 1.0)

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
                "_elevation_progress", 3.0 if on else self.variant_elevation,
                motion.SHORT3, motion.EMPHASIZED)
        self.repaint()
        fire(self, "hover", "true" if on else "false")

    def _pressed_hook(self, x, y):
        press(self, x, y, ripple_duration=motion.SHORT4,
              press_duration=75)
        if self.expressive:
            self._animate_internal("_shape_progress", 1.0, motion.SHORT2,
                                   motion.EMPHASIZED)
        if self.variant_elevation:
            self._animate_internal("_elevation_progress", 1.0, motion.SHORT3,
                                   motion.EMPHASIZED)

    def _released_hook(self, _x, _y):
        release(self, minimum_ms=0, fade_duration=motion.SHORT2)
        if self.expressive:
            self._animate_internal("_shape_progress", 0.0, motion.SHORT2,
                                   motion.EMPHASIZED)
        if self.variant_elevation:
            self._animate_internal(
                "_elevation_progress",
                3.0 if self._hovered else self.variant_elevation,
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
    variant_fg = colors.Colors.ON_SURFACE_VARIANT
    variant_border = colors.Colors.OUTLINE_VARIANT


class TextButton(Button):
    variant_bg = None
    variant_fg = colors.Colors.PRIMARY


class ExpressiveButton(Button):
    """Expressive button with size tokens and pressed shape morph."""
    variant_bg = colors.Colors.PRIMARY
    variant_fg = colors.Colors.ON_PRIMARY

    def __init__(self, content=None, *, size="small", shape="round", **kwargs):
        super().__init__(content, size=size, shape=shape, **kwargs)


# Flet 1.0 renamed ElevatedButton to Button. Its defaults remain the Material
# elevated-button surface/elevation rather than a high-emphasis filled button.
class _ConcreteButton(Button):
    variant_bg = colors.Colors.SURFACE_CONTAINER_LOW
    variant_fg = colors.Colors.PRIMARY
    variant_elevation = 1.0


Button = _ConcreteButton


class IconButton(Control):
    def __init__(self, icon, *, icon_size: float | None = None, icon_color=None,
                 selected_icon=None, selected=False, bgcolor=None,
                 hover_color=None, tooltip=None, on_click=None, on_hover=None,
                 expressive=False, size=None, shape="round", **base):
        super().__init__(tooltip=tooltip, **base)
        self.expressive = bool(expressive or size is not None)
        self.button_size = (size or "small").replace("_", "").lower()
        if self.button_size not in _EXPRESSIVE_SIZES or shape not in ("round", "square"):
            raise ValueError("invalid expressive icon button size or shape")
        self.button_shape = shape
        self.icon = icon
        default_icon = {"xsmall": 20, "small": 24, "medium": 24,
                        "large": 32, "xlarge": 40}[self.button_size]
        self.icon_size = icon_size if icon_size is not None else default_icon
        self.icon_color = icon_color
        self.selected_icon = selected_icon
        self.selected = selected
        self.bgcolor = bgcolor
        self.hover_color = hover_color
        self.on_click = on_click
        self.on_hover = on_hover
        self._hovered = False
        self._pressed = False
        self._shape_progress = 0.0
        self._selected_progress = float(bool(selected))
        self._last_selected = bool(selected)
        init_state_layer(self)

    def _intrinsic(self, max_w, max_h, scale):
        side = _EXPRESSIVE_SIZES[self.button_size][0] if self.expressive else 40.0
        s = self._width if self._width is not None else side
        h = self._height if self._height is not None else side
        return s, h

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _current_icon(self):
        if self.selected and self.selected_icon is not None:
            return self.selected_icon
        return self.icon

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        radius = min(w, h) / 2
        if self.expressive:
            square, pressed = _EXPRESSIVE_SIZES[self.button_size][-2:]
            normal, selected = ((radius, square) if self.button_shape == "round"
                                else (square, radius))
            radius = normal + (selected - normal) * self._selected_progress
            radius += (pressed - radius) * self._shape_progress
        role = (colors.Colors.ON_SURFACE if self.disabled else self.icon_color or
                (colors.Colors.PRIMARY if self.selected else colors.Colors.ON_SURFACE_VARIANT))
        fg = colors.parse_color(role)
        if self.bgcolor is not None:
            r.fill_rect(x, y, w, h, colors.parse_color(self.bgcolor),
                        radius=radius)
        state_color = self.hover_color or role
        if not self.disabled:
            draw_state_layer(self, r, (x, y, w, h), state_color, radius)
        surf = render_icon_cached(
            self._current_icon(), round(self.icon_size * r.scale), fg)
        r.blit_cached(surf, x + (w - surf.get_width() / r.scale) / 2,
               y + (h - surf.get_height() / r.scale) / 2,
               alpha=.38 if self.disabled else 1.0)

    def _hit_test(self, x, y):
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        self.repaint()
        fire(self, "hover", "true" if on else "false")

    def _pressed_hook(self, x, y):
        press(self, x, y, ripple_duration=motion.SHORT4,
              press_duration=75)
        if self.expressive:
            self._animate_internal("_shape_progress", 1.0, motion.SHORT2,
                                   motion.EMPHASIZED)

    def _released_hook(self, _x, _y):
        release(self, minimum_ms=0, fade_duration=motion.SHORT2)
        if self.expressive:
            self._animate_internal("_shape_progress", 0.0, motion.SHORT2,
                                   motion.EMPHASIZED)

    def _prepare_animations(self, now):
        super()._prepare_animations(now)
        if bool(self.selected) != self._last_selected:
            self._last_selected = bool(self.selected)
            self._animate_internal("_selected_progress", float(bool(self.selected)),
                                   motion.SHORT3, motion.EMPHASIZED, now=now)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        return super()._tick_animations(now) or waiting


class ExpressiveIconButton(IconButton):
    def __init__(self, icon, *, size="small", **kwargs):
        super().__init__(icon, size=size, **kwargs)
