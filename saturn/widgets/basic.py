"""Basic visual controls: Icon, Image, Card, ProgressBar, ProgressRing."""
from __future__ import annotations

import base64
import math
import time
from pathlib import Path

import pygame

from .containers import Container
from .. import colors
from .. import motion
from ..animation import _cubic_bezier, ease
from ..control import Control
from ..text import get_icon_font
from ..types import AnimationCurve, BoxFit

ASSETS = Path(__file__).parent.parent / "assets"
_img_cache: dict = {}


def _as_alpha_surface(surface: pygame.Surface) -> pygame.Surface:
    """Return an RGBA surface without consulting pygame.display.

    ``Surface.convert_alpha()`` still relies on the legacy display module's
    pixel format.  Saturn creates windows through ``pygame.Window`` instead,
    and OpenGL windows intentionally have no display-module surface.  Blitting
    into an explicit SRCALPHA surface performs the only conversion we need and
    works for both software and OpenGL windows.
    """
    if surface.get_flags() & pygame.SRCALPHA:
        return surface
    converted = pygame.Surface(surface.get_size(), pygame.SRCALPHA, 32)
    converted.blit(surface, (0, 0))
    return converted


def _segment(t, start_t, end_t, start_value, end_value, curve):
    if t <= start_t:
        return start_value
    if t >= end_t:
        return end_value
    local = (t - start_t) / (end_t - start_t)
    if curve is not None:
        local = _cubic_bezier(local, *curve)
    return start_value + (end_value - start_value) * local


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
        self._surface = _as_alpha_surface(s)
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
        _, _, w, h = self._rect
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
    """Flet Card with Compose Material 3 elevated/filled/outlined surfaces."""

    def __init__(self, content=None, *, elevation: float = 1,
                 variant: str = "elevated", **base):
        from ..types import Border, BoxShadow, Offset

        self.elevation = elevation
        self.variant = variant
        base.setdefault("border_radius", 12)
        if variant == "filled":
            base.setdefault("bgcolor", colors.Colors.SURFACE_CONTAINER_HIGHEST)
        elif variant == "outlined":
            base.setdefault("bgcolor", colors.Colors.SURFACE)
            base.setdefault("border", Border.all(1, colors.Colors.OUTLINE_VARIANT))
        else:
            base.setdefault("bgcolor", colors.Colors.SURFACE_CONTAINER_LOW)
            if elevation > 0:
                base.setdefault("shadow", BoxShadow(
                    blur_radius=3 * elevation, offset=Offset(0, elevation),
                    color="#33000000"))
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
        self._display_value = 0.0 if value is None else float(value)
        self._last_value = value
        self._phase_started = time.perf_counter()
        self._phase = 0.0

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else (max_w or 100),
                self._height if self._height is not None else self.bar_height)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        track = colors.parse_color(self.bgcolor or colors.Colors.SECONDARY_CONTAINER)
        active = colors.parse_color(self.color or colors.Colors.PRIMARY)

        def segment(left, right, color):
            width = right - left
            if width > 0:
                r.fill_rect(left, y, width, h, color,
                            radius=min(h / 2, width / 2))

        if self.value is None:
            phase = self._phase
            # Exact Material Web 2s keyframe geometry: two independently
            # translating and scaling bars, clipped by the track.
            p_tx = (0.0 if phase <= 0.2 else
                    _segment(phase, 0.2, 0.5915, 0.0, 0.836714,
                             (0.5, 0.0, 0.701732, 0.495819)) if phase <= 0.5915
                    else _segment(phase, 0.5915, 1.0, 0.836714, 2.00611,
                                  (0.302435, 0.381352, 0.55, 0.956352)))
            p_scale = (0.08 if phase <= 0.3665 else
                       _segment(phase, 0.3665, 0.6915, 0.08, 0.661479,
                                (0.334731, 0.12482, 0.785844, 1.0))
                       if phase <= 0.6915 else
                       _segment(phase, 0.6915, 1.0, 0.661479, 0.08,
                                (0.06, 0.11, 0.6, 1.0)))
            s_tx = (_segment(phase, 0.0, 0.25, 0.0, 0.376519,
                             (0.15, 0.0, 0.515058, 0.409685))
                    if phase <= 0.25 else
                    _segment(phase, 0.25, 0.4835, 0.376519, 0.843862,
                             (0.31033, 0.284058, 0.8, 0.733712))
                    if phase <= 0.4835 else
                    _segment(phase, 0.4835, 1.0, 0.843862, 1.60278,
                             (0.4, 0.627035, 0.6, 0.902026)))
            s_scale = (_segment(phase, 0.0, 0.1915, 0.08, 0.457104,
                                (0.205028, 0.057051, 0.57661, 0.453971))
                       if phase <= 0.1915 else
                       _segment(phase, 0.1915, 0.4415, 0.457104, 0.72796,
                                (0.152313, 0.196432, 0.648374, 1.00432))
                       if phase <= 0.4415 else
                       _segment(phase, 0.4415, 1.0, 0.72796, 0.08,
                                (0.257759, -0.003163, 0.211762, 1.38179)))
            bars = ((x + w * (-1.45167 + p_tx), w * p_scale),
                    (x + w * (-0.548889 + s_tx), w * s_scale))
            visible = sorted((max(x, bx), min(x + w, bx + bw))
                             for bx, bw in bars if bx + bw > x and bx < x + w)
            cursor = x
            for left, right in visible:
                segment(cursor, left - 4, track)
                cursor = max(cursor, right + 4)
            segment(cursor, x + w, track)
            r.clip_push(x, y, w, h)
            for bx, bw in bars:
                segment(bx, bx + bw, active)
            r.clip_pop()
        else:
            progress = max(0.0, min(1.0, self._display_value))
            active_end = x + w * progress
            segment(active_end + (4 if progress else 0), x + w, track)
            segment(x, active_end, active)
        stop_size = min(4.0, h, w)
        if self.value is not None and stop_size > 0:
            stop_offset = min((h - stop_size) / 2, 6.0)
            r.circle(x + w - stop_size / 2 - stop_offset, y + h / 2,
                     stop_size / 2, active)

    def _prepare_animations(self, now: float):
        super()._prepare_animations(now)
        if self.value is None:
            if self._last_value is not None:
                self._last_value = None
                self._phase_started = now
        elif self.value != self._last_value:
            self._last_value = self.value
            self._animate_internal("_display_value", float(self.value),
                                   motion.MEDIUM1, motion.PROGRESS, now=now)

    def _tick_animations(self, now: float) -> bool:
        active = super()._tick_animations(now)
        if self.value is None:
            self._phase = ((now - self._phase_started) % 2.0) / 2.0
            return True
        return active


