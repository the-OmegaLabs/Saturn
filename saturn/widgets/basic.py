"""Basic visual controls: Icon, Image, Card, ProgressBar, ProgressRing."""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Unpack

import base64
import io
import math
import time
from pathlib import Path

import pygame

from .containers import Container
from .. import colors
from .. import motion
from ..animation import _cubic_bezier, ease
from ..control import Control, ControlOptions
from ..text import render_icon_cached
from ..types import AnimationCurve, BoxFit
from ..types import as_padding
from ._compat import value, reject_options, shape_radius, constrain

ASSETS = Path(__file__).parent.parent / "assets"
_img_cache: dict = {}


def _as_alpha_surface(surface: pygame.Surface) -> pygame.Surface:
    """Return an RGBA surface without consulting pygame.display.

    ``Surface.convert_alpha()`` still relies on the legacy display module's
    pixel format.  Saturn creates windows through ``pygame.Window`` instead,
    and OpenGL windows intentionally have no display-module surface.  Blitting
    into an explicit SRCALPHA surface performs the only conversion we need and
    works for both software and OpenGL windows.
    """
    if surface.get_flags() & pygame.SRCALPHA:
        return surface
    converted = pygame.Surface(surface.get_size(), pygame.SRCALPHA, 32)
    converted.blit(surface, (0, 0))
    return converted


def _segment(t, start_t, end_t, start_value, end_value, curve):
    if t <= start_t:
        return start_value
    if t >= end_t:
        return end_value
    local = (t - start_t) / (end_t - start_t)
    if curve is not None:
        local = _cubic_bezier(local, *curve)
    return start_value + (end_value - start_value) * local


class Icon(Control):
    def __init__(self, icon, *, color=None, size: float = 24,
                 semantics_label=None, shadows=None, fill=None, apply_text_scaling=None,
                 grade=None, weight=None, optical_size=None, blend_mode=None, **base: Unpack[ControlOptions]):
        reject_options("Icon", fill=fill, grade=grade, weight=weight, optical_size=optical_size,
                       apply_text_scaling=apply_text_scaling if apply_text_scaling else None,
                       blend_mode=blend_mode if value(blend_mode) not in (None,"srcOver") else None)
        super().__init__(semantics_label=semantics_label, **base)
        self.icon = icon            # Icons member (codepoint int)
        self.color = color          # None → on_surface
        self.size = 24 if size is None else size
        self.shadows = shadows
        self.apply_text_scaling = apply_text_scaling
        self._icon_shadow_cache = {}

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else self.size,
                self._height if self._height is not None else self.size)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        color = colors.parse_color(self.color or colors.Colors.ON_SURFACE)
        gpu_tint = getattr(r, "native_texture_tint", False)
        surf = render_icon_cached(
            self.icon, round(self.size * r.scale),
            (255, 255, 255, 255) if gpu_tint else color)
        # The glyph surface is cropped tight; center it in whatever rect the
        # parent placed us in (a fixed Container hands over its full inner
        # box, mirroring Flutter's Icon which wraps the glyph in a Center).
        _, _, rw, rh = self._rect
        ox = (rw - surf.get_width() / r.scale) / 2
        oy = (rh - surf.get_height() / r.scale) / 2
        if self.shadows:
            for shadow in self.shadows if isinstance(self.shadows,list) else [self.shadows]:
                key = (self.icon,self.size,r.scale,shadow.color,shadow.blur_radius,shadow.offset.x,shadow.offset.y)
                cached = self._icon_shadow_cache.get(key)
                if cached is None:
                    rgba = colors.parse_color(shadow.color)
                    bitmap = render_icon_cached(self.icon,round(self.size*r.scale),rgba)
                    pad = math.ceil(max(0,shadow.blur_radius)*r.scale*3)
                    layer = pygame.Surface((bitmap.get_width()+pad*2,bitmap.get_height()+pad*2),pygame.SRCALPHA)
                    layer.blit(bitmap,(pad,pad))
                    if pad:
                        layer = pygame.transform.gaussian_blur(layer,shadow.blur_radius*r.scale,False)
                    if len(self._icon_shadow_cache) >= 32:
                        self._icon_shadow_cache.pop(next(iter(self._icon_shadow_cache)))
                    cached = self._icon_shadow_cache[key] = (layer,pad)
                layer,pad = cached
                r.blit_cached(layer,x+ox+shadow.offset.x-pad/r.scale,y+oy+shadow.offset.y-pad/r.scale)
        if gpu_tint:
            r.blit_tinted_scaled(surf, x + ox, y + oy,
                                 surf.get_width() / r.scale,
                                 surf.get_height() / r.scale, color)
        else:
            r.blit_cached(surf, x + ox, y + oy)

    __unsupported_parameters__ = {"fill", "grade", "weight", "optical_size", "blend_mode", "apply_text_scaling"}


