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

    @abstractmethod
    def clip_push(self, x, y, w, h) -> None: ...

    @abstractmethod
    def clip_pop(self) -> None: ...

    @abstractmethod
    def flip(self) -> None: ...

    def on_resize(self, width, height) -> None: ...

    def screenshot(self):
        """RGBA pygame surface of the current frame at logical window size.

        Call from the UI thread (App.screenshot marshals for you).
        """
        raise NotImplementedError(f"screenshot not supported by {type(self).__name__}")
