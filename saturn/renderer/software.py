"""Software renderer: pygame.draw on an internal 2x surface.

The whole frame is drawn at 2x and downscaled on flip, so rounded rects and
text edges get antialiasing pygame.draw can't do alone.
"""
from __future__ import annotations

import os

import pygame

from ..colors import parse_color
from .base import Renderer

SCALE = 2


def _rgb(color) -> tuple:
    return parse_color(color)


class SoftwareRenderer(Renderer):
    scale = SCALE

    def __init__(self):
        self.screen = pygame.display.get_surface()
        w, h = self.screen.get_size()
        self._buf = pygame.Surface((w * SCALE, h * SCALE), pygame.SRCALPHA)
        self._clip: list[tuple] = []
        self._apply_clip()

    def on_resize(self, width, height):
        self.screen = pygame.display.get_surface()
        self._buf = pygame.Surface((width * SCALE, height * SCALE), pygame.SRCALPHA)
        self._apply_clip()

    def _s(self, *vals):
        return [v * SCALE for v in vals]

    def _apply_clip(self):
        rect = None
        for x, y, w, h in self._clip:
            r = pygame.Rect(*self._s(x, y, w, h))
            rect = r if rect is None else rect.clip(r)
        self._buf.set_clip(rect)  # None = full surface

    def clear(self, color):
        self._buf.fill(_rgb(color))

    def fill_rect(self, x, y, w, h, color, radius=0):
        if w <= 0 or h <= 0:
            return
        c = _rgb(color)
        if len(c) > 3 and c[3] < 255:
            # pygame.draw REPLACES pixels (alpha included) on a SRCALPHA buf,
            # so translucent fills accumulate frame over frame — composite
            # through a temp surface instead
            tmp = pygame.Surface((max(1, int(w * SCALE)), max(1, int(h * SCALE))),
                                 pygame.SRCALPHA)
            pygame.draw.rect(tmp, c, tmp.get_rect(),
                             border_radius=int(radius * SCALE))
            self._buf.blit(tmp, self._s(x, y))
            return
        pygame.draw.rect(self._buf, c,
                         (*self._s(x, y)[:2], int(w * SCALE), int(h * SCALE)),
                         border_radius=int(radius * SCALE))

    def overlay_rect(self, x, y, w, h, color, radius=0):
        self.fill_rect(x, y, w, h, color, radius)  # fill_rect blends now

    def stroke_rect(self, x, y, w, h, color, width=1, radius=0):
        c = _rgb(color)
        sw, sh = max(1, int(w * SCALE)), max(1, int(h * SCALE))
        line_w = max(1, int(width * SCALE))
        if len(c) > 3 and c[3] < 255:
            # Like fill_rect, pygame.draw replaces destination alpha on an
            # SRCALPHA surface. Draw translucent strokes into a temporary
            # layer so they blend over the already-opaque frame like GL.
            tmp = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(tmp, c, tmp.get_rect(), width=line_w,
                             border_radius=int(radius * SCALE))
            self._buf.blit(tmp, self._s(x, y))
            return
        pygame.draw.rect(self._buf, c,
                         (*self._s(x, y)[:2], sw, sh), width=line_w,
                         border_radius=int(radius * SCALE))

    def line(self, x1, y1, x2, y2, color, width=1):
        pygame.draw.line(self._buf, _rgb(color), *self._s(x1, y1, x2, y2),
                         width=max(1, int(width * SCALE)))

    def circle(self, x, y, radius, color, fill=True):
        pygame.draw.circle(self._buf, _rgb(color), self._s(x, y),
                           int(radius * SCALE), 0 if fill else max(1, SCALE))

    def arc(self, x, y, radius, start_angle, end_angle, color, width=1):
        rect = pygame.Rect(0, 0, int(radius * 2 * SCALE), int(radius * 2 * SCALE))
        rect.center = self._s(x, y)
        pygame.draw.arc(self._buf, _rgb(color), rect,
                        start_angle, end_angle, max(1, int(width * SCALE)))

    def blit(self, surface, x, y, alpha=1.0):
        """surface is already in device px (text/images render at scale)."""
        s = surface
        if not s.get_flags() & pygame.SRCALPHA:
            s = s.convert_alpha()
        if alpha < 1.0:
            s = s.copy()
            s.set_alpha(int(alpha * 255))
        self._buf.blit(s, self._s(x, y))

    def clip_push(self, x, y, w, h):
        self._clip.append((x, y, w, h))
        self._apply_clip()

    def clip_pop(self):
        self._clip.pop()
        self._apply_clip()

    def flip(self):
        out = pygame.transform.smoothscale(self._buf, self.screen.get_size())
        self.screen.blit(out, (0, 0))
        pygame.display.flip()
        if os.environ.get("SATURN_SHOT"):  # test hook: dump last frame to png
            pygame.image.save(self.screenshot(), os.environ["SATURN_SHOT"])

    def screenshot(self):
        """The composited frame (2x buffer downscaled to window size)."""
        return pygame.transform.smoothscale(self._buf, self.screen.get_size())