class Image(Control):
    def __init__(self, src=None, *, fit=None, border_radius=None, color=None,
                 error_content=None, repeat="noRepeat", color_blend_mode=None,
                 gapless_playback=False, semantics_label=None, exclude_from_semantics=False,
                 filter_quality="medium", placeholder_src=None, placeholder_fit=None,
                 fade_in_animation=None, placeholder_fade_out_animation=None,
                 cache_width=None, cache_height=None, anti_alias=False, **base: Unpack[ControlOptions]):
        reject_options("Image", fade_in_animation=fade_in_animation,
                       placeholder_fade_out_animation=placeholder_fade_out_animation,
                       color_blend_mode=color_blend_mode if value(color_blend_mode) not in (None,"modulate") else None)
        super().__init__(semantics_label=None if exclude_from_semantics else semantics_label, **base)
        self.src = src              # file path, bytes, or data:base64 URI
        self.fit = fit              # v1: None/BoxFit.FILL stretch, CONTAIN fits
        self.border_radius = border_radius
        self.color = color
        self.error_content = error_content
        self.repeat = repeat
        self.gapless_playback = gapless_playback
        self.filter_quality = filter_quality
        self.placeholder_src = placeholder_src
        self.placeholder_fit = placeholder_fit
        self.cache_width,self.cache_height = cache_width,cache_height
        self.anti_alias = anti_alias
        self.exclude_from_semantics = exclude_from_semantics
        self._load_error = False
        self._surface = None
        self._loaded_key = None
        self._svg_data = None
        self._svg_source = None
        self._is_svg = False
        self._prepared_key = None
        self._prepared_surface = None

    def _children(self):
        return [self.error_content] if isinstance(self.error_content,Control) else []

    def _load(self):
        if self.src is None:
            return None
        key = self.src if isinstance(self.src, (str, bytes)) else id(self.src)
        if key == self._loaded_key:
            return self._surface
        data = None
        if isinstance(self.src, bytes):
            data = self.src
        elif isinstance(self.src, str) and self.src.startswith("data:"):
            b64 = self.src.split(",", 1)[1]
            data = base64.b64decode(b64)
        previous_svg = self._is_svg
        self._is_svg = (str(self.src).lower().endswith(".svg") if data is None
                        else b"<svg" in data[:2048].lower())
        try:
            if data is not None:
                s = pygame.image.load(io.BytesIO(data), ".svg" if self._is_svg else "")
            else:
                s = pygame.image.load(self.src)
        except (pygame.error, OSError, ValueError):
            self._load_error = True
            self._loaded_key = key
            if self.gapless_playback and self._surface is not None:
                self._is_svg = previous_svg
                return self._surface
            if self.placeholder_src is not None:
                placeholder = Image(self.placeholder_src, fit=self.placeholder_fit)
                self._surface = placeholder._load()
                self._is_svg = False
                return self._surface
            self._surface = None
            return None
        self._load_error = False
        if self.cache_width is not None or self.cache_height is not None:
            sw,sh = s.get_size()
            cw = self.cache_width or max(1,round(sw*self.cache_height/sh))
            ch = self.cache_height or max(1,round(sh*self.cache_width/sw))
            if cw <= 0 or ch <= 0:
                raise ValueError("image cache dimensions must be positive")
            s = pygame.transform.smoothscale(s,(cw,ch))
        self._surface = _as_alpha_surface(s)
        self._loaded_key = key
        self._svg_data = data if self._is_svg else None
        self._svg_source = self.src if self._is_svg else None
        self._prepared_key = None
        return self._surface

    def _prepare(self, source, width, height, tint, gpu_scale=False):
        # Native sampling can upscale a bitmap; CPU minification and SVG
        # rasterization are retained to preserve source detail at small sizes.
        if (gpu_scale and not self._is_svg and
                width >= source.get_width() and height >= source.get_height()):
            width, height = source.get_size()
        key = (self._loaded_key, width, height, tint, value(self.filter_quality))
        if key != self._prepared_key:
            if self._is_svg:
                svg = (io.BytesIO(self._svg_data) if self._svg_data is not None
                       else self._svg_source)
                prepared = _as_alpha_surface(
                    pygame.image.load_sized_svg(svg, (width, height)))
            elif source.get_size() == (width, height):
                prepared = source
            else:
                # Minify once before the GPU upload: one bilinear texture
                # sample cannot adequately filter a large bitmap to an icon.
                transform = pygame.transform.scale if value(self.filter_quality) == "none" else pygame.transform.smoothscale
                prepared = transform(source, (width, height))
            if tint is not None:
                prepared = prepared.copy()
                prepared.fill(tint, special_flags=pygame.BLEND_RGBA_MULT)
            self._prepared_surface = prepared
            self._prepared_key = key
        return self._prepared_surface

    def _intrinsic(self, max_w, max_h, scale):
        s = self._load()
        if s is None and self.error_content is not None:
            return self.error_content._intrinsic(max_w,max_h,scale)
        nw, nh = s.get_size() if s else (0, 0)
        w = self._width if self._width is not None else \
            (nw / nh * self._height if self._height is not None and nh else nw)
        h = self._height if self._height is not None else \
            (nh / nw * self._width if self._width is not None and nw else nh)
        return w, h

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        if self.error_content is not None:
            self.error_content._place(x,y,w,h,scale)

    def _draw(self, r, x, y):
        s = self._load()
        if s is None:
            if self.error_content is not None:
                self.error_content._draw_all(r,x-self._rect[0],y-self._rect[1])
            return
        tint = colors.parse_color(self.color) if self.color is not None else None
        _, _, w, h = self._rect
        tw, th = round(w * r.scale), round(h * r.scale)
        if tw <= 0 or th <= 0:
            return
        sw, sh = s.get_size()
        fit = value(self.fit)
        if fit in ("contain","cover","fitWidth","fitHeight","none","scaleDown") and sw and sh:
            k = ({"contain":min(tw/sw,th/sh),"cover":max(tw/sw,th/sh),
                  "fitWidth":tw/sw,"fitHeight":th/sh,"none":1,
                  "scaleDown":min(1,tw/sw,th/sh)})[fit]
            dw, dh = max(1, round(sw * k)), max(1, round(sh * k))
            dx, dy = x + (w - dw / r.scale) / 2, y + (h - dh / r.scale) / 2
        else:
            dw, dh = tw, th
            dx, dy = x, y
        native = getattr(r, "native_texture_scaling", False)
        gpu_tint = tint is not None and getattr(r, "native_texture_tint", False)
        if self.border_radius or value(self.repeat) != "noRepeat":
            from ..painting import shape_mask, corners
            key = (self._loaded_key,tw,th,dw,dh,str(self.border_radius),value(self.repeat),tint,value(self.filter_quality))
            if getattr(self,"_decorated_key",None) != key:
                canvas = pygame.Surface((tw,th),pygame.SRCALPHA)
                bitmap = self._prepare(s,dw,dh,tint,False)
                bx,by = round((tw-dw)/2),round((th-dh)/2)
                mode = value(self.repeat)
                xs = range(bx % dw-dw,tw,dw) if mode in ("repeat","repeatX") else (bx,)
                ys = range(by % dh-dh,th,dh) if mode in ("repeat","repeatY") else (by,)
                for yy in ys:
                    for xx in xs:
                        canvas.blit(bitmap,(xx,yy))
                if self.border_radius:
                    canvas.blit(shape_mask(tw,th,corners(self.border_radius,r.scale,tw,th)),(0,0),special_flags=pygame.BLEND_RGBA_MULT)
                self._decorated_surface,self._decorated_key = canvas,key
            r.blit_cached(self._decorated_surface,x,y)
            return
        prepared = self._prepare(s, dw, dh, None if gpu_tint else tint, native)
        clipped = dw > tw or dh > th
        if clipped:
            r.clip_push(x,y,w,h)
        if gpu_tint:
            r.blit_tinted_scaled(prepared, dx, dy, dw / r.scale, dh / r.scale, tint)
        elif native:
            r.blit_cached_scaled(prepared, dx, dy, dw / r.scale, dh / r.scale)
        else:
            r.blit(prepared, dx, dy)
        if clipped:
            r.clip_pop()

    def _draw_all(self,r,ox=0,oy=0):
        if self.visible:
            self._effects_begin(r, ox, oy)
            try:
                self._draw(r,self._rect[0]+ox,self._rect[1]+oy)
            finally:
                self._effects_end(r)

    __unsupported_parameters__ = {"color_blend_mode", "fade_in_animation", "placeholder_fade_out_animation"}


