"""Shared supersampled shape masks and soft elevation shadows."""
import math
from functools import lru_cache

import pygame


def corners(radius, scale, w, h):
    values = radius if isinstance(radius, (tuple, list)) else (radius,) * 4
    return tuple(max(0, min(round(v * scale), w // 2, h // 2)) for v in values)


@lru_cache(maxsize=128)
def shape_mask(w, h, radii):
    """White RGBA mask; corner order is top-left, top-right, bottom-right, bottom-left."""
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surface, (255, 255, 255, 255), surface.get_rect(),
                     border_top_left_radius=radii[0], border_top_right_radius=radii[1],
                     border_bottom_right_radius=radii[2], border_bottom_left_radius=radii[3])
    return surface


@lru_cache(maxsize=96)
def _shadow(w, h, radii, elevation, scale):
    ambient_blur = max(1, round((1 + elevation * .7) * scale))
    key_blur = max(1, round((.5 + elevation * .8) * scale))
    offset = round(elevation * .5 * scale)
    pad = math.ceil(3 * max(ambient_blur, key_blur) + offset)
    size = (w + 2 * pad, h + 2 * pad)
    result = pygame.Surface(size, pygame.SRCALPHA)
    mask = shape_mask(w, h, radii)
    for blur, dy, alpha in ((ambient_blur, 0, 28), (key_blur, offset, 40)):
        silhouette = pygame.Surface((w, h), pygame.SRCALPHA)
        silhouette.fill((0, 0, 0, alpha))
        silhouette.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        layer = pygame.Surface(size, pygame.SRCALPHA)
        layer.blit(silhouette, (pad, pad + dy))
        result.blit(pygame.transform.gaussian_blur(layer, blur, False), (0, 0))
    return result, pad


@lru_cache(maxsize=96)
def _scaled_shadow(w, h, radii, elevation, scale, output_scale):
    surface, pad = _shadow(w, h, radii, elevation, scale)
    size = tuple(max(1, round(v * output_scale / scale)) for v in surface.get_size())
    return pygame.transform.smoothscale(surface, size), pad


def draw_shadow(renderer, rect, radius, elevation):
    if elevation <= 0:
        return
    x, y, width, height = rect
    # Soft shadows contain no sharp detail outside the covered silhouette.
    # Blur a reduced intermediate and upscale at presentation; animation must
    # not run two full-resolution Gaussian filters for every new width/radius.
    scale = min(renderer.scale, .5 if elevation >= 4 else 1.0)
    w, h = round(width * scale), round(height * scale)
    if w <= 0 or h <= 0:
        return
    args = (w, h, corners(radius, scale, w, h), round(elevation * 4) / 4, scale)
    if renderer.native_texture_scaling:
        surface, pad = _shadow(*args)
        renderer.blit_scaled(surface, x - pad / scale, y - pad / scale,
                             surface.get_width() / scale, surface.get_height() / scale)
    else:
        # Software presentation needs device-sized pixels. Reuse the upscale
        # too, especially for menu items whose opacity changes every frame.
        surface, pad = _scaled_shadow(*args, renderer.scale)
        renderer.blit(surface, x - pad / scale, y - pad / scale)


def draw_notched_outline(renderer, rect, color, width, radius, left, gap, *, depth=None):
    """Omit the top label gap without painting over the parent background."""
    x, y, w, h = rect
    start = max(0.0, min(w, left))
    end = max(start, min(w, start + gap))
    depth = max(2.0, width + 1.0) if depth is None else max(0.0, min(h, depth))
    for cx, cy, cw, ch in ((x, y, start, h), (x + end, y, w - end, h),
                           (x + start, y + depth, end - start, h - depth)):
        if cw <= 0 or ch <= 0:
            continue
        renderer.clip_push(cx, cy, cw, ch)
        try:
            renderer.stroke_rect(x, y, w, h, color, width=width, radius=radius)
        finally:
            renderer.clip_pop()
