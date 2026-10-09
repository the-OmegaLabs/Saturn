"""Renderer interface: all a backend must provide.

Coordinates are logical pixels, origin top-left. Colors are whatever
`types.parse_color` returns (RGBA tuple). `blit` draws a pre-rendered RGBA
pygame surface (text runs, images) — backends that are not pygame simply
upload it as a texture.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import math


_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


class Renderer(ABC):
    gpu_name = None
    gpu_index = None
    gpus = ()
    def activate(self):
        """Select this window's rendering context on the UI thread."""
        pass
    scale: float = 1.0  # supersampling factor (software backend sets 2)
    native_texture_scaling = False
    native_shape_overlay = False
    native_state_layer = False
    native_geometry = False
    native_texture_tint = False
    native_shadow = False
    native_shader = False
    anti_aliasing = True
    vsync = True
    vsync_active = False

    def _init_effect_stacks(self):
        self._opacity_stack = [1.0]
        self._translation_stack = [(0.0, 0.0)]
        self._transform_stack = [_IDENTITY]

    @staticmethod
    def _matrix(matrix):
        if len(matrix) != 6:
            raise ValueError("A transform requires six affine coefficients")
        result = tuple(float(value) for value in matrix)
        if not all(math.isfinite(value) for value in result):
            raise ValueError("Transform coefficients must be finite")
        return result

    def transform_push(self, matrix, *, bounds=None) -> None:
        """Compose an affine matrix: x'=a*x+c*y+tx, y'=b*x+d*y+ty."""
        if matrix == _IDENTITY:
            self._transform_stack.append(self._transform_stack[-1])
            return
        matrix = self._matrix(matrix)
        if self._transform_stack[-1] == _IDENTITY:
            self._transform_stack.append(matrix)
            return
        a, b, c, d, tx, ty = matrix
        pa, pb, pc, pd, px, py = self._transform_stack[-1]
        self._transform_stack.append((
            pa*a+pc*b, pb*a+pd*b, pa*c+pc*d, pb*c+pd*d,
            pa*tx+pc*ty+px, pb*tx+pd*ty+py))

    def transform_pop(self) -> None:
        if len(self._transform_stack) > 1:
            self._transform_stack.pop()

    def _transform_point(self, x, y):
        matrix = self._transform_stack[-1]
        if matrix == _IDENTITY:
            return x, y
        a, b, c, d, tx, ty = matrix
        return a*x+c*y+tx, b*x+d*y+ty

    def _transform_rect(self, x, y, w, h):
        """Conservative scissor bounds; GPU clips remain axis aligned."""
        if self._transform_stack[-1] == _IDENTITY:
            return x, y, w, h
        points = (self._transform_point(x, y), self._transform_point(x+w, y),
                  self._transform_point(x+w, y+h), self._transform_point(x, y+h))
        left = min(point[0] for point in points)
        top = min(point[1] for point in points)
        return left, top, max(point[0] for point in points)-left, max(point[1] for point in points)-top

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

    def blit_tinted_scaled(self, surface, x, y, width, height, color) -> None:
        """Sample immutable pixels multiplied by an RGBA tint on the GPU."""
        raise NotImplementedError

    def polygon(self, points, color, *, center) -> None:
        """Fill a radial polygon whose interior is visible from ``center``."""
        raise NotImplementedError

    def polyline(self, points, color, width=1) -> None:
        """Draw a connected stroke with round endpoint caps on the GPU."""
        raise NotImplementedError

    def wave_line(self, x, y, w, h, a, b, amplitude, wavelength, phase, color, width):
        """Draw an analytic sine-wave stroke, with no intermediate bitmap."""
        raise NotImplementedError

    def wave_arc(self, x, y, w, h, radius, start, sweep, amplitude, waves,
                 phase, color, width):
        """Draw an analytic circular wave, with no intermediate bitmap."""
        raise NotImplementedError

    def shadow(self, x, y, w, h, radii, elevation):
        """Draw ambient and key elevation shadows analytically on the GPU."""
        raise NotImplementedError

    def backdrop_blur(self, x, y, w, h, sigma_x, sigma_y, radius=0):
        """Blur pixels already drawn under this logical rect (Container.blur).

        Software uses a downscaled pygame gaussian; OpenGL runs a separable
        GPU pass. No-op when both sigmas are zero. ``radius`` rounds the
        affected region to match the container corner radius.
        """
        raise NotImplementedError

    def shader(self, x, y, w, h, effect, color, secondary_color,
               parameters, information):
        """Draw a procedural fragment effect without an intermediate bitmap."""
        raise NotImplementedError

    def custom_shader(self, x, y, w, h, body, layout, values, call,
                      elapsed, radius, color, secondary_color):
        """Execute a user fragment directly on the GPU."""
        raise NotImplementedError

    @abstractmethod
    def clip_push(self, x, y, w, h) -> None: ...

    @abstractmethod
    def clip_pop(self) -> None: ...

    @abstractmethod
    def flip(self) -> None: ...

    def on_resize(self, width, height, *, pixel_size=None,
                  pixel_ratio: float | None = None) -> None: ...

    def configure(self, *, anti_aliasing: bool, vsync: bool) -> None:
        """Apply rendering options at a frame boundary on the UI thread."""
        self.anti_aliasing = anti_aliasing
        self.vsync = vsync

    def close(self) -> None:
        """Release backend-owned resources before the native window closes."""

    def screenshot(self):
        """RGBA pygame surface of the current frame at logical window size.

        Call from the UI thread (App.screenshot marshals for you).
        """
        raise NotImplementedError(f"screenshot not supported by {type(self).__name__}")