class Card(Container):
    """Card with elevated, filled and outlined Expressive surfaces."""

    def __init__(self, content=None, *, elevation: float = 1,
                 variant: str = "elevated", bgcolor=None, shadow_color=None,
                 shape=None, clip_behavior=None, semantic_container=True,
                 show_border_on_foreground=True, **base: Unpack[ControlOptions]):
        from ..types import Border, BoxShadow, Offset

        elevation = 1 if elevation is None else elevation
        self.elevation = elevation
        self.variant = variant
        self.card_shape = shape
        if shape is not None:
            shape_radius(shape,100,100,12)
        self.shadow_color = shadow_color
        self.semantic_container = semantic_container
        self.show_border_on_foreground = show_border_on_foreground
        base.setdefault("border_radius", getattr(shape,"radius",12) if shape is not None else 12)
        if bgcolor is not None:
            base["bgcolor"] = bgcolor
        if value(variant) == "filled":
            base.setdefault("bgcolor", colors.Colors.SURFACE_CONTAINER_HIGHEST)
        elif value(variant) == "outlined":
            base.setdefault("bgcolor", colors.Colors.SURFACE)
            base.setdefault("border", Border.all(1, colors.Colors.OUTLINE_VARIANT))
        else:
            base.setdefault("bgcolor", colors.Colors.SURFACE_CONTAINER_LOW)
            if elevation > 0:
                base.setdefault("shadow", BoxShadow(
                    blur_radius=3 * elevation, offset=Offset(0, elevation),
                    color=shadow_color or "#33000000"))
        if shape is not None and getattr(shape,"side",None) is not None:
            side = shape.side
            base["border"] = Border.all(side.width,side.color)
        super().__init__(content, clip_behavior=clip_behavior, **base)

    def _radius(self):
        return shape_radius(self.card_shape,self._rect[2],self._rect[3],super()._radius())

    def _draw_all(self,r,ox=0,oy=0):
        if not self.visible:
            return
        if not self.show_border_on_foreground or self.border is None:
            return super()._draw_all(r,ox,oy)
        border = self.border
        self._effects_begin(r,ox,oy)
        try:
            self.border = None
            try:
                self._draw(r,self._rect[0]+ox,self._rect[1]+oy)
            finally:
                self.border = border
            if self.content is not None:
                self.content._draw_all(r,ox,oy)
            if self._clip_children:
                r.clip_pop()
            x,y,w,h = self._rect
            side = border.left
            if side.color is not None and side.width > 0:
                r.stroke_rect(x+ox,y+oy,w,h,colors.parse_color(side.color),width=side.width,radius=self._radius())
        finally:
            self._effects_end(r)


