"""OpenGL renderer (moderngl): SDF rounded rects + textured quads.

Draw calls target a supersampled framebuffer and resolve into the window;
blending is standard alpha. Clip = scissor stack. Coordinates arrive in
logical px with origin top-left and are flipped on the GPU side.
"""
from __future__ import annotations

import hashlib
import ctypes
import math
import os
import struct
from array import array
from collections import OrderedDict
from pathlib import Path

import pygame
import moderngl

from ..colors import parse_color
from .base import Renderer
from .geometry import arc_triangles, polygon_triangles, stroke_triangles


def _set_swap_interval(enabled: bool) -> bool:
    """Request SDL synchronization and report the active driver setting."""
    try:
        dll = ctypes.CDLL(str(Path(pygame.__file__).with_name("SDL2.dll")))
        dll.SDL_GL_SetSwapInterval.argtypes = [ctypes.c_int]
        dll.SDL_GL_SetSwapInterval.restype = ctypes.c_int
        dll.SDL_GL_GetSwapInterval.restype = ctypes.c_int
        dll.SDL_GL_SetSwapInterval(1 if enabled else 0)
        return dll.SDL_GL_GetSwapInterval() != 0
    except (AttributeError, OSError):
        return False

RECT_VS = """
#version 330
in vec2 in_pos;          // px, origin top-left
in vec2 in_center;       // rect center px
in vec2 in_half;         // half size px
in vec2 in_rb;           // radius, border width (radius < 0 -> no SDF)
in vec4 in_color;
in vec4 in_border_color;
uniform vec2 u_size;
uniform mat3 u_transform;
out vec2 v_local;
flat out vec2 v_half;
flat out vec2 v_rb;
out vec4 v_color;
flat out vec4 v_border_color;
void main() {
    vec2 transformed = (u_transform * vec3(in_pos, 1.0)).xy;
    vec2 out_pos = vec2(transformed.x, u_size.y - transformed.y);
    gl_Position = vec4(out_pos / u_size * 2.0 - 1.0, 0.0, 1.0);
    v_local = in_pos - in_center;
    v_half = in_half;
    v_rb = in_rb;
    v_color = in_color;
    v_border_color = in_border_color;
}
"""

RECT_FS = """
#version 330
in vec2 v_local;
flat in vec2 v_half;
flat in vec2 v_rb;
in vec4 v_color;
flat in vec4 v_border_color;
out vec4 frag;
float sd_round(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}
void main() {
    float radius = v_rb.x;
    float bw = v_rb.y;
    vec4 c = v_color;
    float d;
    if (radius < 0.0) {
        d = -1.0;  // geometry-only quad, no SDF
    } else {
        d = sd_round(v_local, v_half, radius);
    }
    float aa = max(fwidth(d), 0.001);
    if (bw > 0.0) {
        float border_mix = smoothstep(-bw - aa, -bw + aa, d);
        c = mix(v_color, v_border_color, border_mix);
    }
    float alpha = 1.0 - smoothstep(-aa, aa, d);
    if (c.a * alpha <= 0.0) discard;
    frag = vec4(c.rgb, c.a * alpha);
}
"""

TEX_VS = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
in vec4 in_color;
uniform vec2 u_size;
uniform mat3 u_transform;
out vec2 v_uv;
out vec4 v_color;
void main() {
    vec2 transformed = (u_transform * vec3(in_pos, 1.0)).xy;
    vec2 out_pos = vec2(transformed.x, u_size.y - transformed.y);
    gl_Position = vec4(out_pos / u_size * 2.0 - 1.0, 0.0, 1.0);
    v_uv = in_uv;
    v_color = in_color;
}
"""

TEX_FS = """
#version 330
in vec2 v_uv;
in vec4 v_color;
uniform sampler2D u_tex;
out vec4 frag;
void main() {
    vec4 t = texture(u_tex, v_uv);
    frag = vec4(t.rgb, t.a) * v_color;
}
"""

STATE_VS = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
uniform vec2 u_size;
uniform mat3 u_transform;
out vec2 v_uv;
void main() {
    vec2 transformed = (u_transform * vec3(in_pos, 1.0)).xy;
    vec2 out_pos = vec2(transformed.x, u_size.y - transformed.y);
    gl_Position = vec4(out_pos / u_size * 2.0 - 1.0, 0.0, 1.0);
    v_uv = in_uv;
}
"""

