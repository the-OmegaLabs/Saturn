"""Shared supersampled shape masks and soft elevation shadows."""
import hashlib
import math
from collections import OrderedDict
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
# Match OpenGL blur FBO ceiling (cpp saturn::kMaxLayoutDim).
_MAX_BLUR_TARGET_DIM = 1 << 15
_MAX_BLUR_CACHE_ENTRIES = 24


def normalize_blur_sigmas(sigma_x, sigma_y, scale):
    """Logical sigmas -> device-pixel radii, clamped for cost.

    Non-finite inputs (NaN/Inf) become 0 so dirty values never reach GL uniforms
    even if a caller bypasses as_blur.
    """
    sx = float(sigma_x)
    sy = float(sigma_y)
    sc = float(scale)
    if not math.isfinite(sx):
        sx = 0.0
    if not math.isfinite(sy):
        sy = 0.0
    if not math.isfinite(sc) or sc <= 0.0:
        sc = 0.0
    sx = max(0.0, sx) * sc
    sy = max(0.0, sy) * sc
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


def plan_backdrop_blur(sigma_x, sigma_y, scale, region_w, region_h):
    """Pure planning for separable backdrop blur (shared by GL + unit tests).

    Returns a dict describing downsample target and which axis passes run.
    Matches ``OpenGLRenderer.backdrop_blur`` pass selection.
    """
    sx, sy = normalize_blur_sigmas(sigma_x, sigma_y, scale)
    rw = max(0, int(region_w))
    rh = max(0, int(region_h))
    if (sx < 0.5 and sy < 0.5) or rw <= 0 or rh <= 0:
        return {
            "skip": True,
            "sigma_x": sx,
            "sigma_y": sy,
            "factor": 1,
            "target": (0, 0),
            "passes": (),
        }
    factor = blur_downsample_factor(sx, sy)
    bw, bh = max(1, rw // factor), max(1, rh // factor)
    if bw > _MAX_BLUR_TARGET_DIM or bh > _MAX_BLUR_TARGET_DIM:
        extra = max(
            math.ceil(bw / _MAX_BLUR_TARGET_DIM),
            math.ceil(bh / _MAX_BLUR_TARGET_DIM),
        )
        factor = max(factor, factor * extra)
        bw, bh = max(1, rw // factor), max(1, rh // factor)
        bw = min(bw, _MAX_BLUR_TARGET_DIM)
        bh = min(bh, _MAX_BLUR_TARGET_DIM)
    passes = []
    if sx >= 0.5:
        passes.append(("x", max(0.5, sx / factor)))
    if sy >= 0.5:
        passes.append(("y", max(0.5, sy / factor)))
    return {
        "skip": False,
        "sigma_x": sx,
        "sigma_y": sy,
        "factor": factor,
        "target": (bw, bh),
        "passes": tuple(passes),
    }


def blur_source_digest(raw: bytes) -> bytes:
    """Stable fingerprint of backdrop pixels for blur-result caching."""
    if not raw:
        return b"\0" * 16
    step = max(1, len(raw) // 1024)
    return hashlib.blake2b(raw[::step], digest_size=16).digest()


class BlurResultCache:
    """LRU of blurred backdrops keyed by region+sigmas+source digest."""

    def __init__(self, max_entries=_MAX_BLUR_CACHE_ENTRIES, on_evict=None):
        self._max = max(1, int(max_entries))
        self._on_evict = on_evict
        self._entries = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key, digest):
        entry = self._entries.get(key)
        if entry is None or entry[0] != digest:
            self.misses += 1
            return None
        self._entries.move_to_end(key)
        self.hits += 1
        return entry[1]

    def put(self, key, digest, payload):
        old = self._entries.pop(key, None)
        if old is not None and self._on_evict is not None and old[1] is not payload:
            self._on_evict(old[1])
        self._entries[key] = (digest, payload)
        while len(self._entries) > self._max:
            _, (_, payload) = self._entries.popitem(last=False)
            if self._on_evict is not None:
                self._on_evict(payload)

    def clear(self):
        if self._on_evict is not None:
            for _, payload in self._entries.values():
                self._on_evict(payload)
        self._entries.clear()
        self.hits = 0
        self.misses = 0

    def __len__(self):
        return len(self._entries)


def _separable_gaussian_surface(work, sx, sy):
    """Apply per-axis Gaussian blur so software matches the GL path.

    pygame only exposes isotropic ``gaussian_blur``. When both axes are active
    we pre-scale so an isotropic radius maps back to (sx, sy). A near-zero
    axis is skipped (same threshold as GL: sigma < 0.5).
    """
    import pygame
    do_x = sx >= 0.5
    do_y = sy >= 0.5
    if not do_x and not do_y:
        return work
    w, h = work.get_size()
    if do_x and do_y:
        ref = min(sx, sy)
        bw = max(1, round(w * ref / sx))
        bh = max(1, round(h * ref / sy))
        scaled = work if (bw, bh) == (w, h) else pygame.transform.smoothscale(work, (bw, bh))
        blurred = pygame.transform.gaussian_blur(scaled, max(1, round(ref)), False)
        if blurred.get_size() != (w, h):
            blurred = pygame.transform.smoothscale(blurred, (w, h))
        return blurred
    # Single-axis: stretch the inactive axis so isotropic blur barely affects it,
    # then restore. Cap stretch to keep cost bounded.
    if do_x:
        ref = sx
        stretch = min(8, max(2, round(ref / 0.25)))
        bh = max(1, min(h * stretch, h * 8))
        scaled = pygame.transform.smoothscale(work, (w, bh))
        blurred = pygame.transform.gaussian_blur(scaled, max(1, round(ref)), False)
        return pygame.transform.smoothscale(blurred, (w, h))
    ref = sy
    stretch = min(8, max(2, round(ref / 0.25)))
    bw = max(1, min(w * stretch, w * 8))
    scaled = pygame.transform.smoothscale(work, (bw, h))
    blurred = pygame.transform.gaussian_blur(scaled, max(1, round(ref)), False)
    return pygame.transform.smoothscale(blurred, (w, h))


def backdrop_blur_surface(surface, sigma_x, sigma_y):
    """Separable Gaussian blur; downscale for large sigmas then upscale.

    Honors distinct ``sigma_x`` / ``sigma_y`` (matching OpenGL) instead of
    collapsing to ``max(sx, sy)``.
    """
    import pygame
    sx = max(0.0, float(sigma_x))
    sy = max(0.0, float(sigma_y))
    if (sx < 0.5 and sy < 0.5) or surface.get_width() <= 0 or surface.get_height() <= 0:
        return surface
    # Factor from active axes only so a near-zero axis is not "helped" into a
    # smoothscale that smears the seam before the separable pass.
    factor = blur_downsample_factor(
        sx if sx >= 0.5 else 0.0,
        sy if sy >= 0.5 else 0.0,
    )
    work = surface
    if factor > 1:
        size = (max(1, surface.get_width() // factor),
                max(1, surface.get_height() // factor))
        work = pygame.transform.smoothscale(surface, size)
        sx = sx / factor
        sy = sy / factor
    blurred = _separable_gaussian_surface(work, sx, sy)
    if factor > 1:
        blurred = pygame.transform.smoothscale(blurred, surface.get_size())
    return blurred