class ProgressBar(Control):
    def __init__(self, value: float | None = None, *, bar_height: float = 4,
                 color=None, bgcolor=None, border_radius=None, semantics_label=None,
                 semantics_value=None, stop_indicator_color=None, stop_indicator_radius=None,
                 track_gap=None, year_2023=None, **base: Unpack[ControlOptions]):
        super().__init__(semantics_label=semantics_label, **base)
        self.value = value
        self.bar_height = 4 if bar_height is None else bar_height
        self.color = color
        self.bgcolor = bgcolor
        self.border_radius = border_radius
        self.semantics_value = semantics_value
        self.stop_indicator_color = stop_indicator_color
        self.stop_indicator_radius = stop_indicator_radius
        self.track_gap = (0 if year_2023 else 4) if track_gap is None else track_gap
        self.year_2023 = year_2023
        self._display_value = 0.0 if value is None else float(value)
        self._last_value = value
        self._phase_started = time.perf_counter()
        self._phase = 0.0

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else (max_w or 100),
                self._height if self._height is not None else self.bar_height)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        track = colors.parse_color(self.bgcolor or colors.Colors.SECONDARY_CONTAINER)
        active = colors.parse_color(self.color or colors.Colors.PRIMARY)

        def segment(left, right, color):
            width = right - left
            if width > 0:
                r.fill_rect(left, y, width, h, color,
                            radius=(self.border_radius if isinstance(self.border_radius,(int,float)) else
                                    (0 if self.year_2023 else min(h/2,width/2))))

        if self.value is None:
            phase = self._phase
            # Exact Material Web 2s keyframe geometry: two independently
            # translating and scaling bars, clipped by the track.
            p_tx = (0.0 if phase <= 0.2 else
                    _segment(phase, 0.2, 0.5915, 0.0, 0.836714,
                             (0.5, 0.0, 0.701732, 0.495819)) if phase <= 0.5915
                    else _segment(phase, 0.5915, 1.0, 0.836714, 2.00611,
                                  (0.302435, 0.381352, 0.55, 0.956352)))
            p_scale = (0.08 if phase <= 0.3665 else
                       _segment(phase, 0.3665, 0.6915, 0.08, 0.661479,
                                (0.334731, 0.12482, 0.785844, 1.0))
                       if phase <= 0.6915 else
                       _segment(phase, 0.6915, 1.0, 0.661479, 0.08,
                                (0.06, 0.11, 0.6, 1.0)))
            s_tx = (_segment(phase, 0.0, 0.25, 0.0, 0.376519,
                             (0.15, 0.0, 0.515058, 0.409685))
                    if phase <= 0.25 else
                    _segment(phase, 0.25, 0.4835, 0.376519, 0.843862,
                             (0.31033, 0.284058, 0.8, 0.733712))
                    if phase <= 0.4835 else
                    _segment(phase, 0.4835, 1.0, 0.843862, 1.60278,
                             (0.4, 0.627035, 0.6, 0.902026)))
            s_scale = (_segment(phase, 0.0, 0.1915, 0.08, 0.457104,
                                (0.205028, 0.057051, 0.57661, 0.453971))
                       if phase <= 0.1915 else
                       _segment(phase, 0.1915, 0.4415, 0.457104, 0.72796,
                                (0.152313, 0.196432, 0.648374, 1.00432))
                       if phase <= 0.4415 else
                       _segment(phase, 0.4415, 1.0, 0.72796, 0.08,
                                (0.257759, -0.003163, 0.211762, 1.38179)))
            bars = ((x + w * (-1.45167 + p_tx), w * p_scale),
                    (x + w * (-0.548889 + s_tx), w * s_scale))
            visible = sorted((max(x, bx), min(x + w, bx + bw))
                             for bx, bw in bars if bx + bw > x and bx < x + w)
            cursor = x
            for left, right in visible:
                segment(cursor, left - self.track_gap, track)
                cursor = max(cursor, right + self.track_gap)
            segment(cursor, x + w, track)
            r.clip_push(x, y, w, h)
            for bx, bw in bars:
                segment(bx, bx + bw, active)
            r.clip_pop()
        else:
            progress = max(0.0, min(1.0, self._display_value))
            active_end = x + w * progress
            segment(active_end + (self.track_gap if progress else 0), x + w, track)
            segment(x, active_end, active)
        stop_size = min(4.0 if self.stop_indicator_radius is None else self.stop_indicator_radius*2, h, w)
        if not self.year_2023 and self.value is not None and stop_size > 0:
            stop_offset = min((h - stop_size) / 2, 6.0)
            r.circle(x + w - stop_size / 2 - stop_offset, y + h / 2,
                     stop_size / 2, colors.parse_color(self.stop_indicator_color) if self.stop_indicator_color else active)

    def _prepare_animations(self, now: float):
        super()._prepare_animations(now)
        if self.value is None:
            if self._last_value is not None:
                self._last_value = None
                self._phase_started = now
        elif self.value != self._last_value:
            self._last_value = self.value
            self._animate_internal("_display_value", float(self.value),
                                   motion.MEDIUM1, motion.PROGRESS, now=now)

    def _tick_animations(self, now: float) -> bool:
        active = super()._tick_animations(now)
        if self.value is None:
            self._phase = ((now - self._phase_started) % 2.0) / 2.0
            return True
        return active