STATE_FS = """
#version 330
in vec2 v_uv;
uniform vec2 u_rect_size;
uniform vec4 u_radii;
uniform vec2 u_ripple_center;
uniform float u_ripple_radius;
uniform vec4 u_color;
uniform float u_hover;
uniform float u_pressed;
uniform float u_mode;
uniform vec4 u_wave;
uniform vec4 u_info;
uniform vec4 u_secondary_color;
out vec4 frag;
""" + Path(__file__).with_name('wave.glsl').read_text() + Path(__file__).with_name('effects.glsl').read_text() + """
void main() {
    vec2 p = v_uv * u_rect_size;
    if (u_mode > 3.5) {
        frag = procedural_effect(v_uv, u_rect_size, u_mode - 4.0, u_color,
                                 u_secondary_color, u_wave, u_info);
        return;
    }
    if (u_mode > .5) {
        if (u_mode > 2.5) {
            frag = vec4(u_color.rgb, u_color.a *
                        elevation_shadow(p, u_rect_size, u_wave, u_info));
            return;
        }
        float distance = u_mode < 1.5 ? wave_line_distance(p, u_wave, u_info) :
                         wave_arc_distance(p - u_rect_size * .5, u_wave, u_info);
        float aa = max(fwidth(distance), .001);
        float alpha = 1.0 - smoothstep(-aa, aa, distance);
        frag = vec4(u_color.rgb, u_color.a * alpha);
        return;
    }
    float radius = p.y < u_rect_size.y * 0.5
        ? (p.x < u_rect_size.x * 0.5 ? u_radii.x : u_radii.y)
        : (p.x < u_rect_size.x * 0.5 ? u_radii.w : u_radii.z);
    vec2 local = p - u_rect_size * 0.5;
    vec2 q = abs(local) - u_rect_size * 0.5 + radius;
    float shape_dist = min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - radius;
    float shape_aa = max(fwidth(shape_dist), 0.001);
    float shape = 1.0 - smoothstep(-shape_aa, shape_aa, shape_dist);
    float circle_dist = length(p - u_ripple_center) - u_ripple_radius;
    float circle_aa = max(fwidth(circle_dist), 0.001);
    float ripple = 1.0 - smoothstep(-circle_aa, circle_aa, circle_dist);
    float press_alpha = u_pressed * ripple;
    float alpha = shape * (u_hover + press_alpha * (1.0 - u_hover));
    if (alpha <= 0.0) discard;
    frag = vec4(u_color.rgb, alpha * u_color.a);
}
"""


