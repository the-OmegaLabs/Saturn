"""Renderer interface: all a backend must provide.

Coordinates are logical pixels, origin top-left. Colors are whatever
`types.parse_color` returns (RGBA tuple). `blit` draws a pre-rendered RGBA
pygame surface (text runs, images) — backends that are not pygame simply
upload it as a texture.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Renderer(ABC):
    scale: float = 1.0  # supersampling factor (software backend sets 2)
    native_texture_scaling = False
    native_shape_overlay = False
    native_state_layer = False

    def _init_effect_stacks(self):
        self._opacity_stack = [1.0]
        self._translation_stack = [(0.0, 0.0)]

    def opacity_push(self, opacity: float) -> None:
        self._opacity_stack.append(self._opacity_stack[-1] * opacity)

    def opacity_pop(self) -> None:
        if len(self._opacity_stack) > 1:
            self._opacity_stack.pop()

    @property
    def opacity(self) -> float:
        return self._opacity_stack[-1]

    def translate_push(self, x: float, y: float) -> None:
        px, py = self._translation_stack[-1]
        self._translation_stack.append((px + x, py + y))

    def translate_pop(self) -> None:
        if len(self._translation_stack) > 1:
            self._translation_stack.pop()

    def _translate(self, x: float, y: float) -> tuple[float, float]:
        tx, ty = self._translation_stack[-1]
        return x + tx, y + ty

    def _effect_color(self, color):
        from ..colors import parse_color
        r, g, b, a = parse_color(color)
        return r, g, b, round(a * self.opacity)

    @abstractmethod
    def clear(self, color) -> None: ...

    @abstractmethod
    def fill_rect(self, x, y, w, h, color, radius=0) -> None: ...

    def overlay_rect(self, x, y, w, h, color, radius=0) -> None:
        """Alpha-composited rect (barriers/shadows); default = fill_rect."""
        self.fill_rect(x, y, w, h, color, radius)

    @abstractmethod
    def stroke_rect(self, x, y, w, h, color, width=1, radius=0) -> None: ...

    @abstractmethod
    def line(self, x1, y1, x2, y2, color, width=1) -> None: ...

    @abstractmethod
    def circle(self, x, y, radius, color, fill=True) -> None: ...

    @abstractmethod
    def arc(self, x, y, radius, start_angle, end_angle, color, width=1) -> None: ...

    @abstractmethod
    def blit(self, surface, x, y, alpha=1.0) -> None: ...

    def blit_cached(self, surface, x, y, alpha=1.0) -> None:
        """Blit a source surface that callers keep unchanged."""
        self.blit(surface, x, y, alpha)

    @abstractmethod
    def blit_scaled(self, surface, x, y, width, height,
                    alpha=1.0) -> None: ...

    def blit_cached_scaled(self, surface, x, y, width, height,
                           alpha=1.0) -> None:
        self.blit_scaled(surface, x, y, width, height, alpha)

    @abstractmethod
    def clip_push(self, x, y, w, h) -> None: ...

    @abstractmethod
    def clip_pop(self) -> None: ...

    @abstractmethod
    def flip(self) -> None: ...

    def on_resize(self, width, height, *, pixel_size=None,
                  pixel_ratio: float | None = None) -> None: ...

    def close(self) -> None:
        """Release backend-owned resources before the native window closes."""

    def screenshot(self):
        """RGBA pygame surface of the current frame at logical window size.

        Call from the UI thread (App.screenshot marshals for you).
        """
        raise NotImplementedError(f"screenshot not supported by {type(self).__name__}")