class ProgressRing(Control):
    def __init__(self, value: float | None = None, *, stroke_width: float = 4,
                 color=None, bgcolor=None, stroke_align=None, stroke_cap=None,
                 semantics_label=None, semantics_value=None, track_gap=None,
                 size_constraints=None, padding=None, year_2023=None, **base: Unpack[ControlOptions]):
        super().__init__(semantics_label=semantics_label, **base)
        self.value = value
        self.stroke_width = 4 if stroke_width is None else stroke_width
        self.color = color
        self.bgcolor = bgcolor
        self.stroke_align = 0 if stroke_align is None else stroke_align
        self.stroke_cap = stroke_cap
        self.semantics_value = semantics_value
        self.track_gap = (0 if year_2023 else 4) if track_gap is None else track_gap
        self.size_constraints = size_constraints
        self.padding = padding
        self.year_2023 = year_2023
        self._display_value = 0.0 if value is None else float(value)
        self._last_value = value
        self._phase_started = time.perf_counter()
        self._phase = 0.0

    def _intrinsic(self, max_w, max_h, scale):
        p = as_padding(self.padding)
        return constrain(self._width if self._width is not None else 40+p.left+p.right,
                         self._height if self._height is not None else 40+p.top+p.bottom,self.size_constraints)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _round_arc(self,r, cx, cy, radius, start, end, color, width):
        if end <= start:
            return
        r.arc(cx, cy, radius, start, end, color, width=width)
        cap = value(self.stroke_cap) or ("butt" if self.year_2023 else "round")
        if end - start < 2 * math.pi - 1e-6 and color[3] == 255 and cap == "round":
            centerline = radius - width / 2
            for angle in (start, end):
                r.circle(cx + math.cos(angle) * centerline,
                         cy + math.sin(angle) * centerline,
                         width / 2, color)
        elif cap == "square" and end-start < 2*math.pi-1e-6:
            for angle in (start,end):
                xx,yy = cx+math.cos(angle)*(radius-width/2),cy+math.sin(angle)*(radius-width/2)
                r.fill_rect(xx-width/2,yy-width/2,width,width,color)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        p = as_padding(self.padding)
        x,y,w,h = x+p.left,y+p.top,w-p.left-p.right,h-p.top-p.bottom
        cx, cy = x + w / 2, y + h / 2
        diameter = min(w, h)
        if diameter <= 0:
            return
        radius = diameter / 2 + self.stroke_width*self.stroke_align/2
        width = min(self.stroke_width, diameter)
        if width <= 0:
            return
        active = colors.parse_color(self.color or colors.Colors.PRIMARY)
        track_color = self.bgcolor or (colors.Colors.SECONDARY_CONTAINER
                                       if self.value is not None else None)
        track = colors.parse_color(track_color) if track_color else None
        if self.value is None:
            elapsed = self._phase
            arc_phase = (elapsed % 1.333) / 1.333
            if arc_phase <= 0.5:
                sweep = 10 + 260 * ease(
                    AnimationCurve.FAST_OUT_SLOWIN, arc_phase * 2)
            else:
                sweep = 270 - 260 * ease(
                    AnimationCurve.FAST_OUT_SLOWIN, (arc_phase - 0.5) * 2)
            linear_rotation = (elapsed / (1.333 * 360 / 306) * 360) % 360
            cycle = (elapsed % (4 * 1.333)) / (4 * 1.333)
            arc_rotation = ease(AnimationCurve.FAST_OUT_SLOWIN, cycle) * 1080
            start = math.radians(-90 + linear_rotation + arc_rotation)
            sweep = math.radians(sweep)
        else:
            start = -math.pi / 2
            sweep = 2 * math.pi * max(0.0, min(1.0, self._display_value))
        if track is not None and track[3] > 0:
            gap = min(sweep, 2 * (self.track_gap + width) / diameter)
            self._round_arc(r, cx, cy, radius,
                            start + sweep + gap, start + 2 * math.pi - gap,
                            track, width)
        self._round_arc(r, cx, cy, radius, start, start + sweep, active, width)

    def _prepare_animations(self, now: float):
        super()._prepare_animations(now)
        if self.value is None:
            if self._last_value is not None:
                self._last_value = None
                self._phase_started = now
        elif self.value != self._last_value:
            self._last_value = self.value
            self._animate_internal("_display_value", float(self.value),
                                   motion.LONG2,
                                   AnimationCurve.DECELERATE, now=now)

    def _tick_animations(self, now: float) -> bool:
        active = super()._tick_animations(now)
        if self.value is None:
            self._phase = now - self._phase_started
            return True
        return active
