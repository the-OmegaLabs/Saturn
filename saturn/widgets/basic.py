"""Basic visual controls: Icon, Image, Card, ProgressBar, ProgressRing."""
from __future__ import annotations

import base64
from pathlib import Path

import pygame

from .containers import Container
from .. import colors
from ..control import Control
from ..text import get_icon_font
from ..types import BoxFit

ASSETS = Path(__file__).parent.parent / "assets"
_img_cache: dict = {}


class Icon(Control):
    def __init__(self, icon, *, color=None, size: float = 24, **base):
        super().__init__(**base)
        self.icon = icon            # Icons member (codepoint int)
        self.color = color          # None → on_surface
        self.size = size

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else self.size,
                self._height if self._height is not None else self.size)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        f = get_icon_font(round(self.size * r.scale))
        surf = f.render(chr(int(self.icon)), True,
                        colors.parse_color(self.color or colors.Colors.ON_SURFACE))
        r.blit(surf, x, y)


class Image(Control):
    def __init__(self, src=None, *, fit=None, border_radius=None, **base):
        super().__init__(**base)
        self.src = src              # file path, bytes, or data:base64 URI
        self.fit = fit              # v1: None/BoxFit.FILL stretch, CONTAIN fits
        self.border_radius = border_radius
        self._surface = None
        self._loaded_key = None

    def _load(self):
        if self.src is None:
            return None
        key = self.src if isinstance(self.src, (str, bytes)) else id(self.src)
        if key == self._loaded_key:
            return self._surface
        if isinstance(self.src, bytes):
            s = pygame.image.load(self.src)
        elif isinstance(self.src, str) and self.src.startswith("data:"):
            b64 = self.src.split(",", 1)[1]
            s = pygame.image.load(base64.b64decode(b64))
        else:
            s = pygame.image.load(self.src)
        self._surface = s.convert_alpha()
        self._loaded_key = key
        return self._surface

    def _intrinsic(self, max_w, max_h, scale):
        s = self._load()
        nw, nh = s.get_size() if s else (0, 0)
        w = self._width if self._width is not None else \
            (nw / nh * self._height if self._height is not None and nh else nw)
        h = self._height if self._height is not None else \
            (nh / nw * self._width if self._width is not None and nw else nh)
        return w, h

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        s = self._load()
        if s is None:
            return
        x, y, w, h = self._rect
        tw, th = int(w * r.scale), int(h * r.scale)
        if tw <= 0 or th <= 0:
            return
        sw, sh = s.get_size()
        if self.fit is BoxFit.CONTAIN and sw and sh:
            k = min(tw / sw, th / sh)
            dw, dh = int(sw * k), int(sh * k)
            s2 = pygame.transform.smoothscale(s, (dw, dh))
            r.blit(s2, x + (w - dw / r.scale) / 2, y + (h - dh / r.scale) / 2)
        else:
            r.blit(pygame.transform.smoothscale(s, (tw, th)), x, y)


class Card(Container):
    """flet Card: container with M3 card styling (flat v1 — no blur shadow)."""

    def __init__(self, content=None, *, elevation: float = 1,
                 variant: str = "elevated", **base):
        self.elevation = elevation
        self.variant = variant
        base.setdefault("bgcolor", colors.Colors.SURFACE_CONTAINER_LOW)
        super().__init__(content, **base)


class ProgressBar(Control):
    def __init__(self, value: float | None = None, *, bar_height: float = 4,
                 color=None, bgcolor=None, border_radius=None, **base):
        super().__init__(**base)
        self.value = value
        self.bar_height = bar_height
        self.color = color
        self.bgcolor = bgcolor
        self.border_radius = border_radius
        # ponytail: indeterminate is a static stub; animate via frame clock later

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else (max_w or 100),
                self._height if self._height is not None else self.bar_height)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        x, y, w, h = self._rect
        v = self.value if self.value is not None else 0.35
        r.fill_rect(x, y, w, h,
                    colors.parse_color(self.bgcolor or colors.Colors.SURFACE_CONTAINER_HIGHEST),
                    radius=h / 2)
        if v > 0:
            r.fill_rect(x, y, w * min(1.0, v), h,
                        colors.parse_color(self.color or colors.Colors.PRIMARY),
                        radius=h / 2)


class ProgressRing(Control):
    def __init__(self, value: float | None = None, *, stroke_width: float = 4,
                 color=None, bgcolor=None, **base):
        super().__init__(**base)
        self.value = value
        self.stroke_width = stroke_width
        self.color = color
        self.bgcolor = bgcolor

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else 36,
                self._height if self._height is not None else 36)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        x, y, w, h = self._rect
        cx, cy = x + w / 2, y + h / 2
        radius = min(w, h) / 2 - self.stroke_width / 2
        import math
        r.circle(cx, cy, radius,
                 colors.parse_color(self.bgcolor or colors.Colors.SURFACE_CONTAINER_HIGHEST),
                 fill=False)
        v = self.value if self.value is not None else 0.25
        if v > 0:
            # pygame arc angles: 0 = +x axis, counterclockwise (y-down: visually clockwise)
            start = math.pi / 2  # top
            r.arc(cx, cy, radius, start, start + 2 * math.pi * min(1.0, v),
                  colors.parse_color(self.color or colors.Colors.PRIMARY),
                  width=self.stroke_width)
