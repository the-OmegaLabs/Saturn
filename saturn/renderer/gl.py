"""OpenGL renderer (moderngl): SDF rounded rects + textured quads.

Draw calls target a supersampled framebuffer and resolve into the window;
blending is standard alpha. Clip = scissor stack. Coordinates arrive in
logical px with origin top-left and are flipped on the GPU side.
"""
from __future__ import annotations

import hashlib
import math
import os
import struct
from array import array
from collections import OrderedDict

import pygame
import moderngl

from ..colors import parse_color
from .base import Renderer

RECT_VS = """
#version 330
in vec2 in_pos;          // px, origin top-left
in vec2 in_center;       // rect center px
in vec2 in_half;         // half size px
in vec2 in_rb;           // radius, border width (radius < 0 -> no SDF)
in vec4 in_color;
in vec4 in_border_color;
uniform vec2 u_size;
out vec2 v_local;
flat out vec2 v_half;
flat out vec2 v_rb;
flat out vec4 v_color;
flat out vec4 v_border_color;
void main() {
    vec2 out_pos = vec2(in_pos.x, u_size.y - in_pos.y);
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
flat in vec4 v_color;
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
out vec2 v_uv;
out vec4 v_color;
void main() {
    vec2 out_pos = vec2(in_pos.x, u_size.y - in_pos.y);
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
out vec2 v_uv;
void main() {
    vec2 out_pos = vec2(in_pos.x, u_size.y - in_pos.y);
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
out vec4 frag;
void main() {
    vec2 p = v_uv * u_rect_size;
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
    native_state_layer = True
    # text/icons are rendered at 2x and downsampled in blit (matches the
    # software backend's supersampling); rects get SDF AA at device resolution
    _ssaa = 2

    def __init__(self, window, *, logical_size=None,
                 pixel_ratio: float = 1.0):
        self._init_effect_stacks()
        self.window = window
        self.pixel_ratio = max(1.0, float(pixel_ratio))
        self._ssaa = 1 if self.pixel_ratio >= 1.5 else 2
        self.scale = self._ssaa * self.pixel_ratio
        self.ctx = moderngl.create_context()
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
        self._prog["u_size"].value = self._fb_size()
        self._prog_tex["u_size"].value = self._fb_size()
        self._prog_state["u_size"].value = self._fb_size()
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
                   border_color):
        """corners: 6 (x, y) tuples (two triangles, any winding)."""
        r, g, b, a = self._effect_color(color)
        if border_color is not None:
            br, bg, bb, ba = self._effect_color(border_color)
        else:
            br = bg = bb = ba = 0.0
        color4 = (r / 255, g / 255, b / 255, a / 255)
        border4 = (br / 255, bg / 255, bb / 255, ba / 255)
        data = self._rect_vertices
        for (px, py) in corners:
            data.extend((px, py, *center, *half, radius, border_w,
                         *color4, *border4))
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
        # axis-aligned exact; diagonal = bounding quad (ponytail: tessellate when needed)
        x1, y1 = self._translate(x1, y1)
        x2, y2 = self._translate(x2, y2)
        # _rect_call also applies the current translation, so remove it here.
        tx, ty = self._translation_stack[-1]
        x1, y1, x2, y2 = x1 - tx, y1 - ty, x2 - tx, y2 - ty
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
        x, y = self._translate(x, y)
        sweep = end_angle - start_angle
        if radius <= 0 or width <= 0 or sweep == 0:
            return
        segments = max(8, int(abs(sweep) * radius / 3))
        inner = max(0.0, radius - width)
        corners = []
        for index in range(segments):
            a0 = start_angle + sweep * index / segments
            a1 = start_angle + sweep * (index + 1) / segments
            outer0 = (x + math.cos(a0) * radius,
                      y + math.sin(a0) * radius)
            outer1 = (x + math.cos(a1) * radius,
                      y + math.sin(a1) * radius)
            inner0 = (x + math.cos(a0) * inner,
                      y + math.sin(a0) * inner)
            inner1 = (x + math.cos(a1) * inner,
                      y + math.sin(a1) * inner)
            corners.extend((outer0, outer1, inner1,
                            outer0, inner1, inner0))
        self._draw_rect(corners, (x, y), (radius, radius), -1.0, 0.0,
                        color, None)

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
                      framebuffer_texture=False):
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
        for vx, vy, u, v in verts:
            data += [vx, vy, u, v, 1.0, 1.0, 1.0, alpha]
        self._tex_vbo.write(struct.pack(f"{len(data)}f", *data))
        tex.use(0)
        self._tex_vao.render(moderngl.TRIANGLES)

    def blit_scaled(self, surface, x, y, width, height, alpha=1.0):
        x, y = self._translate(x, y)
        alpha *= self.opacity
        tex, _ = self._texture(surface)
        self._draw_texture(tex, x, y, width, height, alpha)

    def blit_cached_scaled(self, surface, x, y, width, height, alpha=1.0):
        x, y = self._translate(x, y)
        alpha *= self.opacity
        self._draw_texture(self._cached_texture(surface), x, y,
                           width, height, alpha)

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

    # -- clip -------------------------------------------------------------------
    def clip_push(self, x, y, w, h):
        self._flush_rects()
        x, y = self._translate(x, y)
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
            self._ssaa = 1 if self.pixel_ratio >= 1.5 else 2
            self.scale = self._ssaa * self.pixel_ratio
        self._size = target_size
        self._pixel_size = target_pixels
        self._prog["u_size"].value = (float(width), float(height))
        self._prog_tex["u_size"].value = (float(width), float(height))
        self._prog_state["u_size"].value = (float(width), float(height))
        self._create_frame_target()

    def close(self):
        self._flush_rects()
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
