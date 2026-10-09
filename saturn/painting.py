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
    if getattr(renderer, 'native_shadow', False):
        if width > 0 and height > 0:
            radii = radius if isinstance(radius, (tuple, list)) else (radius,) * 4
            renderer.shadow(x, y, width, height, radii, elevation)
        return
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
        renderer.blit_cached_scaled(surface, x - pad / scale, y - pad / scale,
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


# Cap device-pixel sigma so a large Container.blur cannot stall the UI thread.
_MAX_DEVICE_SIGMA = 48.0


def normalize_blur_sigmas(sigma_x, sigma_y, scale):
    """Logical sigmas -> device-pixel radii, clamped for cost."""
    sx = max(0.0, float(sigma_x)) * scale
    sy = max(0.0, float(sigma_y)) * scale
    peak = max(sx, sy)
    if peak > _MAX_DEVICE_SIGMA:
        factor = _MAX_DEVICE_SIGMA / peak
        sx *= factor
        sy *= factor
    return sx, sy


def blur_downsample_factor(sigma_x, sigma_y):
    """Keep the intermediate blur near a cheap radius (matches elevation shadows)."""
    peak = max(sigma_x, sigma_y)
    if peak <= 4:
        return 1
    if peak <= 12:
        return 2
    if peak <= 24:
        return 3
    return 4


def backdrop_blur_surface(surface, sigma_x, sigma_y):
    """Gaussian-blur an RGBA surface; downscale for large sigmas then upscale.

    pygame.transform.gaussian_blur is isotropic. When sigmas differ, the larger
    radius is used so a Flet-style (0, 10) still softens the backdrop.
    """
    import pygame
    sx = max(0.0, float(sigma_x))
    sy = max(0.0, float(sigma_y))
    radius = max(sx, sy)
    if radius < 0.5 or surface.get_width() <= 0 or surface.get_height() <= 0:
        return surface
    factor = blur_downsample_factor(sx, sy)
    work = surface
    if factor > 1:
        size = (max(1, surface.get_width() // factor),
                max(1, surface.get_height() // factor))
        work = pygame.transform.smoothscale(surface, size)
        radius = max(0.5, radius / factor)
    blurred = pygame.transform.gaussian_blur(work, max(1, round(radius)), False)
    if factor > 1:
        blurred = pygame.transform.smoothscale(blurred, surface.get_size())
    return blurred

