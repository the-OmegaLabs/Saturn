"""Expressive floating action buttons, measured in logical pixels."""
from __future__ import annotations

from .. import colors, motion, text as txt
from ..event import fire
from ..text import render_icon_cached
from ..painting import draw_shadow
from ._material import draw_state_layer, press, release, set_hover
from .buttons import Button


# (square side, corner radius, icon size, extended height, leading/trailing
# padding, icon-label gap, label size, label weight). The medium and large
# icon-label gaps and the large icon size are explicit per-size values.
_SIZES = {
    "small": (40.0, 12.0, 24.0, 56.0, 16.0, 8.0, 16.0, 500),
    "standard": (56.0, 16.0, 24.0, 56.0, 16.0, 12.0, 14.0, 500),
    "medium": (80.0, 20.0, 28.0, 80.0, 26.0, 12.0, 22.0, 400),
    "large": (96.0, 28.0, 36.0, 96.0, 28.0, 16.0, 24.0, 400),
}
_EXTENDED_ICON_SIZES = {"large": 32.0}


class FloatingActionButton(Button):
    """Material 3 FAB. Add ``text`` for the extended icon-and-label form.

    ``size`` is ``small`` (40), ``standard`` (56), ``medium`` (80), or
    ``large`` (96). Extended versions use heights 56/56/80/96 respectively.
    ``expanded=False`` shows only the icon at the square FAB size.
    """

    variant_bg = colors.Colors.PRIMARY_CONTAINER
    variant_fg = colors.Colors.ON_PRIMARY_CONTAINER
    variant_elevation = 6.0

    def __init__(self, icon=None, *, content: str | None = None,
                 text: str | None = None, mini: bool = False,
                 size: str = "standard", expanded: bool = True,
                 bgcolor=None, color=None, foreground_color=None,
                 elevation: float = 6.0,
                 on_click=None, on_hover=None, **base):
        if text is None:
            text = content
        if text is not None and not isinstance(text, str):
            raise TypeError("FAB content must be text")
        if mini and size == "standard":
            size = "small"
        if size not in _SIZES:
            raise ValueError(f"invalid FAB size: {size!r}")
        if not expanded and icon is None:
            raise ValueError("a collapsed extended FAB needs an icon")
        self.mini = mini
        self.foreground_color = foreground_color
        self.size = size
        self.text = text
        self.expanded = expanded
        self._base_elevation = max(0.0, float(elevation))
        super().__init__(content=text, icon=icon, bgcolor=bgcolor,
                         color=color if color is not None else foreground_color,
                         elevation=elevation, on_click=on_click, on_hover=on_hover,
                         **base)
        self._elevation_progress = self._base_elevation

    def _metrics(self):
        return _SIZES[self.size]

    def _extended(self):
        return bool(self.text) and (self.expanded or self.icon is None)

    def _intrinsic(self, max_w, max_h, scale):
        side, _, icon_size, extended_h, pad, gap, label_size, label_weight = self._metrics()
        if not self._extended():
            width = height = side
        else:
            icon_size = _EXTENDED_ICON_SIZES.get(self.size, icon_size)
            label_w, _ = txt.measure(self.text, label_size, scale=scale,
                                     weight=label_weight)
            if self.icon is None:
                # Text-only extended FAB has 20dp horizontal padding
                # and an 80dp minimum width.
                pad = 20.0 if self.size == "standard" else pad
                width = max(80.0 if self.size == "standard" else extended_h,
                            label_w + 2 * pad)
            else:
                end_pad = 20.0 if self.size == "standard" else pad
                width = max(extended_h, pad + icon_size + gap + label_w + end_pad)
            height = extended_h
        return (self._width if self._width is not None else width,
                self._height if self._height is not None else height)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        _, radius, icon_size, _, pad, gap, label_size, label_weight = self._metrics()
        extended = self._extended()
        if extended:
            icon_size = _EXTENDED_ICON_SIZES.get(self.size, icon_size)
            if self.size == "small":
                radius = 16.0
        radius = min(radius, w / 2, h / 2)
        bg = self._bg()
        fg = self._fg()
        elevation = self._elevation_progress
        if elevation > 0 and not self.disabled:
            draw_shadow(r, (x, y, w, h), radius, elevation)
        if bg is not None:
            r.fill_rect(x, y, w, h, bg, radius=radius)
        if not self.disabled:
            draw_state_layer(self, r, (x, y, w, h), self._fg_raw(), radius)

        scale = r.scale
        icon_surf = (render_icon_cached(self.icon, round(icon_size * scale), fg)
                     if self.icon is not None else None)
        label_surf = (txt.render_line_cached(self.text, label_size, scale=scale,
                                             weight=label_weight, color=fg)
                      if extended else None)
        icon_w = icon_surf.get_width() / scale if icon_surf is not None else 0.0
        label_w = label_surf.get_width() / scale if label_surf is not None else 0.0
        total_w = icon_w + (gap if icon_w and label_w else 0.0) + label_w
        if extended:
            leading = 20.0 if self.icon is None and self.size == "standard" else pad
            trailing = 20.0 if self.size == "standard" else pad
            cx = x + (w - leading - total_w - trailing) / 2 + leading
        else:
            cx = x + (w - total_w) / 2
        cy = y + h / 2
        if icon_surf is not None:
            r.blit_cached(icon_surf, cx, cy - icon_surf.get_height() / (2 * scale),
                   alpha=0.38 if self.disabled else 1.0)
            cx += icon_w + (gap if label_surf is not None else 0.0)
        if label_surf is not None:
            r.blit_cached(label_surf, cx, cy - label_surf.get_height() / (2 * scale),
                   alpha=0.38 if self.disabled else 1.0)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        self._animate_internal("_elevation_progress",
                               self._base_elevation + (2.0 if on else 0.0),
                               motion.SHORT3, motion.EMPHASIZED)
        self.update()
        fire(self, "hover", "true" if on else "false")

    def _pressed_hook(self, x, y):
        press(self, x, y, ripple_duration=motion.SHORT4, press_duration=75)
        self._animate_internal("_elevation_progress", self._base_elevation,
                               motion.SHORT3, motion.EMPHASIZED)

    def _released_hook(self, _x, _y):
        release(self, minimum_ms=0, fade_duration=motion.SHORT2)
        self._animate_internal("_elevation_progress",
                               self._base_elevation + (2.0 if self._hovered else 0.0),
                               motion.SHORT3, motion.EMPHASIZED)


class SmallFloatingActionButton(FloatingActionButton):
    def __init__(self, icon=None, **kwargs):
        super().__init__(icon, size="small", **kwargs)


class MediumFloatingActionButton(FloatingActionButton):
    def __init__(self, icon=None, **kwargs):
        super().__init__(icon, size="medium", **kwargs)


class LargeFloatingActionButton(FloatingActionButton):
    def __init__(self, icon=None, **kwargs):
        super().__init__(icon, size="large", **kwargs)


class ExtendedFloatingActionButton(FloatingActionButton):
    def __init__(self, text: str, *, icon=None, size: str = "standard", **kwargs):
        super().__init__(icon, text=text, size=size, **kwargs)
