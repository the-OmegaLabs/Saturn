"""Built-in effects and user GLSL fragment backgrounds."""
from __future__ import annotations

import math
import time as _time
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

from .. import colors
from ..control import Control


class ShaderEffect(str, Enum):
    GRADIENT = "gradient"
    NOISE = "noise"
    RIPPLE = "ripple"
    PLASMA = "plasma"


_EFFECTS = {effect.value: index for index, effect in enumerate(ShaderEffect)}
_UNIFORMS = {"intensity", "frequency", "center", "angle"}


@dataclass(frozen=True)
class ShaderBuffer:
    """Additive instanced geometry rendered to u_buffer before mainImage.

    Stages define void main(), share the Shader uniforms, and use
    SATURN_LOCATION, SATURN_VERTEX_ID and SATURN_INSTANCE_ID for portability.
    The fragment returns premultiplied color. The final mainImage can call
    saturnSampleBuffer(uv) with top-left UV coordinates.
    """
    vertex_shader: str | Path
    fragment_shader: str | Path
    instances: int = 1

    def __post_init__(self):
        if not isinstance(self.vertex_shader, (str, Path)) or not isinstance(self.fragment_shader, (str, Path)):
            raise TypeError("ShaderBuffer stages must be GLSL strings or pathlib.Path files")
        if isinstance(self.instances, bool) or not isinstance(self.instances, int) or not 1 <= self.instances <= 1_000_000:
            raise ValueError("ShaderBuffer.instances must be an integer from 1 to 1,000,000")


def _number(value, name):
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


