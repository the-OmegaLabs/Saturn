"""Software renderer: pygame.draw on an internal 2x surface.

The whole frame is drawn at 2x and downscaled on flip, so rounded rects and
text edges get antialiasing pygame.draw can't do alone.
"""
from __future__ import annotations

import os
import math

import pygame

from ..colors import parse_color
from .base import Renderer

SCALE = 2


def _rgb(color) -> tuple:
    return parse_color(color)


def _as_alpha_surface(surface: pygame.Surface) -> pygame.Surface:
    """Convert to RGBA without depending on pygame.display's pixel format."""
    if surface.get_flags() & pygame.SRCALPHA:
        return surface
    converted = pygame.Surface(surface.get_size(), pygame.SRCALPHA, 32)
    converted.blit(surface, (0, 0))
    return converted


class SoftwareRenderer(Renderer):
    name = "software"

    def __init__(self, window=None, *, logical_size=None,
                 pixel_ratio: float = 1.0, anti_aliasing: bool = True,
                 vsync: bool = True):
        self._init_effect_stacks()
        self.window = window
        self.pixel_ratio = max(1.0, float(pixel_ratio))
        self.anti_aliasing = anti_aliasing
        self.vsync = vsync
        self._aa_scale = 1 if not anti_aliasing or self.pixel_ratio >= 1.5 else SCALE
        self.scale = self._aa_scale * self.pixel_ratio
        self.screen = (window.get_surface() if window is not None
                       else pygame.display.get_surface())
        w, h = self.screen.get_size()
        self._buf = pygame.Surface(
            (w * self._aa_scale, h * self._aa_scale), pygame.SRCALPHA)
        self._clip: list[tuple] = []
        self._transform_layers = []
        self._transform_translation = (0.0, 0.0)
        self._buf_origin = (0.0, 0.0)
        self._layer_empty = False
        from ..painting import BlurResultCache
        self._blur_cache = BlurResultCache()
        self._apply_clip()

    def on_resize(self, width, height, *, pixel_size=None,
                  pixel_ratio: float | None = None):
        if pixel_ratio is not None:
            self.pixel_ratio = max(1.0, float(pixel_ratio))
        self._aa_scale = (1 if not self.anti_aliasing or self.pixel_ratio >= 1.5
                          else SCALE)
        self.scale = self._aa_scale * self.pixel_ratio
        self.screen = (self.window.get_surface() if self.window is not None
                       else pygame.display.get_surface())
        pixel_width, pixel_height = (
            tuple(pixel_size) if pixel_size is not None
            else self.screen.get_size())
        self._buf = pygame.Surface(
            (max(1, int(pixel_width)) * self._aa_scale,
             max(1, int(pixel_height)) * self._aa_scale), pygame.SRCALPHA)
        if hasattr(self, "_blur_cache"):
            self._blur_cache.clear()
        self._apply_clip()

    def configure(self, *, anti_aliasing: bool, vsync: bool):
        changed = anti_aliasing != self.anti_aliasing
        super().configure(anti_aliasing=anti_aliasing, vsync=vsync)
        if changed:
            self.on_resize(*self.screen.get_size())

    def _s(self, *vals):
        origin = self._buf_origin
        return [(value-origin[index % 2])*self.scale for index, value in enumerate(vals)]

    def transform_push(self, matrix, *, bounds=None):
        if matrix == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0):
            super().transform_push(matrix)
            self._transform_layers.append(None)
            return
        matrix = self._matrix(matrix)
        a, b, c, d, tx, ty = matrix
        if (a, b, c, d) == (1.0, 0.0, 0.0, 1.0):
            previous = self._transform_translation
            super().transform_push(matrix)
            self._transform_translation = (previous[0]+tx, previous[1]+ty)
            self.translate_push(tx, ty)
            self._transform_layers.append(("translation", previous))
            return
        sx, column_y = math.hypot(a, b), math.hypot(c, d)
        if abs(a*c+b*d) > max(1e-10, sx*column_y*1e-8):
            raise NotImplementedError("Software transforms support rotation and per-axis scale, not shear")
        px, py = self._transform_translation
        # Ancestor translations are already applied to paint coordinates.
        # Conjugate this layer matrix so rotation remains inside that parent.
        adjusted = (a, b, c, d, tx+px-a*px-c*py, ty+py-b*px-d*py)
        determinant = a*d-b*c
        empty = abs(determinant) < 1e-12 or self._layer_empty
        left = top = right = bottom = 0.0
        if not empty:
            clip = self._buf.get_clip()
            x0 = self._buf_origin[0]+clip.left/self.scale
            y0 = self._buf_origin[1]+clip.top/self.scale
            x1 = self._buf_origin[0]+clip.right/self.scale
            y1 = self._buf_origin[1]+clip.bottom/self.scale
            mx, my = adjusted[4:]
            points = [((d*(x-mx)-c*(y-my))/determinant,
                       (a*(y-my)-b*(x-mx))/determinant)
                      for x, y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
            left, top = min(point[0] for point in points), min(point[1] for point in points)
            right, bottom = max(point[0] for point in points), max(point[1] for point in points)
            if bounds is not None:
                if len(bounds) != 4 or not all(math.isfinite(float(value)) for value in bounds):
                    raise ValueError("Transform bounds must contain four finite coordinates")
                bx, by, bw, bh = (float(value) for value in bounds)
                bx, by = self._translate(bx, by)
                left, top = max(left,bx), max(top,by)
                right, bottom = min(right,bx+max(0,bw)), min(bottom,by+max(0,bh))
            empty = right <= left or bottom <= top
        origin = (math.floor(left*self.scale-1)/self.scale,
                  math.floor(top*self.scale-1)/self.scale)
        size = ((1,1) if empty else
                (max(1,math.ceil((right-origin[0])*self.scale)+1),
                 max(1,math.ceil((bottom-origin[1])*self.scale)+1)))
        if max(size) > 16384 or size[0]*size[1] > 16777216:
            raise ValueError("Software transform layer exceeds 16 million pixels; provide tighter paint bounds")
        layer = pygame.Surface(size, pygame.SRCALPHA, 32)
        super().transform_push(matrix)
        self._transform_layers.append(("layer", self._buf, self._clip, adjusted,
                                       self._buf_origin, self._layer_empty))
        self._buf, self._clip = layer, []
        self._buf_origin, self._layer_empty = origin, empty
        self._apply_clip()

    def transform_pop(self):
        if not self._transform_layers:
            return
        layer = self._transform_layers.pop()
        super().transform_pop()
        if layer is None:
            return
        if layer[0] == "translation":
            self.translate_pop()
            self._transform_translation = layer[1]
            return
        source = self._buf
        source_origin = self._buf_origin
        _, self._buf, self._clip, matrix, self._buf_origin, self._layer_empty = layer
        self._apply_clip()
        bounds = source.get_bounding_rect(min_alpha=1)
        if not bounds.width or not bounds.height:
            return
        a, b, c, d, tx, ty = matrix
        sx = math.hypot(a, b)
        if sx <= 1e-12:
            return
        sy = (a*d-b*c) / sx
        if abs(sy) <= 1e-12:
            return
        scaled = pygame.transform.smoothscale(
            source.subsurface(bounds),
            (max(1, round(bounds.width*sx)), max(1, round(bounds.height*abs(sy)))))
        if sy < 0:
            scaled = pygame.transform.flip(scaled, False, True)
        angle = math.degrees(math.atan2(b, a))
        transformed = pygame.transform.rotate(scaled, -angle) if angle else scaled
        cx = source_origin[0]+(bounds.x+bounds.width/2)/self.scale
        cy = source_origin[1]+(bounds.y+bounds.height/2)/self.scale
        center = ((a*cx+c*cy+tx-self._buf_origin[0])*self.scale,
                  (b*cx+d*cy+ty-self._buf_origin[1])*self.scale)
        self._buf.blit(transformed, (round(center[0]-transformed.get_width()/2),
                                     round(center[1]-transformed.get_height()/2)))

    def _apply_clip(self):
        if self._layer_empty:
            self._buf.set_clip((0,0,0,0))
            return
        rect = None
        for x, y, w, h in self._clip:
            ox, oy = self._buf_origin
            left, top, right, bottom = (round(v * self.scale) for v in (x-ox,y-oy,x+w-ox,y+h-oy))
            r = pygame.Rect(left, top, max(0,right-left), max(0,bottom-top))
            rect = r if rect is None else rect.clip(r)
        self._buf.set_clip(rect)  # None = full surface

    def clear(self, color):
        self._buf.fill(_rgb(color))

    def fill_rect(self, x, y, w, h, color, radius=0):
        if w <= 0 or h <= 0:
            return
        x, y = self._translate(x, y)
        c = self._effect_color(color)
        if len(c) > 3 and c[3] < 255:
            # pygame.draw REPLACES pixels (alpha included) on a SRCALPHA buf,
            # so translucent fills accumulate frame over frame — composite
            # through a temp surface instead
            tmp = pygame.Surface((max(1, int(w * self.scale)),
                                  max(1, int(h * self.scale))),
                                 pygame.SRCALPHA)
            pygame.draw.rect(tmp, c, tmp.get_rect(),
                             border_radius=int(radius * self.scale))
            self._buf.blit(tmp, self._s(x, y))
            return
        pygame.draw.rect(self._buf, c,
                         (*self._s(x, y)[:2], int(w * self.scale),
                          int(h * self.scale)),
                         border_radius=int(radius * self.scale))

    def overlay_rect(self, x, y, w, h, color, radius=0):
        self.fill_rect(x, y, w, h, color, radius)  # fill_rect blends now

    def stroke_rect(self, x, y, w, h, color, width=1, radius=0):
        x, y = self._translate(x, y)
        c = self._effect_color(color)
        sw, sh = (max(1, int(w * self.scale)),
                  max(1, int(h * self.scale)))
        line_w = max(1, int(width * self.scale))
        if len(c) > 3 and c[3] < 255:
            # Like fill_rect, pygame.draw replaces destination alpha on an
            # SRCALPHA surface. Draw translucent strokes into a temporary
            # layer so they blend over the already-opaque frame like GL.
            tmp = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(tmp, c, tmp.get_rect(), width=line_w,
                             border_radius=int(radius * self.scale))
            self._buf.blit(tmp, self._s(x, y))
            return
        pygame.draw.rect(self._buf, c,
                         (*self._s(x, y)[:2], sw, sh), width=line_w,
                         border_radius=int(radius * self.scale))

    def line(self, x1, y1, x2, y2, color, width=1):
        x1, y1 = self._translate(x1, y1)
        x2, y2 = self._translate(x2, y2)
        pygame.draw.line(self._buf, self._effect_color(color),
                         self._s(x1, y1), self._s(x2, y2),
                         width=max(1, int(width * self.scale)))

    def circle(self, x, y, radius, color, fill=True):
        x, y = self._translate(x, y)
        c = self._effect_color(color)
        rr = max(1, int(radius * self.scale))
        if len(c) > 3 and c[3] < 255:
            size = rr * 2 + 4
            tmp = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(tmp, c, (size // 2, size // 2), rr,
                               0 if fill else max(1, round(self.scale)))
            px, py = self._s(x,y)
            self._buf.blit(tmp, (round(px) - size // 2,
                                 round(py) - size // 2))
            return
        pygame.draw.circle(self._buf, c, self._s(x, y), rr,
                           0 if fill else max(1, round(self.scale)))

    def arc(self, x, y, radius, start_angle, end_angle, color, width=1):
        if radius <= 0 or width <= 0 or end_angle <= start_angle:
            return
        x, y = self._translate(x, y)
        rect = pygame.Rect(
            0, 0, int(radius * 2 * self.scale),
            int(radius * 2 * self.scale))
        rect.center = self._s(x, y)
        c = self._effect_color(color)
        line_width = max(1, int(width * self.scale))
        # Renderer angles run clockwise in screen coordinates, like GL.
        # pygame's arc API uses a mathematical (counterclockwise) y axis.
        if c[3] < 255:
            surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.arc(surface, c, surface.get_rect(),
                            -end_angle, -start_angle, line_width)
            self._buf.blit(surface, rect.topleft)
        else:
            pygame.draw.arc(self._buf, c, rect, -end_angle, -start_angle,
                            line_width)

    def blit(self, surface, x, y, alpha=1.0):
        """surface is already in device px (text/images render at scale)."""
        x, y = self._translate(x, y)
        alpha *= self.opacity
        s = surface
        s = _as_alpha_surface(s)
        if alpha < 1.0:
            s = s.copy()
            s.set_alpha(int(alpha * 255))
        self._buf.blit(s, self._s(x, y))

    def blit_scaled(self, surface, x, y, width, height, alpha=1.0):
        """Draw a cached device-pixel surface at a logical target size."""
        x, y = self._translate(x, y)
        alpha *= self.opacity
        target = (max(1, round(width * self.scale)),
                  max(1, round(height * self.scale)))
        s = surface if surface.get_size() == target else \
            pygame.transform.smoothscale(surface, target)
        s = _as_alpha_surface(s)
        if alpha < 1.0:
            s = s.copy()
            s.set_alpha(int(alpha * 255))
        self._buf.blit(s, self._s(x, y))

    def clip_push(self, x, y, w, h):
        x, y = self._translate(x, y)
        self._clip.append((x, y, w, h))
        self._apply_clip()

    def clip_pop(self):
        self._clip.pop()
        self._apply_clip()

    def flip(self):
        out = pygame.transform.smoothscale(self._buf, self.screen.get_size())
        self.screen.blit(out, (0, 0))
        if self.window is not None:
            self.window.flip()
        else:
            pygame.display.flip()
        if os.environ.get("SATURN_SHOT"):  # test hook: dump last frame to png
            pygame.image.save(self.screenshot(), os.environ["SATURN_SHOT"])

    def backdrop_blur(self, x, y, w, h, sigma_x, sigma_y, radius=0):
        """Blur the already-drawn buffer under this logical rect in place."""
        from ..painting import (BlurResultCache, backdrop_blur_surface,
                                blur_source_digest, corners,
                                normalize_blur_sigmas, shape_mask)
        if w <= 0 or h <= 0:
            return
        sx, sy = normalize_blur_sigmas(sigma_x, sigma_y, self.scale)
        if sx < 0.5 and sy < 0.5:
            return
        x, y = self._translate(x, y)
        # Expand slightly so the blur kernel can sample edge neighbors.
        pad = math.ceil(3 * max(sx, sy))
        x0 = max(0, math.floor(x * self.scale) - pad)
        y0 = max(0, math.floor(y * self.scale) - pad)
        x1 = min(self._buf.get_width(), math.ceil((x + w) * self.scale) + pad)
        y1 = min(self._buf.get_height(), math.ceil((y + h) * self.scale) + pad)
        rw, rh = x1 - x0, y1 - y0
        if rw <= 0 or rh <= 0:
            return
        region = self._buf.subsurface((x0, y0, rw, rh)).copy()
        qx, qy = round(sx * 4) / 4, round(sy * 4) / 4
        rad_key = round(float(radius) * self.scale * 4) / 4
        cache_key = (x0, y0, rw, rh, qx, qy, rad_key)
        digest = blur_source_digest(region.get_buffer().raw)
        if not hasattr(self, "_blur_cache"):
            self._blur_cache = BlurResultCache()
        blurred = self._blur_cache.get(cache_key, digest)
        if blurred is None:
            blurred = backdrop_blur_surface(region, sx, sy)
            self._blur_cache.put(cache_key, digest, blurred.copy())
        # Restrict the write to the container's rounded rect in device pixels.
        cx0 = max(x0, round(x * self.scale))
        cy0 = max(y0, round(y * self.scale))
        cx1 = min(x1, round((x + w) * self.scale))
        cy1 = min(y1, round((y + h) * self.scale))
        cw, ch = cx1 - cx0, cy1 - cy0
        if cw <= 0 or ch <= 0:
            return
        cropped = blurred.subsurface((cx0 - x0, cy0 - y0, cw, ch)).copy()
        if radius:
            mask = shape_mask(cw, ch, corners(radius, self.scale, cw, ch))
            cropped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            # Keep unblurred pixels outside the rounded corner instead of
            # wiping them to transparent when the mask has alpha < 255.
            dest = self._buf.subsurface((cx0, cy0, cw, ch)).copy()
            dest.blit(cropped, (0, 0))
            self._buf.blit(dest, (cx0, cy0))
        else:
            self._buf.blit(cropped, (cx0, cy0))

    def screenshot(self):
        """The composited frame (2x buffer downscaled to window size)."""
        return pygame.transform.smoothscale(self._buf, self.screen.get_size())
