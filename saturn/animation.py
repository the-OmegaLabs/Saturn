"""Implicit-animation primitives matching Flet 1.0 / Flutter timing."""
from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import fields, is_dataclass

from .types import Animation, AnimationCurve, Duration


def animation_spec(value) -> tuple[float, AnimationCurve] | None:
    """Resolve Flet's AnimationValue shorthand to seconds + curve."""
    if value is None or value is False:
        return None
    if value is True:
        return 1.0, AnimationCurve.LINEAR
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, float(value) / 1000.0), AnimationCurve.LINEAR
    if isinstance(value, Animation):
        duration = value.duration
        if isinstance(duration, Duration):
            seconds = duration.in_microseconds / 1_000_000.0
        elif hasattr(duration, "in_microseconds"):
            seconds = duration.in_microseconds / 1_000_000.0
        elif hasattr(duration, "total_seconds"):
            seconds = duration.total_seconds()
        else:
            seconds = float(duration) / 1000.0
        curve = value.curve
        if not isinstance(curve, AnimationCurve):
            curve = AnimationCurve(getattr(curve, "value", curve))
        return max(0.0, seconds), curve
    raise TypeError("animation must be bool, milliseconds, Animation, or None")


def _cubic_bezier(t: float, x1: float, y1: float,
                  x2: float, y2: float) -> float:
    def axis(u, a, b):
        v = 1.0 - u
        return 3 * v * v * u * a + 3 * v * u * u * b + u * u * u

    def deriv(u, a, b):
        return (3 * (1 - u) * (1 - u) * a
                + 6 * (1 - u) * u * (b - a)
                + 3 * u * u * (1 - b))

    u = t
    for _ in range(8):
        dx = deriv(u, x1, x2)
        if abs(dx) < 1e-7:
            break
        candidate = u - (axis(u, x1, x2) - t) / dx
        if not 0 <= candidate <= 1:
            break
        u = candidate
    else:
        return axis(u, y1, y2)
    lo, hi = 0.0, 1.0
    for _ in range(20):
        u = (lo + hi) / 2
        if axis(u, x1, x2) < t:
            lo = u
        else:
            hi = u
    return axis((lo + hi) / 2, y1, y2)


def _bounce_out(t: float) -> float:
    if t < 1 / 2.75:
        return 7.5625 * t * t
    if t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    if t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    t -= 2.625 / 2.75
    return 7.5625 * t * t + 0.984375