class Shader(Control):
    """Draw built-in effects or user GLSL fragments on a GPU backend.

    ``uniforms`` accepts ``intensity`` (0..1), positive ``frequency``, normalized
    ``center`` (x, y), and ``angle`` in radians. ``time`` is an optional offset
    in seconds; ``animate=False`` holds the effect at that time. Software draws
    ``fallback_color`` (or ``color``) once, without emulating shaders on the CPU.
    This paints its own rectangle; it does not filter or blur other controls.
    Custom source defines mainImage; includes and scalar/vector uniforms are
    described in docs/shaders.md. Compilation errors use a static fallback.
    """

    def __init__(self, effect: ShaderEffect | str | None = None, *, shader=None,
                 color="#6750A4", secondary_color="#EADDFF", uniforms=None,
                 animate: bool = True, speed: float = 1.0, time: float = 0.0,
                 border_radius: float = 0.0, fallback_color=None,
                 includes=None, include_dirs=(), on_error=None, buffer=None, **base):
        super().__init__(**base)
        if shader is not None and effect is not None:
            raise ValueError("Pass shader or the legacy effect argument, not both")
        self.shader = shader if shader is not None else effect if effect is not None else ShaderEffect.GRADIENT
        self.color = color
        self.secondary_color = secondary_color
        self.uniforms = {} if uniforms is None else dict(uniforms)
        self.animate = animate
        self.speed = speed
        self.time = time
        self.border_radius = border_radius
        self.fallback_color = fallback_color
        self.includes = dict(includes or {})
        self.include_dirs = tuple(include_dirs)
        self.on_error = on_error
        self.buffer = buffer
        self._buffer_token = object()
        self._buffer_key = None
        self._buffer_sources = None
        self._error = None
        self._source_key = None
        self._source = None
        self._prepared_key = None
        self._prepared = None
        self._started = _time.perf_counter()
        self._elapsed = 0.0
        if self._builtin:
            self._parameters()
        else:
            self._custom_parameters()

    @property
    def effect(self):
        """Compatibility alias for shader."""
        return self.shader.value if isinstance(self.shader, ShaderEffect) else self.shader

    @effect.setter
    def effect(self, value):
        self.shader = value

    @property
    def error(self):
        return self._error

    def reload(self):
        """Read the source file and includes again on the next frame."""
        self._source_key = None
        self._buffer_key = None
        self.update()

    def _buffer_parameters(self):
        if self.buffer is None:
            return None
        if not isinstance(self.buffer, ShaderBuffer):
            raise TypeError("buffer must be a ShaderBuffer or None")
        from ..renderer.shader_source import resolve_source
        key = (self.buffer, tuple(sorted(self.includes.items())), self.include_dirs)
        if key != self._buffer_key:
            self._buffer_sources = tuple(resolve_source(source, self.includes, self.include_dirs)
                for source in (self.buffer.vertex_shader, self.buffer.fragment_shader))
            self._buffer_key = key
        return (self._buffer_token, *self._buffer_sources, self.buffer.instances)

    @property
    def _builtin(self):
        return isinstance(self.shader, ShaderEffect) or isinstance(self.shader, str) and self.shader in _EFFECTS

    def _custom_parameters(self):
        from ..renderer.shader_source import resolve_source, prepare_source
        key = (self.shader, tuple(sorted(self.includes.items())), self.include_dirs)
        if key != self._source_key:
            self._source = resolve_source(self.shader, self.includes, self.include_dirs)
            self._source_key = key
            self._prepared_key = None
        if 'saturnSampleBuffer' in self._source and self.buffer is None:
            raise ValueError("saturnSampleBuffer requires a ShaderBuffer")
        radius = _number(self.border_radius, "border_radius")
        if radius < 0:
            raise ValueError("border_radius must be nonnegative")
        if not isinstance(self.animate, bool):
            raise TypeError("animate must be a bool")
        # GLSL parsing dominates the frame budget if redone per frame; the
        # prepared program inputs only change when source or uniforms do.
        prepared_key = (self._source_key, tuple(sorted(self.uniforms.items())))
        if prepared_key != self._prepared_key:
            self._prepared = prepare_source(self._source, self.uniforms)
            self._prepared_key = prepared_key
        elapsed = _number(self.time, "time") + self._elapsed * _number(self.speed, "speed")
        return (*self._prepared, elapsed, radius)

    def _parameters(self):
        effect = self.effect.value if isinstance(self.effect, ShaderEffect) else self.effect
        if effect not in _EFFECTS:
            raise ValueError(f"Unknown shader effect {effect!r}; choose {', '.join(_EFFECTS)}")
        unknown = set(self.uniforms) - _UNIFORMS
        if unknown:
            raise ValueError(f"Unknown shader uniforms: {', '.join(sorted(unknown))}")
        intensity = _number(self.uniforms.get("intensity", 1.0), "intensity")
        frequency = _number(self.uniforms.get("frequency", 4.0), "frequency")
        angle = _number(self.uniforms.get("angle", 0.0), "angle")
        radius = _number(self.border_radius, "border_radius")
        if not 0 <= intensity <= 1:
            raise ValueError("intensity must be between 0 and 1")
        if frequency <= 0 or radius < 0:
            raise ValueError("frequency must be positive and border_radius nonnegative")
        center = self.uniforms.get("center", (0.5, 0.5))
        if not isinstance(center, (tuple, list)) or len(center) != 2:
            raise ValueError("center must contain two normalized coordinates")
        cx, cy = (_number(value, "center") for value in center)
        if not (0 <= cx <= 1 and 0 <= cy <= 1):
            raise ValueError("center coordinates must be between 0 and 1")
        speed = _number(self.speed, "speed")
        elapsed = _number(self.time, "time") + self._elapsed * speed
        if not isinstance(self.animate, bool):
            raise TypeError("animate must be a bool")
        return _EFFECTS[effect], (elapsed, intensity, frequency, radius), (cx, cy, angle, 0)

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else min(240, max_w),
                self._height if self._height is not None else min(160, max_h))

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, renderer, x, y):
        w, h = self._rect[2:]
        if not getattr(renderer, "native_shader", False):
            renderer.fill_rect(x, y, w, h, self.fallback_color or self.color,
                               radius=self.border_radius)
            return
        if self._builtin:
            effect, parameters, information = self._parameters()
            renderer.shader(x, y, w, h, effect, colors.parse_color(self.color),
                            colors.parse_color(self.secondary_color), parameters, information)
            self._error = None
        else:
            from ..renderer.shader_source import ShaderCompilationError
            try:
                renderer.custom_shader(x, y, w, h, *self._custom_parameters(),
                                       colors.parse_color(self.color), colors.parse_color(self.secondary_color),
                                       buffer_pass=self._buffer_parameters())
                self._error = None
            except (ShaderCompilationError, ValueError, TypeError, FileNotFoundError) as error:
                message = str(error)
                if message != self._error:
                    self._error = message
                    if self.page is not None:
                        from ..event import ControlEvent
                        self.page._dispatch(self.on_error, ControlEvent("shader_error", self, data=message))
                renderer.fill_rect(x, y, w, h, self.fallback_color or self.color, radius=self.border_radius)

    def _tick_animations(self, now):
        active = super()._tick_animations(now)
        control = self
        while control is not None:
            if not control.visible:
                return active
            control = control.parent
        native = (self.page is None or
                  getattr(self.page._app.renderer, "native_shader", False))
        if self.animate and self.speed != 0 and native:
            self._elapsed = max(0.0, now - self._started)
            return True
        return active
