"""Shared Material Web interaction-state animation helpers."""
from __future__ import annotations

import math
import time

from .. import colors
from .. import motion
from ..types import AnimationCurve
from ..painting import corners, shape_mask
import pygame

HOVER_OPACITY = 0.08
PRESS_OPACITY = 0.12


def init_state_layer(control):
    control._state_hover_alpha = 0.0
    control._state_press_alpha = 0.0
    control._state_ripple_progress = 0.0
    control._state_press_origin = (0.0, 0.0)
    control._state_press_started = 0.0
    control._state_release_deadline = None
    control._state_release_duration = 375


def set_hover(control, on: bool):
    control._hovered = bool(on)
    control._animate_internal(
        "_state_hover_alpha", HOVER_OPACITY if on else 0.0,
        15, AnimationCurve.LINEAR)


def press(control, x: float, y: float, *, ripple_duration=motion.LONG1,
          press_duration=105):
    control._state_press_origin = (x, y)
    control._state_press_started = time.perf_counter()
    control._state_release_deadline = None
    control._animations.pop("_state_ripple_progress", None)
    control._animation_overrides.pop("_state_ripple_progress", None)
    control._state_ripple_progress = 0.0
    control._animation_targets["_state_ripple_progress"] = 0.0
    control._animate_internal(
        "_state_ripple_progress", 1.0, ripple_duration, motion.STANDARD)
    control._animate_internal(
        "_state_press_alpha", PRESS_OPACITY, press_duration,
        AnimationCurve.LINEAR)


def release(control, *, now: float | None = None, minimum_ms=225,
            fade_duration=375):
    now = time.perf_counter() if now is None else now
    control._state_release_duration = fade_duration
    minimum_end = control._state_press_started + minimum_ms / 1000.0
    if now < minimum_end:
        control._state_release_deadline = minimum_end
    else:
        control._animate_internal(
            "_state_press_alpha", 0.0, fade_duration,
            AnimationCurve.LINEAR, now=now)


def tick_state_layer(control, now: float) -> bool:
    deadline = control._state_release_deadline
    if deadline is not None and now >= deadline:
        control._state_release_deadline = None
        control._animate_internal(
            "_state_press_alpha", 0.0,
            control._state_release_duration,
            AnimationCurve.LINEAR, now=now)
    return control._state_release_deadline is not None


def draw_state_layer(control, renderer, rect, color, radius=0.0):
    """Draw hover and a radial ripple clipped to the exact component silhouette."""
    x, y, w, h = rect
    red, green, blue, _ = colors.parse_color(color)
    hover = control._state_hover_alpha
    pressed = control._state_press_alpha
    if (hover <= 0 and pressed <= 0) or w <= 0 or h <= 0:
        return
    scale = renderer.scale
    pw, ph = max(1, round(w * scale)), max(1, round(h * scale))
    mask = shape_mask(pw, ph, corners(radius, scale, pw, ph))
    layer = pygame.Surface((pw, ph), pygame.SRCALPHA)
    layer.fill((red, green, blue, round(255 * max(0, hover))))
    ox, oy = control._state_press_origin
    ox = max(x, min(x + w, ox))
    oy = max(y, min(y + h, oy))
    progress = control._state_ripple_progress
    cx, cy = x + w / 2, y + h / 2
    ripple_x = ox + (cx - ox) * progress
    ripple_y = oy + (cy - oy) * progress
    end_radius = max(
        math.hypot(ripple_x - px, ripple_y - py)
        for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h))
    ) + 10.0
    start_radius = 0.1 * max(w, h)
    ripple_radius = start_radius + (end_radius - start_radius) * progress
    if pressed > 0:
        ripple = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.circle(ripple, (red, green, blue, round(255 * pressed)),
                           (round((ripple_x - x) * scale), round((ripple_y - y) * scale)),
                           max(1, round(ripple_radius * scale)))
        layer.blit(ripple, (0, 0))
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    renderer.blit(layer, x, y)