def ease(curve: AnimationCurve, t: float) -> float:
    """Evaluate Flutter-compatible easing. Overshooting curves stay un-clamped."""
    t = max(0.0, min(1.0, float(t)))
    if t in (0.0, 1.0):
        return t
    name = curve.value if isinstance(curve, AnimationCurve) else str(curve)
    cubics = {
        "ease": (.25, .1, .25, 1),
        "easeIn": (.42, 0, 1, 1),
        "easeOut": (0, 0, .58, 1),
        "easeInOut": (.42, 0, .58, 1),
        "decelerate": (0, 0, .2, 1),
        "fastOutSlowIn": (.4, 0, .2, 1),
        "linearToEaseOut": (.35, .91, .33, .97),
        "fastLinearToSlowEaseIn": (.18, 1, .04, 1),
        "easeInToLinear": (.67, .03, .65, .09),
        "slowMiddle": (.15, .85, .85, .15),
        "easeInOutCubicEmphasized": (.2, 0, 0, 1),
        "materialStandard": (.2, 0, 0, 1),
        "materialStandardAccelerate": (.3, 0, 1, 1),
        "materialStandardDecelerate": (0, 0, 0, 1),
        "materialEmphasized": (.3, 0, 0, 1),
        "materialEmphasizedAccelerate": (.3, 0, .8, .15),
        "materialEmphasizedDecelerate": (.05, .7, .1, 1),
        "materialSwitchOvershoot": (.175, .885, .32, 1.275),
        "materialProgress": (.4, 0, .6, 1),
    }
    if name in cubics:
        return _cubic_bezier(t, *cubics[name])
    if name == "linear":
        return t
    if name == "easeInQuad":
        return t * t
    if name == "easeOutQuad":
        return 1 - (1 - t) ** 2
    if name == "easeInOutQuad":
        return 2 * t * t if t < .5 else 1 - (-2 * t + 2) ** 2 / 2
    if name == "easeInCubic":
        return t ** 3
    if name == "easeOutCubic":
        return 1 - (1 - t) ** 3
    if name == "easeInOutCubic":
        return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
    if name == "easeInQuart":
        return t ** 4
    if name == "easeOutQuart":
        return 1 - (1 - t) ** 4
    if name == "easeInOutQuart":
        return 8 * t ** 4 if t < .5 else 1 - (-2 * t + 2) ** 4 / 2
    if name == "easeInQuint":
        return t ** 5
    if name == "easeOutQuint":
        return 1 - (1 - t) ** 5
    if name == "easeInOutQuint":
        return 16 * t ** 5 if t < .5 else 1 - (-2 * t + 2) ** 5 / 2
    if name == "easeInSine":
        return 1 - math.cos(t * math.pi / 2)
    if name == "easeOutSine":
        return math.sin(t * math.pi / 2)
    if name == "easeInOutSine":
        return -(math.cos(math.pi * t) - 1) / 2
    if name == "easeInExpo":
        return 2 ** (10 * t - 10)
    if name == "easeOutExpo":
        return 1 - 2 ** (-10 * t)
    if name == "easeInOutExpo":
        return 2 ** (20 * t - 10) / 2 if t < .5 else (2 - 2 ** (-20 * t + 10)) / 2
    if name == "easeInCirc":
        return 1 - math.sqrt(1 - t * t)
    if name == "easeOutCirc":
        return math.sqrt(1 - (t - 1) ** 2)
    if name == "easeInOutCirc":
        return ((1 - math.sqrt(1 - (2 * t) ** 2)) / 2 if t < .5
                else (math.sqrt(1 - (-2 * t + 2) ** 2) + 1) / 2)
    if name == "easeInBack":
        c = 1.70158
        return (c + 1) * t ** 3 - c * t * t
    if name == "easeOutBack":
        c = 1.70158
        return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
    if name == "easeInOutBack":
        c = 1.70158 * 1.525
        return ((2 * t) ** 2 * ((c + 1) * 2 * t - c) / 2 if t < .5
                else ((2 * t - 2) ** 2 * ((c + 1) * (2 * t - 2) + c) + 2) / 2)
    if name == "bounceOut":
        return _bounce_out(t)
    if name == "bounceIn":
        return 1 - _bounce_out(1 - t)
    if name == "bounceInOut":
        return ((1 - _bounce_out(1 - 2 * t)) / 2 if t < .5
                else (1 + _bounce_out(2 * t - 1)) / 2)
    c = 2 * math.pi / 3
    if name == "elasticIn":
        return -(2 ** (10 * t - 10)) * math.sin((t * 10 - 10.75) * c)
    if name == "elasticOut":
        return 2 ** (-10 * t) * math.sin((t * 10 - .75) * c) + 1
    if name == "elasticInOut":
        c2 = 2 * math.pi / 4.5
        return (-(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c2)) / 2
                if t < .5 else
                (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c2)) / 2 + 1)
    return t


def interpolate(start, end, t: float, name: str = ""):
    if t <= 0:
        return deepcopy(start)
    if t >= 1:
        return deepcopy(end)
    if isinstance(start, bool) or isinstance(end, bool):
        return start
    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
        return start + (end - start) * t
    if isinstance(start, str) and isinstance(end, str) and "color" in name:
        from .colors import parse_color
        a, b = parse_color(start), parse_color(end)
        return tuple(round(x + (y - x) * t) for x, y in zip(a, b))
    if (isinstance(start, tuple) and isinstance(end, tuple)
            and len(start) == len(end)):
        return tuple(interpolate(a, b, t, name) for a, b in zip(start, end))
    if is_dataclass(start) and type(start) is type(end):
        values = {}
        for f in fields(start):
            values[f.name] = interpolate(getattr(start, f.name), getattr(end, f.name),
                                         t, f.name)
        return type(start)(**values)
    return deepcopy(start)