class GLRenderer(Renderer):
    native_texture_scaling = True
    native_shape_overlay = True
    native_geometry = True
    native_texture_tint = True
    native_shadow = True
    native_shader = True
    native_state_layer = True
    # text/icons are rendered at 2x and downsampled in blit (matches the
    # software backend's supersampling); rects get SDF AA at device resolution
    _ssaa = 2

    def __init__(self, window, *, logical_size=None,
                 pixel_ratio: float = 1.0, anti_aliasing: bool = True,
                 vsync: bool = True):
        self._init_effect_stacks()
        self.window = window
        self.pixel_ratio = max(1.0, float(pixel_ratio))
        self.anti_aliasing = anti_aliasing
        self.vsync = vsync
        self._ssaa = 1 if not anti_aliasing or self.pixel_ratio >= 1.5 else 2
        self.scale = self._ssaa * self.pixel_ratio
        self.ctx = moderngl.create_context()
        library = Path(pygame.__file__).with_name("SDL2.dll")
        self._context_sdl = ctypes.CDLL(str(library) if library.exists() else pygame.base.__file__)
        self._context_sdl.SDL_GL_GetCurrentContext.restype = ctypes.c_void_p
        self._native_gl_context = self._context_sdl.SDL_GL_GetCurrentContext()
        self._context_sdl.SDL_GetWindowFromID.argtypes = [ctypes.c_uint32]
        self._context_sdl.SDL_GetWindowFromID.restype = ctypes.c_void_p
        self._native_sdl_window = self._context_sdl.SDL_GetWindowFromID(window.id)
        self._context_sdl.SDL_GL_MakeCurrent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self._context_sdl.SDL_GL_MakeCurrent.restype = ctypes.c_int
        self.ctx.enable(moderngl.BLEND)
        # the GL backbuffer follows the OS window automatically, but pygame's
        # get_surface() and moderngl's ctx.screen both cache the CREATION size —
        # never trust them; on_resize is the source of truth
        self._pixel_size = self._query_size()
        self._size = (tuple(logical_size) if logical_size is not None else
                      tuple(round(v / self.pixel_ratio)
                            for v in self._pixel_size))
        self._prog = self.ctx.program(vertex_shader=RECT_VS, fragment_shader=RECT_FS)
        self._prog_tex = self.ctx.program(vertex_shader=TEX_VS, fragment_shader=TEX_FS)
        self._prog_state = self.ctx.program(vertex_shader=STATE_VS, fragment_shader=STATE_FS)
        self._custom_programs = OrderedDict()
        self._shader_buffers = OrderedDict()
        self._buffer_programs = OrderedDict()
        self._custom_failures = OrderedDict()
        self._prog["u_size"].value = self._fb_size()
        self._prog_tex["u_size"].value = self._fb_size()
        self._prog_state["u_size"].value = self._fb_size()
        self._set_transform()
        self._prog_tex["u_tex"].value = 0
        self._rect_vertices = array("f")
        self._rect_vbo = self.ctx.buffer(reserve=65536)
        self._rect_vao = self.ctx.vertex_array(
            self._prog,
            [(self._rect_vbo, "2f 2f 2f 2f 4f 4f", "in_pos", "in_center",
              "in_half", "in_rb", "in_color", "in_border_color")])
        self._tex_vbo = self.ctx.buffer(reserve=192)
        self._tex_vao = self.ctx.vertex_array(
            self._prog_tex,
            [(self._tex_vbo, "2f 2f 4f", "in_pos", "in_uv", "in_color")])
        self._state_vbo = self.ctx.buffer(reserve=96)
        self._state_vao = self.ctx.vertex_array(
            self._prog_state,
            [(self._state_vbo, "2f 2f", "in_pos", "in_uv")])
        self._tex_cache: dict = {}  # surface digest -> texture
        self._immutable_tex_cache: OrderedDict = OrderedDict()
        self._clip_stack: list = []
        self._frame_color = None
        self._frame_target = None
        self._create_frame_target()
        self.vsync_active = _set_swap_interval(vsync)

    def activate(self):
        if self._context_sdl.SDL_GL_GetCurrentContext() != self._native_gl_context:
            if self._context_sdl.SDL_GL_MakeCurrent(self._native_sdl_window, self._native_gl_context) != 0:
                raise RuntimeError("Cannot activate the window's OpenGL context")

    def configure(self, *, anti_aliasing: bool, vsync: bool):
        changed = anti_aliasing != self.anti_aliasing
        self._flush_rects()
        if vsync != self.vsync:
            self.vsync_active = _set_swap_interval(vsync)
        super().configure(anti_aliasing=anti_aliasing, vsync=vsync)
        if changed:
            self._ssaa = (1 if not anti_aliasing or self.pixel_ratio >= 1.5 else 2)
            self.scale = self._ssaa * self.pixel_ratio
            self._create_frame_target()

    def _set_transform(self):
        a, b, c, d, tx, ty = self._transform_stack[-1]
        value = (a, b, 0.0, c, d, 0.0, tx, ty, 1.0)
        for program in (self._prog, self._prog_tex, self._prog_state):
            program['u_transform'].value = value

    def transform_push(self, matrix, *, bounds=None):
        previous = self._transform_stack[-1]
        super().transform_push(matrix, bounds=bounds)
        if self._transform_stack[-1] != previous:
            self._flush_rects()
            self._set_transform()

    def transform_pop(self):
        previous = self._transform_stack[-1]
        super().transform_pop()
        if self._transform_stack[-1] != previous:
            self._flush_rects()
            self._set_transform()

    def _query_size(self):
        try:
            return tuple(self.window.size)
        except Exception:
            return (0, 0)

    # -- helpers -----------------------------------------------------------
    def _fb_size(self):
        return (float(self._size[0]), float(self._size[1]))

    def _create_frame_target(self):
        if self._frame_target is not None:
            self._frame_target.release()
        if self._frame_color is not None:
            self._frame_color.release()
        w = max(1, int(self._pixel_size[0]) * self._ssaa)
        h = max(1, int(self._pixel_size[1]) * self._ssaa)
        self._frame_color = self.ctx.texture((w, h), 4)
        self._frame_color.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._frame_color.repeat_x = False
        self._frame_color.repeat_y = False
        self._frame_target = self.ctx.framebuffer(
            color_attachments=[self._frame_color])
        self._use_frame_target()

    def _use_frame_target(self):
        self._frame_target.use()
        self.ctx.viewport = (0, 0,
                             max(1, int(self._pixel_size[0]) * self._ssaa),
                             max(1, int(self._pixel_size[1]) * self._ssaa))
        self.ctx.scissor = self._clip_stack[-1] if self._clip_stack else None

    def _flush_rects(self):
        vertices = self._rect_vertices
        if not vertices:
            return
        data = vertices.tobytes()
        if len(data) > self._rect_vbo.size:
            self._rect_vbo.orphan(max(len(data), self._rect_vbo.size * 2))
        self._rect_vbo.write(data)
        self._rect_vao.render(moderngl.TRIANGLES, vertices=len(vertices) // 16)
        vertices.clear()

    def _draw_rect(self, corners, center, half, radius, border_w, color,
                   border_color, coverage=None):
        """corners: 6 (x, y) tuples (two triangles, any winding)."""
        r, g, b, a = self._effect_color(color)
        if border_color is not None:
            br, bg, bb, ba = self._effect_color(border_color)
        else:
            br = bg = bb = ba = 0.0
        color4 = (r / 255, g / 255, b / 255, a / 255)
        border4 = (br / 255, bg / 255, bb / 255, ba / 255)
        data = self._rect_vertices
        # Repeat common fields in C instead of converting 16 Python floats
        # for every triangle vertex in an animated rounded polygon.
        block = array('f', (0, 0, *center, *half, radius, border_w,
                            *color4, *border4)) * len(corners)
        for index, (px, py) in enumerate(corners):
            offset = index * 16
            block[offset], block[offset + 1] = px, py
            if coverage is not None:
                block[offset + 11] = color4[3] * coverage[index]
        data.extend(block)
        if len(data) >= 16 * 6 * 256:
            self._flush_rects()

    def _rect_call(self, x, y, w, h, color, radius=0.0, border_w=0.0,
                   border_color=(0, 0, 0, 0)):
        if w <= 0 or h <= 0:
            return
        x, y = self._translate(x, y)
        # Snap to the supersampled grid. This preserves stable edges while
        # allowing half-pixel motion instead of visibly jumping whole pixels.
        device_scale = self.scale
        x0 = round(x * device_scale) / device_scale
        y0 = round(y * device_scale) / device_scale
        x1 = round((x + w) * device_scale) / device_scale
        y1 = round((y + h) * device_scale) / device_scale
        w, h = x1 - x0, y1 - y0
        cx, cy = x0 + w / 2, y0 + h / 2
        hw, hh = w / 2, h / 2
        # SDF coverage extends half a device pixel outside the nominal shape.
        # Keep that fringe inside the rasterized geometry instead of clipping
        # it at the quad boundary.
        pad = 1.0 / device_scale if radius >= 0 else 0.0
        corners = [(x0 - pad, y0 - pad), (x1 + pad, y0 - pad),
                   (x1 + pad, y1 + pad), (x0 - pad, y0 - pad),
                   (x1 + pad, y1 + pad), (x0 - pad, y1 + pad)]
        self._draw_rect(corners, (cx, cy), (hw, hh), float(radius), float(border_w),
                        color, border_color)

    # -- Renderer API ---------------------------------------------------------
    def clear(self, color):
        self._flush_rects()
        # SDL may call glViewport with the native window size after a resize,
        # outside ModernGL's cached state. Rebind the supersampled target and
        # restore its actual viewport at the start of every new frame.
        self._use_frame_target()
        r, g, b, a = parse_color(color)
        self.ctx.clear(r / 255, g / 255, b / 255, a / 255)

    def fill_rect(self, x, y, w, h, color, radius=0):
        self._rect_call(x, y, w, h, color, radius=radius)

    def stroke_rect(self, x, y, w, h, color, width=1, radius=0):
        self._rect_call(x, y, w, h, (0, 0, 0, 0), radius=radius,
                        border_w=width, border_color=color)

    def line(self, x1, y1, x2, y2, color, width=1):
        if width <= 0:
            return
        if x1 != x2 and y1 != y2:
            points, coverage = stroke_triangles(
                ((x1, y1), (x2, y2)), width, 1 / self.scale)
            self._draw_geometry(points, coverage, color)
            return
        x, y = min(x1, x2), min(y1, y2)
        w = abs(x2 - x1) or width
        h = abs(y2 - y1) or width
        if x1 == x2:
            x, w = x1 - width / 2, width
        if y1 == y2:
            y, h = y1 - width / 2, width
        self._rect_call(x, y, w, h, color)

    def circle(self, x, y, radius, color, fill=True):
        if fill:
            self._rect_call(x - radius, y - radius,
                            radius * 2, radius * 2,
                            color, radius=radius)
        else:
            self._rect_call(x - radius, y - radius,
                            radius * 2, radius * 2,
                            (0, 0, 0, 0), radius=radius, border_w=max(1.0, radius / 8),
                            border_color=color)

    def arc(self, x, y, radius, start_angle, end_angle, color, width=1):
        points, coverage = arc_triangles(
            x, y, radius, start_angle, end_angle, width, 1 / self.scale)
        self._draw_geometry(points, coverage, color)

    def _draw_geometry(self, points, coverage, color):
        if not points:
            return
        tx, ty = self._translation_stack[-1]
        points = [(x + tx, y + ty) for x, y in points]
        self._draw_rect(points, (0, 0), (1, 1), -1, 0, color, None, coverage)

    def polygon(self, points, color, *, center):
        vertices, coverage = polygon_triangles(points, 1 / self.scale, center)
        self._draw_geometry(vertices, coverage, color)

    def polyline(self, points, color, width=1):
        points = list(points)
        vertices, coverage = stroke_triangles(points, width, 1 / self.scale)
        self._draw_geometry(vertices, coverage, color)
        if len(points) > 1 and width > 0:
            for x, y in (points[0], points[-1]):
                self.circle(x, y, width / 2, color)

    def _texture(self, surface):
        raw = pygame.image.tobytes(surface, "RGBA")
        digest = hashlib.blake2b(raw, digest_size=12).digest()
        tex = self._tex_cache.get(digest)
        if tex is None:
            tex = self.ctx.texture(surface.get_size(), 4, raw)
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            tex.repeat_x = False
            tex.repeat_y = False
            self._tex_cache[digest] = tex
            # ponytail: unbounded texture cache; LRU if long sessions leak
            if len(self._tex_cache) > 600:
                old = next(iter(self._tex_cache))
                self._tex_cache.pop(old).release()
        return tex, raw

    def _cached_texture(self, surface):
        key = id(surface)
        entry = self._immutable_tex_cache.get(key)
        if entry is not None and entry[0] is surface:
            self._immutable_tex_cache.move_to_end(key)
            return entry[1]
        raw = pygame.image.tobytes(surface, "RGBA")
        tex = self.ctx.texture(surface.get_size(), 4, raw)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = False
        tex.repeat_y = False
        self._immutable_tex_cache[key] = (surface, tex)
        if len(self._immutable_tex_cache) > 600:
            _, (_, old) = self._immutable_tex_cache.popitem(last=False)
            old.release()
        return tex

    def blit(self, surface, x, y, alpha=1.0):
        s = self.scale
        self.blit_scaled(surface, x, y,
                         surface.get_width() / s,
                         surface.get_height() / s, alpha)

    def blit_cached(self, surface, x, y, alpha=1.0):
        s = self.scale
        self.blit_cached_scaled(surface, x, y,
                                surface.get_width() / s,
                                surface.get_height() / s, alpha)

    def _draw_texture(self, tex, x, y, width, height, alpha=1.0, *,
                      framebuffer_texture=False, tint=(255, 255, 255, 255)):
        self._flush_rects()
        device_scale = self.scale
        x0 = round(x * device_scale) / device_scale
        y0 = round(y * device_scale) / device_scale
        x1 = x0 + round(width * device_scale) / device_scale
        y1 = y0 + round(height * device_scale) / device_scale
        # pygame byte row 0 maps to v=0 and is intentionally placed at the
        # quad top. A framebuffer texture uses OpenGL's bottom-up orientation,
        # so its V coordinates are reversed during the final resolve.
        top_v, bottom_v = ((1.0, 0.0) if framebuffer_texture
                           else (0.0, 1.0))
        verts = [(x0, y0, 0.0, top_v), (x1, y0, 1.0, top_v),
                 (x1, y1, 1.0, bottom_v), (x0, y0, 0.0, top_v),
                 (x1, y1, 1.0, bottom_v), (x0, y1, 0.0, bottom_v)]
        data = []
        tr, tg, tb, ta = (c / 255 for c in tint)
        for vx, vy, u, v in verts:
            data += [vx, vy, u, v, tr, tg, tb, ta * alpha]
        self._tex_vbo.write(struct.pack(f"{len(data)}f", *data))
        tex.use(0)
        self._tex_vao.render(moderngl.TRIANGLES)

    def blit_scaled(self, surface, x, y, width, height, alpha=1.0):
        if width <= 0 or height <= 0 or surface.get_width() == 0 or surface.get_height() == 0:
            return
        x, y = self._translate(x, y)
        alpha *= self.opacity
        tex, _ = self._texture(surface)
        self._draw_texture(tex, x, y, width, height, alpha)

    def blit_cached_scaled(self, surface, x, y, width, height, alpha=1.0):
        if width <= 0 or height <= 0 or surface.get_width() == 0 or surface.get_height() == 0:
            return
        x, y = self._translate(x, y)
        alpha *= self.opacity
        self._draw_texture(self._cached_texture(surface), x, y,
                           width, height, alpha)

    def blit_tinted_scaled(self, surface, x, y, width, height, color):
        if width <= 0 or height <= 0 or surface.get_width() == 0 or surface.get_height() == 0:
            return
        x, y = self._translate(x, y)
        self._draw_texture(self._cached_texture(surface), x, y, width, height,
                           self.opacity, tint=parse_color(color))

    def overlay_rect(self, x, y, w, h, color, radius=0):
        self._rect_call(x, y, w, h, color, radius=radius)  # blend handles alpha

    def state_layer(self, x, y, w, h, color, radii, hover, pressed,
                    ripple_x, ripple_y, ripple_radius):
        """Draw a clipped Material ripple without allocating a CPU bitmap."""
        if w <= 0 or h <= 0:
            return
        self._flush_rects()
        original_x, original_y = x, y
        x, y = self._translate(x, y)
        s = self.scale
        x0 = round(x * s) / s
        y0 = round(y * s) / s
        x1 = round((x + w) * s) / s
        y1 = round((y + h) * s) / s
        vertices = (
            x0, y0, 0.0, 0.0, x1, y0, 1.0, 0.0,
            x1, y1, 1.0, 1.0, x0, y0, 0.0, 0.0,
            x1, y1, 1.0, 1.0, x0, y1, 0.0, 1.0)
        self._state_vbo.write(struct.pack("24f", *vertices))
        r, g, b, a = self._effect_color(color)
        program = self._prog_state
        program["u_mode"].value = 0.0
        program["u_rect_size"].value = (x1 - x0, y1 - y0)
        program["u_radii"].value = tuple(float(v) for v in radii)
        program["u_ripple_center"].value = (
            ripple_x - original_x + x - x0,
            ripple_y - original_y + y - y0)
        program["u_ripple_radius"].value = float(ripple_radius)
        program["u_color"].value = (r / 255, g / 255, b / 255, a / 255)
        program["u_hover"].value = max(0.0, min(1.0, hover))
        program["u_pressed"].value = max(0.0, min(1.0, pressed))
        self._state_vao.render(moderngl.TRIANGLES)

    def _wave_quad(self, x, y, w, h, color, mode, wave, info):
        if w <= 0 or h <= 0:
            return
        self._flush_rects()
        x, y = self._translate(x, y)
        vertices = (x, y, 0, 0, x + w, y, 1, 0, x + w, y + h, 1, 1,
                    x, y, 0, 0, x + w, y + h, 1, 1, x, y + h, 0, 1)
        self._state_vbo.write(struct.pack('24f', *vertices))
        program = self._prog_state
        program['u_mode'].value = float(mode)
        program['u_rect_size'].value = (float(w), float(h))
        program['u_wave'].value = tuple(float(v) for v in wave)
        program['u_info'].value = tuple(float(v) for v in info)
        program['u_color'].value = tuple(v / 255 for v in self._effect_color(color))
        self._state_vao.render(moderngl.TRIANGLES)

    def wave_line(self, x, y, w, h, a, b, amplitude, wavelength, phase, color, width):
        self._wave_quad(x, y, w, h, color, 1, (a, b, amplitude, wavelength),
                        (phase, width, h / 2, 0))

    def wave_arc(self, x, y, w, h, radius, start, sweep, amplitude, waves,
                 phase, color, width):
        self._wave_quad(x, y, w, h, color, 2, (radius, start, sweep, amplitude),
                        (phase, width, waves, 0))

    def shadow(self, x, y, w, h, radii, elevation):
        ambient, key = 1 + elevation * .7, .5 + elevation * .8
        offset = elevation * .5
        pad = math.ceil(3 * max(ambient, key) + offset)
        self._wave_quad(x-pad, y-pad, w+2*pad, h+2*pad, (0, 0, 0, 255), 3,
                        radii, (ambient, key, offset, pad))

    def shader(self, x, y, w, h, effect, color, secondary_color,
               parameters, information):
        self._prog_state['u_secondary_color'].value = tuple(
            value / 255 for value in self._effect_color(secondary_color))
        self._wave_quad(x, y, w, h, color, 4 + effect, parameters, information)

    def custom_shader(self, x, y, w, h, body, layout, values, call,
                      elapsed, radius, color, secondary_color, *, buffer_pass=None):
        from .shader_source import fragment_source, ShaderCompilationError
        if w <= 0 or h <= 0:
            return
        key = (body, layout, call)
        if key in self._custom_failures:
            raise ShaderCompilationError(self._custom_failures[key])
        if key not in self._custom_programs:
            try:
                program = self.ctx.program(vertex_shader=STATE_VS,
                    fragment_shader=fragment_source(body, layout, call))
            except moderngl.Error as error:
                self._custom_failures[key] = str(error)
                if len(self._custom_failures)>32:
                    self._custom_failures.popitem(last=False)
                raise ShaderCompilationError(str(error)) from error
            vao = self.ctx.vertex_array(program,
                [(self._state_vbo, '2f 2f', 'in_pos', 'in_uv')], skip_errors=True)
            self._custom_programs[key] = (program, vao)
            if len(self._custom_programs)>32:
                _, (old_program, old_vao) = self._custom_programs.popitem(last=False)
                old_vao.release()
                old_program.release()
        program, vao = self._custom_programs[key]
        self._custom_programs.move_to_end(key)
        self._flush_rects()
        if buffer_pass is not None:
            self._render_shader_buffer(buffer_pass, layout, values, w, h, elapsed, color, secondary_color)
        x, y = self._translate(x, y)
        vertices = (x,y,0,0, x+w,y,1,0, x+w,y+h,1,1,
                    x,y,0,0, x+w,y+h,1,1, x,y+h,0,1)
        self._state_vbo.write(struct.pack('24f', *vertices))
        a,b,c,d,tx,ty = self._transform_stack[-1]
        builtins = dict(u_size=self._fb_size(), u_transform=(a,b,0,c,d,0,tx,ty,1),
                        u_resolution=(float(w),float(h)), u_time=elapsed,
                        u_border_radius=radius, u_opacity=self.opacity,
                        u_color=tuple(v/255 for v in parse_color(color)),
                        u_secondary_color=tuple(v/255 for v in parse_color(secondary_color)))
        for name, value in (*builtins.items(), *zip((name for name,_ in layout), values)):
            if name in program:
                program[name].value = value
        vao.render(moderngl.TRIANGLES)

    def _render_shader_buffer(self, buffer_pass, layout, values, w, h, elapsed, color, secondary):
        from .shader_source import buffer_source, ShaderCompilationError
        token, vertex, fragment, instances = buffer_pass
        key = (vertex, fragment, layout)
        failure_key = ('buffer', *key)
        if failure_key in self._custom_failures:
            raise ShaderCompilationError(self._custom_failures[failure_key])
        if key not in self._buffer_programs:
            try:
                program = self.ctx.program(vertex_shader=buffer_source(vertex, layout, vertex=True),
                                          fragment_shader=buffer_source(fragment, layout))
                vao = self.ctx.vertex_array(program, [])
            except moderngl.Error as error:
                self._custom_failures[failure_key] = str(error)
                if len(self._custom_failures) > 32:
                    self._custom_failures.popitem(last=False)
                raise ShaderCompilationError(str(error)) from error
            self._buffer_programs[key] = (program, vao)
            if len(self._buffer_programs) > 16:
                _, (old, old_vao) = self._buffer_programs.popitem(last=False)
                old_vao.release()
                old.release()
        program, vao = self._buffer_programs[key]
        self._buffer_programs.move_to_end(key)
        size = (max(1, round(w*self.scale)), max(1, round(h*self.scale)))
        cached = self._shader_buffers.get(token)
        if cached is not None and cached[0] != size:
            cached[2].release()
            cached[1].release()
            del self._shader_buffers[token]
            cached = None
        if cached is None:
            texture = self.ctx.texture(size, 4)
            texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            texture.repeat_x = texture.repeat_y = False
            target = self.ctx.framebuffer(color_attachments=[texture])
            cached = self._shader_buffers[token] = (size, texture, target)
        self._shader_buffers.move_to_end(token)
        if len(self._shader_buffers) > 16:
            _, (_, old_texture, old_target) = self._shader_buffers.popitem(last=False)
            old_target.release()
            old_texture.release()
        viewport, scissor = self.ctx.viewport, self.ctx.scissor
        try:
            cached[2].use()
            self.ctx.viewport = (0, 0, *size)
            self.ctx.scissor = None
            cached[2].clear(0, 0, 0, 0)
            self.ctx.blend_func = (moderngl.ONE, moderngl.ONE, moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
            builtins = dict(u_resolution=(float(w),float(h)), u_time=elapsed,
                            u_border_radius=0., u_opacity=1.,
                            u_color=tuple(v/255 for v in parse_color(color)),
                            u_secondary_color=tuple(v/255 for v in parse_color(secondary)))
            for name, value in (*builtins.items(), *zip((n for n,_ in layout), values)):
                if name in program:
                    program[name].value = value
            vao.render(moderngl.TRIANGLES, vertices=6, instances=instances)
        finally:
            self._use_frame_target()
            self.ctx.viewport, self.ctx.scissor = viewport, scissor
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        cached[1].use(location=0)

    # -- clip -------------------------------------------------------------------
    def clip_push(self, x, y, w, h):
        self._flush_rects()
        x, y = self._translate(x, y)
        x, y, w, h = self._transform_rect(x, y, w, h)
        _sw, sh = self._fb_size()
        device_scale = self.scale
        left, right = round(x * device_scale), round((x + w) * device_scale)
        bottom, top = round((sh - y - h) * device_scale), round((sh - y) * device_scale)
        rect = (left, bottom, max(0, right-left), max(0, top-bottom))
        if self._clip_stack:
            px0, py0, pw, ph = self._clip_stack[-1]
            ex0, ey0 = max(px0, rect[0]), max(py0, rect[1])
            ex1 = min(px0 + pw, rect[0] + rect[2])
            ey1 = min(py0 + ph, rect[1] + rect[3])
            rect = (ex0, ey0, max(0, ex1 - ex0), max(0, ey1 - ey0))
        self._clip_stack.append(rect)
        self.ctx.scissor = rect

    def clip_pop(self):
        self._flush_rects()
        if self._clip_stack:
            self._clip_stack.pop()
        self.ctx.scissor = self._clip_stack[-1] if self._clip_stack else None

    # -- present -------------------------------------------------------------
    def screenshot(self):
        """Current framebuffer contents (must run on the UI thread, pre-swap)."""
        self._flush_rects()
        w, h = int(self._pixel_size[0]), int(self._pixel_size[1])
        if w <= 0 or h <= 0:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        rw, rh = w * self._ssaa, h * self._ssaa
        data = self._frame_target.read(components=3, viewport=(0, 0, rw, rh))
        stride = rw * 3
        rows = [data[i * stride:(i + 1) * stride] for i in range(rh)]
        full = pygame.image.frombytes(b"".join(reversed(rows)), (rw, rh), "RGB")
        return pygame.transform.smoothscale(full, (w, h))

    def _resolve_to_window(self):
        self._flush_rects()
        self.ctx.screen.use()
        self.ctx.viewport = (
            0, 0, int(self._pixel_size[0]), int(self._pixel_size[1]))
        self.ctx.scissor = None
        # The frame target already contains the finished page. Its alpha can
        # be below 1 after translucent controls, so blending it over the
        # previous window backbuffer leaves trails from hidden controls and
        # old caret positions. The resolve must replace every window pixel.
        self.ctx.disable(moderngl.BLEND)
        try:
            self._draw_texture(self._frame_color, 0, 0,
                               self._size[0], self._size[1],
                               framebuffer_texture=True)
        finally:
            self.ctx.enable(moderngl.BLEND)

    def flip(self):
        self._resolve_to_window()
        if os.environ.get("SATURN_SHOT"):  # test hook: dump last frame to png
            pygame.image.save(self.screenshot(), os.environ["SATURN_SHOT"])
        self.window.flip()
        self._use_frame_target()

    def on_resize(self, width, height, *, pixel_size=None,
                  pixel_ratio: float | None = None):
        target_ratio = (max(1.0, float(pixel_ratio)) if pixel_ratio is not None
                        else self.pixel_ratio)
        target_size = (int(width), int(height))
        target_pixels = (tuple(int(v) for v in pixel_size)
                         if pixel_size is not None else self._query_size())
        if (target_ratio == self.pixel_ratio and target_size == self._size
                and target_pixels == self._pixel_size):
            return
        self._flush_rects()
        if pixel_ratio is not None:
            self.pixel_ratio = target_ratio
            self._ssaa = (1 if not self.anti_aliasing or self.pixel_ratio >= 1.5
                          else 2)
            self.scale = self._ssaa * self.pixel_ratio
        self._size = target_size
        self._pixel_size = target_pixels
        self._prog["u_size"].value = (float(width), float(height))
        self._prog_tex["u_size"].value = (float(width), float(height))
        self._prog_state["u_size"].value = (float(width), float(height))
        self._create_frame_target()

    def close(self):
        for _, texture, target in self._shader_buffers.values():
            target.release()
            texture.release()
        self._shader_buffers.clear()
        for program, vao in self._buffer_programs.values():
            vao.release()
            program.release()
        self._buffer_programs.clear()
        self._flush_rects()
        for program, vao in self._custom_programs.values():
            vao.release()
            program.release()
        self._custom_programs.clear()
        for resource in (self._rect_vao, self._tex_vao, self._state_vao,
                         self._rect_vbo, self._tex_vbo, self._state_vbo,
                         self._frame_target, self._frame_color,
                         self._prog, self._prog_tex, self._prog_state):
            resource.release()
        for tex in self._tex_cache.values():
            tex.release()
        self._tex_cache.clear()
        for _, tex in self._immutable_tex_cache.values():
            tex.release()
        self._immutable_tex_cache.clear()