class ProgressRing(Control):
    def __init__(self, value: float | None = None, *, stroke_width: float = 4,
                 color=None, bgcolor=None, **base):
        super().__init__(**base)
        self.value = value
        self.stroke_width = stroke_width
        self.color = color
        self.bgcolor = bgcolor
        self._display_value = 0.0 if value is None else float(value)
        self._last_value = value
        self._phase_started = time.perf_counter()
        self._phase = 0.0

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else 40,
                self._height if self._height is not None else 40)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    @staticmethod
    def _round_arc(r, cx, cy, radius, start, end, color, width):
        if end <= start:
            return
        r.arc(cx, cy, radius, start, end, color, width=width)
        if end - start < 2 * math.pi - 1e-6 and color[3] == 255:
            centerline = radius - width / 2
            for angle in (start, end):
                r.circle(cx + math.cos(angle) * centerline,
                         cy + math.sin(angle) * centerline,
                         width / 2, color)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        cx, cy = x + w / 2, y + h / 2
        diameter = min(w, h)
        if diameter <= 0:
            return
        radius = diameter / 2
        width = min(self.stroke_width, diameter)
        if width <= 0:
            return
        active = colors.parse_color(self.color or colors.Colors.PRIMARY)
        track_color = self.bgcolor or (colors.Colors.SECONDARY_CONTAINER
                                       if self.value is not None else None)
        track = colors.parse_color(track_color) if track_color else None
        if self.value is None:
            elapsed = self._phase
            arc_phase = (elapsed % 1.333) / 1.333
            if arc_phase <= 0.5:
                sweep = 10 + 260 * ease(
                    AnimationCurve.FAST_OUT_SLOWIN, arc_phase * 2)
            else:
                sweep = 270 - 260 * ease(
                    AnimationCurve.FAST_OUT_SLOWIN, (arc_phase - 0.5) * 2)
            linear_rotation = (elapsed / (1.333 * 360 / 306) * 360) % 360
            cycle = (elapsed % (4 * 1.333)) / (4 * 1.333)
            arc_rotation = ease(AnimationCurve.FAST_OUT_SLOWIN, cycle) * 1080
            start = math.radians(-90 + linear_rotation + arc_rotation)
            sweep = math.radians(sweep)
        else:
            start = -math.pi / 2
            sweep = 2 * math.pi * max(0.0, min(1.0, self._display_value))
        if track is not None and track[3] > 0:
            gap = min(sweep, 2 * (4 + width) / diameter)
            self._round_arc(r, cx, cy, radius,
                            start + sweep + gap, start + 2 * math.pi - gap,
                            track, width)
        self._round_arc(r, cx, cy, radius, start, start + sweep, active, width)

    def _prepare_animations(self, now: float):
        super()._prepare_animations(now)
        if self.value is None:
            if self._last_value is not None:
                self._last_value = None
                self._phase_started = now
        elif self.value != self._last_value:
            self._last_value = self.value
            self._animate_internal("_display_value", float(self.value),
                                   motion.LONG2,
                                   AnimationCurve.DECELERATE, now=now)

    def _tick_animations(self, now: float) -> bool:
        active = super()._tick_animations(now)
        if self.value is None:
            self._phase = now - self._phase_started
            return True
        return active
