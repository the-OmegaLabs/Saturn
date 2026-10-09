"""Layout containers: Container, Row, Column, Stack, Divider.

Layout protocol (two passes, absolute rects):
  _intrinsic(max_w, max_h, scale) -> (w, h)   desired size under constraints
  _place(x, y, w, h, scale)                    final box; sets _rect, recurses
Draw pass: _draw_all walks the tree and renders at the absolute rects.

Row/Column arrange children using flex layout: alignment (MainAxisAlignment),
cross alignment (CrossAxisAlignment), spacing, tight, expand on children.
Container adds padding/margin/bgcolor/border/border_radius/alignment.
Stack children position via their own left/top/right/bottom.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Unpack

import enum
import math
import sys
import time

from .. import colors
from ..animation import ease
from ..control import Control, ControlOptions
from ..types import (Alignment, AnimationCurve, CrossAxisAlignment,
                     MainAxisAlignment, as_border_radius, as_padding)
from ._material import (draw_state_layer, init_state_layer, press,
                        release, set_hover, tick_state_layer)
from ._compat import axis_distribution, value, reject_options


def _margins(c):
    m = as_padding(c.margin)
    return m.left, m.top, m.right, m.bottom


class _Multi(Control):
    """Shared flex plumbing for Row/Column."""

    vertical = False  # Row

    def __init__(self, *items, controls=None,
                 alignment=MainAxisAlignment.START,
                 vertical_alignment=None, horizontal_alignment=None,
                 spacing: float = 10, tight: bool = False, wrap=False,
                 run_spacing=10, run_alignment=MainAxisAlignment.START,
                 intrinsic_height=False, intrinsic_width=False,
                 scroll=None, auto_scroll=False, auto_scroll_animation=None,
                 scroll_interval=10, on_scroll=None, **base: Unpack[ControlOptions]):
        reject_options(type(self).__name__,auto_scroll_animation=auto_scroll_animation)
        if controls is not None:
            if items:
                raise TypeError("controls cannot be combined with positional children")
            items = tuple(controls)
        elif len(items) == 1 and isinstance(items[0], list):
            items = tuple(items[0])  # legacy Saturn shorthand
        super().__init__(**base)
        self.controls = list(items)
        self.alignment = alignment
        self.vertical_alignment = vertical_alignment or (
            CrossAxisAlignment.START if self.vertical
            else CrossAxisAlignment.CENTER)
        self.horizontal_alignment = horizontal_alignment or CrossAxisAlignment.START
        self.spacing = spacing
        self.tight = tight
        self.wrap = bool(wrap)
        self.run_spacing = run_spacing
        self.run_alignment = run_alignment
        self.intrinsic_height = bool(intrinsic_height)
        self.intrinsic_width = bool(intrinsic_width)
        self.scroll = scroll
        self.auto_scroll = auto_scroll
        self.auto_scroll_animation = auto_scroll_animation
        self.scroll_interval = scroll_interval
        self.on_scroll = on_scroll
        self._scroll_view = None
        if self.wrap and value(scroll) not in (None, "none"):
            raise ValueError("wrap and scrolling cannot be combined")

    def _children(self):
        if self._scroll_view is not None and value(self.scroll) not in (None,"none"):
            return [self._scroll_view]
        return self.controls

    def _visible(self):
        items = [c for c in self.controls if c.visible]
        return list(reversed(items)) if not self.vertical and self._rtl else items

    @staticmethod
    def _expand_of(c) -> float:
        e = c.expand
        if e is True:
            return 1.0
        return float(e) if isinstance(e, (int, float)) and e else 0.0

    # -- measuring -----------------------------------------------------------
    def _intrinsic(self, max_w, max_h, scale):
        if self.wrap:
            runs = self._wrap_runs(max_h if self.vertical else max_w, max_w, scale)
            main = max((sum(s[1] for s in run) + self.spacing * (len(run)-1)
                        for run in runs), default=0)
            cross = sum(max((s[2] for s in run), default=0) for run in runs)
            cross += self.run_spacing * max(0, len(runs)-1)
            w, h = (cross, main) if self.vertical else (main, cross)
            return self._width if self._width is not None else w, self._height if self._height is not None else h
        kids = self._visible()
        footprints = [self._footprint(k, max_w, scale) for k in kids]
        main = sum(f[0 if not self.vertical else 1] for f in footprints)
        main += self.spacing * max(0, len(kids) - 1)
        cross = max((f[1 if not self.vertical else 0] for f in footprints),
                    default=0.0)
        if self.vertical:
            w = self._width if self._width is not None else cross
            h = self._height if self._height is not None else (
                main if self.tight or max_h is None else max_h)
        else:
            w = self._width if self._width is not None else (
                main if self.tight or max_w is None else max_w)
            h = self._height if self._height is not None else cross
        return w, h

    def _footprint(self, k, max_w, scale, max_h=None):
        """Child intrinsic size + its margin (margin sits outside the box)."""
        ml, mt, mr, mb = _margins(k)
        w, h = k._intrinsic(
            (max_w - ml - mr) if max_w is not None else None,
            (max_h - mt - mb) if max_h is not None else None, scale)
        return w + ml + mr, h + mt + mb

    # -- placing -----------------------------------------------------------
    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        if value(self.scroll) not in (None, "none"):
            # Reuse the existing ListView scrollbar, wheel routing and culling.
            from .scrolling import ListView
            if self._scroll_view is None:
                self._scroll_view = ListView()
            view = self._scroll_view
            view.controls = self.controls
            view.horizontal = not self.vertical
            view.spacing = self.spacing
            view.scroll = self.scroll
            view.auto_scroll = self.auto_scroll
            view.on_scroll = self._forward_scroll
            view.scroll_interval = self.scroll_interval
            view.page, view.parent = self.page, self
            if self.page is not None:
                for child in self.controls:
                    if child.parent is not view:
                        child._attach(self.page,view)
            view._place(x, y, w, h, scale)
            return
        if self.wrap:
            self._place_wrapped(x, y, w, h, scale)
            return
        kids = self._visible()
        if not kids:
            return
        # Flutter Flex measures children with an UNBOUNDED main axis (a nested
        # Row sizes to content, so SPACE_BETWEEN keeps its free space) and a
        # bounded cross axis (aligned children may fill it).
        sizes = [self._footprint(k,
                                 None if not self.vertical else w,
                                 scale,
                                 h if not self.vertical else None)
                 for k in kids]
        main_sizes = [s[0] if not self.vertical else s[1] for s in sizes]
        box_main = w if not self.vertical else h
        flex = [self._expand_of(k) for k in kids]
        if sum(flex):
            # Flutter Flex allocates the remaining main axis after non-flex
            # children. Intrinsic flex sizes must not bias proportional slots.
            fixed = sum(size for size,weight in zip(main_sizes,flex) if not weight)
            available = max(0,box_main-fixed-self.spacing*(len(kids)-1))
            share = available/sum(flex)
            for i, k in enumerate(kids):
                if flex[i]:
                    slot = share*flex[i]
                    if k.expand_loose:
                        ml,mt,mr,mb = _margins(k)
                        cw,ch = k._intrinsic(max(0,w-ml-mr) if self.vertical else max(0,slot-ml-mr),
                                             max(0,slot-mt-mb) if self.vertical else max(0,h-mt-mb),scale)
                        sizes[i] = cw+ml+mr,ch+mt+mb
                        main_sizes[i] = min(slot,sizes[i][1 if self.vertical else 0])
                    else:
                        main_sizes[i] = slot
        used = sum(main_sizes)+self.spacing*(len(kids)-1)
        free = box_main-used

        alignment = self.alignment
        if not self.vertical and self._rtl and value(alignment) in ("start","end"):
            alignment = "end" if value(alignment) == "start" else "start"
        pos, gap = axis_distribution(alignment, free, len(kids), self.spacing)

        for i, k in enumerate(kids):
            ml, mt, mr, mb = _margins(k)
            fw, fh = sizes[i]
            if flex[i]:
                if self.vertical:
                    fh = main_sizes[i]
                else:
                    fw = main_sizes[i]
            # Flutter's constrained cross axis: a fixed child larger than the
            # flex box is clamped to it (Container height=35 inside a 25px
            # Row renders 25px tall), so children never overflow the line.
            if not self.vertical:
                if h is not None and fh > h:
                    fh = h
            elif w is not None and fw > w:
                fw = w
            # margin sits outside the child's box
            cw, ch = fw - ml - mr, fh - mt - mb
            # cross-axis STRETCH fills the inner cross size (unless fixed)
            if not self.vertical:
                if value(self.vertical_alignment) == "stretch" and k._height is None:
                    ch = h - mt - mb
            elif value(self.horizontal_alignment) == "stretch" and k._width is None:
                cw = w - ml - mr
            if self.vertical:
                cx = self._cross_pos(k, cw, w, scale)
                k._place(x + cx + ml, y + pos + mt, cw, ch, scale)
            else:
                cy = self._cross_pos(k, ch, h, scale)
                k._place(x + pos + ml, y + cy + mt, cw, ch, scale)
            pos += main_sizes[i] + gap

    def _cross_pos(self, k, child_cross, inner_cross, scale) -> float:
        a = self.vertical_alignment if not self.vertical else self.horizontal_alignment
        if self.vertical and self._rtl and value(a) in ("start","end"):
            a = "end" if value(a) == "start" else "start"
        if value(a) == "end":
            return inner_cross - child_cross
        if value(a) == "center":
            return (inner_cross - child_cross) / 2
        return 0.0  # START / BASELINE / STRETCH

    def _draw(self, r, x, y):
        pass  # children render via _draw_all

    def _wrap_runs(self, available, max_w, scale):
        runs, run, used = [], [], 0
        for child in self._visible():
            w, h = self._footprint(child, max_w, scale)
            main, cross = (h, w) if self.vertical else (w, h)
            if run and available is not None and used + self.spacing + main > available:
                runs.append(run)
                run, used = [], 0
            used += main + (self.spacing if run else 0)
            run.append((child, main, cross))
        if run:
            runs.append(run)
        return runs

    def _place_wrapped(self, x, y, w, h, scale):
        box_main, box_cross = (h, w) if self.vertical else (w, h)
        runs = self._wrap_runs(box_main, w, scale)
        cross_sizes = [max(entry[2] for entry in run) for run in runs]
        cross_free = box_cross - sum(cross_sizes) - self.run_spacing * max(0, len(runs)-1)
        cross_pos, cross_gap = axis_distribution(self.run_alignment, cross_free, len(runs), self.run_spacing)
        for run, cross in zip(runs, cross_sizes):
            used = sum(entry[1] for entry in run) + self.spacing * (len(run)-1)
            pos, gap = axis_distribution(self.alignment, box_main-used, len(run), self.spacing)
            for child, main, child_cross in run:
                ml, mt, mr, mb = _margins(child)
                offset = self._cross_pos(child, child_cross, cross, scale)
                if self.vertical:
                    child._place(x+cross_pos+offset+ml, y+pos+mt,
                                 child_cross-ml-mr, main-mt-mb, scale)
                else:
                    child._place(x+pos+ml, y+cross_pos+offset+mt,
                                 main-ml-mr, child_cross-mt-mb, scale)
                pos += main+gap
            cross_pos += cross+cross_gap

    def _draw_all(self, r, ox=0, oy=0):
        if self._scroll_view is not None and value(self.scroll) not in (None, "none"):
            if self.visible:
                self._effects_begin(r, ox, oy)
                try:
                    self._scroll_view._draw_all(r, ox, oy)
                finally:
                    self._effects_end(r)
            return
        super()._draw_all(r, ox, oy)

    def _find_scrollable(self, x, y):
        if self._scroll_view is not None and value(self.scroll) not in (None, "none"):
            x,y = self._hit_point(x,y)
            if not self.visible or self.disabled:
                return None
            return self._scroll_view._find_scrollable(x, y)
        return super()._find_scrollable(x, y)

    def _hit_test(self, x, y):
        if self._scroll_view is not None and value(self.scroll) not in (None, "none"):
            x,y = self._hit_point(x,y)
            if not self.visible or self.disabled:
                return None
            return self._scroll_view._hit_test(x, y)
        return super()._hit_test(x, y)

    def _hit_test_hover(self, x, y):
        if self._scroll_view is not None and value(self.scroll) not in (None, "none"):
            x,y = self._hit_point(x,y)
            if not self.visible or self.disabled:
                return None
            return self._scroll_view._hit_test_hover(x, y)
        return super()._hit_test_hover(x, y)

    def scroll_to(self, offset=0, delta=None, **options):
        if self._scroll_view is None:
            raise RuntimeError("scrolling must be enabled and laid out first")
        return self._scroll_view.scroll_to(offset, delta, **options)

    def _forward_scroll(self,event):
        from ..event import normalize_handlers,_invoke
        event.control = self
        for handler in normalize_handlers(self.on_scroll):
            self.page._app.call(_invoke,handler,event)

    __unsupported_parameters__ = {"auto_scroll_animation"}


class Row(_Multi):
    vertical = False


class Column(_Multi):
    vertical = True


def _draw_shadow(r, x, y, w, h, sh, radius):
    """Box shadow as stacked translucent fills (no blur primitive); goes
    through fill_rect so every renderer composites it identically."""
    blur = max(0.0, float(sh.blur_radius))
    spread = float(sh.spread_radius or 0.0)
    off = sh.offset
    c = colors.parse_color(sh.color)
    if c[3] <= 0 or (blur <= 0 and spread <= 0 and not off.x and not off.y):
        return
    steps = 4
    for j in range(steps, 0, -1):          # outermost first
        grow = spread + blur * j / steps
        r.fill_rect(x - grow + off.x, y - grow + off.y,
                    w + 2 * grow, h + 2 * grow,
                    (c[0], c[1], c[2], round(c[3] / (j + 1))),
                    radius=radius + grow)


class Container(Control):
    def __init__(self, content=None, *, padding=None, bgcolor=None,
                 border=None, border_radius=None, alignment=None,
                 gradient=None, shadow=None, ink=False,
                 animate=None, on_click=None, on_hover=None,
                 on_long_press=None, on_tap_down=None, ink_color=None,
                 clip_behavior=None, shape="rectangle", url=None,
                 ignore_interactions=False, blend_mode=None, image=None,
                 blur=None, theme=None, dark_theme=None, theme_mode=None,
                 color_filter=None, foreground_decoration=None, **base: Unpack[ControlOptions]):
        reject_options("Container", blend_mode=blend_mode, image=image, blur=blur,
                       theme=theme, dark_theme=dark_theme, theme_mode=theme_mode,
                       color_filter=color_filter, foreground_decoration=foreground_decoration)
        super().__init__(**base)
        self.content = content
        self.padding = as_padding(padding)
        self.bgcolor = bgcolor
        self.border = border
        self.border_radius = border_radius
        self.alignment = alignment
        self.gradient = gradient
        self.shadow = shadow
        self.ink = ink
        self.animate = animate
        self.on_click = on_click
        self.on_hover = on_hover
        self.on_long_press = on_long_press
        self.on_tap_down = on_tap_down
        self.ink_color = ink_color
        self.clip_behavior = clip_behavior
        self.shape = shape
        self.url = url
        self.ignore_interactions = bool(ignore_interactions)
        self._hovered = False
        self._pressed = False
        init_state_layer(self)

    def _animation_groups(self):
        groups = super()._animation_groups()
        groups["container"] = (
            "animate",
            ("padding", "alignment", "bgcolor", "border", "border_radius", "shadow"),
        )
        return groups

    def _set_hover(self, on: bool):
        if self.ink:
            set_hover(self, on)
        else:
            self._hovered = on
        self.repaint()
        from ..event import fire
        fire(self, "hover", "true" if on else "false")

    def _hit_test_hover(self, x, y):
        """Ink containers have a visual hover state even without a handler."""
        x,y = self._hit_point(x,y)
        if not self.visible or self.disabled or self.ignore_interactions:
            return None
        for child in reversed(self._children()):
            hit = child._hit_test_hover(x, y)
            if hit is not None:
                return hit
        if ((self.ink or self.on_hover or self.tooltip)
                and self._contains(x, y)):
            return self
        return None

    def _pressed_hook(self, x, y):
        import time
        self._long_press_at = time.perf_counter()+.5 if self.on_long_press else None
        self._consume_click = False
        if self.on_tap_down:
            from ..event import fire, TapEvent
            fire(self, "tap_down", TapEvent("mouse", (x-self._rect[0], y-self._rect[1]), (x,y)))
        if not self.ink:
            return
        press(self, x, y)

    def _released_hook(self, _x, _y):
        self._long_press_at = None
        if not self.ink:
            return
        release(self)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now) if self.ink else False
        deadline = getattr(self,"_long_press_at",None)
        if deadline is not None and self._pressed:
            if now >= deadline:
                self._long_press_at = None
                self._consume_click = True
                from ..event import fire
                fire(self,"long_press")
            else:
                waiting = True
        return super()._tick_animations(now) or waiting

    def _children(self):
        return [self.content] if self.content is not None else []

    def _intrinsic(self, max_w, max_h, scale):
        state = object.__getattribute__(self, "__dict__")
        overrides = state.get("_animation_overrides")
        if overrides:
            state = state | overrides
        padding = as_padding(state["padding"])
        pad_w = padding.left + padding.right
        pad_h = padding.top + padding.bottom
        content = state["content"]
        if content is not None:
            cw, ch = content._intrinsic(
                max(0.0, max_w - pad_w) if max_w is not None else None,
                max(0.0, max_h - pad_h) if max_h is not None else None,
                scale)
        else:
            cw = ch = 0.0
        w = state["_width"] if state["_width"] is not None else cw + pad_w
        h = state["_height"] if state["_height"] is not None else ch + pad_h
        # Flutter Container rules: with an alignment and no explicit size the
        # box fills the bounded constraints instead of wrapping its content,
        # and a childless Container fills the bounded constraints as well.
        if state["alignment"] is not None or content is None:
            if state["_width"] is None and max_w is not None:
                w = max_w
            if state["_height"] is None and max_h is not None:
                h = max_h
        # Parent constraints limit the child's requested size. A 460px card
        # placed in a 330px page shrinks to the available width.
        if max_w is not None:
            w = min(w, max_w)
        if max_h is not None:
            h = min(h, max_h)
        return w, h

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        if self.content is None:
            return
        m = as_padding(self.margin)
        x, y = x + m.left, y + m.top
        w, h = w - m.left - m.right, h - m.top - m.bottom
        padding = as_padding(self.padding)
        px, py = x + padding.left, y + padding.top
        pw, ph = w - padding.left - padding.right, \
            h - padding.top - padding.bottom
        if self.alignment is not None:
            cw, ch = self.content._intrinsic(pw, ph, scale)
            ax = (pw - cw) * (self.alignment.x + 1) / 2
            ay = (ph - ch) * (self.alignment.y + 1) / 2
            self.content._place(px + ax, py + ay, cw, ch, scale)
        else:
            self.content._place(px, py, pw, ph, scale)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        if self.shadow is not None:
            shadows = self.shadow if isinstance(self.shadow, list) else [self.shadow]
            for sh in shadows:
                _draw_shadow(r, x, y, w, h, sh, self._radius())
        if self.bgcolor is not None:
            r.fill_rect(x, y, w, h, colors.parse_color(self.bgcolor),
                        radius=self._radius())
        if self.gradient is not None:
            self._draw_gradient(r, x, y, w, h)
        if self.border is not None and self.border.left.color is not None:
            r.stroke_rect(x, y, w, h, colors.parse_color(self.border.left.color),
                          width=self.border.left.width, radius=self._radius())
        if self.ink:
            draw_state_layer(self, r, (x, y, w, h),
                             self.ink_color or colors.Colors.ON_SURFACE, self._radius())
        if self._clip_children:
            r.clip_push(x, y, w, h)

    def _draw_all(self, r, ox: float = 0.0, oy: float = 0.0):
        if not self.visible:
            return
        self._effects_begin(r, ox, oy)
        try:
            self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
            if self.content is not None:
                self.content._draw_all(r, ox, oy)
            if self._clip_children:
                r.clip_pop()
        finally:
            self._effects_end(r)

    def _radius(self):
        if value(self.shape) == "circle":
            return min(self._rect[2:]) / 2
        return as_border_radius(self.border_radius).top_left

    @property
    def _clip_children(self):
        return (bool(self.border_radius) if self.clip_behavior is None else
                value(self.clip_behavior) != "none")

    def _hit_test(self, x, y):
        if self.ignore_interactions:
            return None
        return super()._hit_test(x, y)

    def _draw_gradient(self, r, x, y, w, h):
        # Static decoration cache: gradients are rasterized only when their
        # size or stops change, then share the ordinary GPU texture path.
        import math
        import pygame
        from bisect import bisect_right
        from ..painting import corners, shape_mask
        g = self.gradient
        begin, end = getattr(g, "begin", None), getattr(g, "end", None)
        center, radius = getattr(g, "center", None), getattr(g, "radius", None)
        if begin is None or end is None:
            if center is None or radius is None:
                raise NotImplementedError(
                    "only linear and radial gradients are supported")
        rgba = tuple(colors.parse_color(c) for c in g.colors)
        if len(rgba) < 2:
            raise ValueError("a gradient requires at least two colors")
        stops = tuple(g.stops) if g.stops else tuple(i/(len(rgba)-1) for i in range(len(rgba)))
        if len(stops) != len(rgba) or list(stops) != sorted(stops):
            raise ValueError("gradient stops must match colors and increase")
        pw, ph = max(1, round(w*r.scale)), max(1, round(h*r.scale))
        if radius is not None:  # radial
            focal = getattr(g, "focal", None)
            if focal is not None and (focal.x != center.x or focal.y != center.y):
                raise NotImplementedError(
                    "an off-center focal point is not supported for radial gradients")
            cx, cy = (center.x+1)*pw/2, (center.y+1)*ph/2
            span = math.hypot(pw, ph)/2
            rp = max(1.0, radius*span)
            fp = max(0.0, getattr(g, "focal_radius", 0.0)*span)
            key = ("radial", pw, ph, rgba, stops, cx, cy, rp, fp, self._radius())
            def t_at(px, py):
                return (math.hypot(px-cx, py-cy)-fp)/(rp-fp)
        else:
            sx, sy = (begin.x+1)*pw/2, (begin.y+1)*ph/2
            dx, dy = (end.x-begin.x)*pw/2, (end.y-begin.y)*ph/2
            denom = dx*dx+dy*dy or 1
            key = (pw, ph, rgba, stops, begin.x, begin.y, end.x, end.y, self._radius())
            def t_at(px, py):
                return ((px-sx)*dx+(py-sy)*dy)/denom
        if getattr(self, "_gradient_key", None) != key:
            surface = pygame.Surface((pw, ph), pygame.SRCALPHA)
            # A smooth gradient has no high-frequency detail. Rasterize its
            # small color field once and upscale, without an extra dependency.
            gw,gh = min(pw,128),min(ph,128)
            field = pygame.Surface((gw,gh),pygame.SRCALPHA)
            for gy in range(gh):
                for gx in range(gw):
                    t = max(0,min(1,t_at(gx*pw/gw, gy*ph/gh)))
                    i = max(0,min(len(stops)-2,bisect_right(stops,t)-1))
                    fraction = max(0,min(1,(t-stops[i])/(stops[i+1]-stops[i] or 1)))
                    field.set_at((gx,gy),tuple(round(a+(b-a)*fraction) for a,b in zip(rgba[i],rgba[i+1])))
            surface = pygame.transform.smoothscale(field,(pw,ph))
            if self._radius():
                surface.blit(shape_mask(pw, ph, corners(self._radius(), r.scale, pw, ph)), (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            self._gradient_surface, self._gradient_key = surface, key
        r.blit_cached(self._gradient_surface, x, y)

    __unsupported_parameters__ = {"blend_mode", "image", "blur", "theme", "dark_theme",
                                  "theme_mode", "color_filter", "foreground_decoration"}


class Stack(Control):
    def __init__(self, *items, controls=None, clip_behavior="hardEdge",
                 alignment=None, fit="loose", **base: Unpack[ControlOptions]):
        if controls is not None:
            if items:
                raise TypeError("controls cannot be combined with positional children")
            items = tuple(controls)
        elif len(items) == 1 and isinstance(items[0], list):
            items = tuple(items[0])
        super().__init__(**base)
        self.controls = list(items)
        self.clip_behavior = clip_behavior
        self.alignment = alignment
        self.fit = fit

    def _children(self):
        return self.controls

    def _intrinsic(self, max_w, max_h, scale):
        ws, hs = 0.0, 0.0
        positioned = 0
        visible = 0
        for k in self.controls:
            if not k.visible:
                continue
            visible += 1
            if k.left is not None or k.top is not None \
                    or k.right is not None or k.bottom is not None:
                positioned += 1
            w, h = k._intrinsic(max_w, max_h, scale)
            ws, hs = max(ws, w), max(hs, h)
        if positioned and positioned == visible:
            # Flutter: a Stack with only positioned children sizes itself to
            # the biggest size the constraints allow; unbounded axes fall
            # back to the largest child.
            w = self._width if self._width is not None else (
                max_w if max_w is not None else ws)
            h = self._height if self._height is not None else (
                max_h if max_h is not None else hs)
            return w, h
        w = self._width if self._width is not None else ws
        h = self._height if self._height is not None else hs
        # Layout rule: the Stack itself fits its constraints; oversized
        # children still overflow at draw time
        if max_w is not None:
            w = min(w, max_w)
        if max_h is not None:
            h = min(h, max_h)
        return w, h

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        for k in self.controls:
            if not k.visible:
                continue
            if k.expand and k.left is None and k.top is None \
                    and k.right is None and k.bottom is None:
                # an expand child of a Stack stretches to the stack
                k._place(x, y, w, h, scale)
                continue
            ml, mt, mr, mb = _margins(k)
            kw, kh = k._intrinsic(w, h, scale)
            if value(self.fit) == "expand" and k.left is None and k.right is None and k.top is None and k.bottom is None:
                kw, kh = w, h
            if k._width is not None:
                kw = k._width
            if k._height is not None:
                kh = k._height
            kw -= ml + mr
            kh -= mt + mb
            if k.left is not None and k.right is not None and k._width is None:
                kw = max(0, w-k.left-k.right-ml-mr)
            if k.top is not None and k.bottom is not None and k._height is None:
                kh = max(0, h-k.top-k.bottom-mt-mb)
            ax, ay = ((self.alignment.x+1)/2, (self.alignment.y+1)/2) if self.alignment else (0,0)
            left = k.left if k.left is not None else (
                w - kw - (k.right or 0) if k.right is not None else (w-kw)*ax)
            top = k.top if k.top is not None else (
                h - kh - (k.bottom or 0) if k.bottom is not None else (h-kh)*ay)
            k._place(x + left + ml, y + top + mt, kw, kh, scale)

    def _draw(self, r, x, y):
        pass

    def _draw_all(self, r, ox=0, oy=0):
        if not self.visible:
            return
        clipped = value(self.clip_behavior) != "none"
        if clipped:
            x,y,w,h = self._rect
            r.clip_push(x+ox,y+oy,w,h)
        try:
            super()._draw_all(r, ox, oy)
        finally:
            if clipped:
                r.clip_pop()


class Divider(Control):
    def __init__(self, height: float = 16, *, thickness: float = 1,
                 color=None, leading_indent: float = 0, trailing_indent: float = 0,
                 radius=None, **base: Unpack[ControlOptions]):
        super().__init__(**base)
        self.height = 16 if height is None else height
        self.thickness = 1 if thickness is None else thickness
        self.color = color
        self.leading_indent = leading_indent or 0
        self.trailing_indent = trailing_indent or 0
        self.radius = radius

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else (max_w or 0),
                self._height if self._height is not None else self.height)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        cy = y + (h - self.thickness) / 2
        r.fill_rect(x + self.leading_indent, cy,
                    max(0, w - self.leading_indent - self.trailing_indent),
                    self.thickness,
                    colors.parse_color(self.color or colors.Colors.OUTLINE_VARIANT), radius=self.radius or 0)


class VerticalDivider(Control):
    """A thin vertical line, flet-compatible with Divider's axis flipped."""

    def __init__(self, width: float | None = None, *, thickness: float | None = 1,
                 color=None, leading_indent: float = 0, trailing_indent: float = 0,
                 radius=None, **base: Unpack[ControlOptions]):
        super().__init__(**base)
        self.width = 16 if width is None else width
        self.thickness = 1 if thickness is None else thickness
        self.color = color
        self.leading_indent = leading_indent or 0
        self.trailing_indent = trailing_indent or 0
        self.radius = radius

    def _intrinsic(self, max_w, max_h, scale):
        return (self._width if self._width is not None else self.width,
                self._height if self._height is not None else (max_h or 0))

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        cx = x + (w - self.thickness) / 2
        r.fill_rect(cx, y + self.leading_indent, self.thickness,
                    max(0, h - self.leading_indent - self.trailing_indent),
                    colors.parse_color(self.color or colors.Colors.OUTLINE_VARIANT), radius=self.radius or 0)


class WindowDragArea(Control):
    """Turn its content into a draggable title-bar region (flet-compatible).

    A press inside the area enters the native move loop; a double press
    toggles maximize unless ``maximizable=False``. The native loop blocks
    the UI queue until the button is released, so ``on_drag_end`` is
    dispatched by the command queued behind the drag.
    """

    def __init__(self, content=None, *, maximizable: bool = True,
                 on_double_tap=None, on_drag_start=None, on_drag_end=None, **base: Unpack[ControlOptions]):
        super().__init__(**base)
        self.content = content
        self.maximizable = maximizable
        self.on_double_tap = on_double_tap
        self.on_drag_start = on_drag_start
        self.on_drag_end = on_drag_end
        self._last_press = None
        self._last_press_pos = None

    def _children(self):
        return [self.content] if self.content is not None else []

    def _intrinsic(self, max_w, max_h, scale):
        if self.content is None:
            return (self._width or max_w or 0, self._height or max_h or 0)
        w, h = self.content._intrinsic(max_w, max_h, scale)
        return (self._width or w, self._height or h)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        if self.content is not None:
            self.content._place(x, y, w, h, scale)

    def _draw(self, r, x, y):
        pass

    def _hit_test(self, x, y):
        x, y = self._hit_point(x, y)
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        if self.content is not None:
            hit = self.content._hit_test(x, y)
            if hit is not None:
                return hit  # interactive children (window buttons) win taps
        return self  # everything else drags the window

    def _hit_test_hover(self, x, y):
        x, y = self._hit_point(x, y)
        if not self.visible or self.disabled or not self._contains(x, y):
            return None
        if self.content is not None:
            hit = self.content._hit_test_hover(x, y)
            if hit is not None:
                return hit
        return self

    def _pressed_hook(self, x, y):
        page = self.page
        if page is None:
            return
        window = page.window
        now = time.perf_counter()
        last, last_pos = self._last_press, self._last_press_pos
        self._last_press, self._last_press_pos = now, (x, y)
        if window is None:
            return
        if (last is not None and now - last <= 0.5 and last_pos is not None
                and abs(x - last_pos[0]) <= 8 and abs(y - last_pos[1]) <= 8):
            self._last_press = None
            if self.maximizable:
                window.maximized = not window.maximized
            if self.on_double_tap:
                page._dispatch(self.on_double_tap)
            return
        native = getattr(window, "_native", None)
        if sys.platform != "win32" or native is None or not window.movable:
            return
        if self.on_drag_start:
            page._dispatch(self.on_drag_start)
        # FIFO on the UI queue: the drag blocks inside the native move loop
        # and the completion hook queued behind it runs on release.
        page._app.post(lambda: native.start_interaction(2))
        if self.on_drag_end:
            page._app.post(lambda: page._dispatch(self.on_drag_end))


class AnimatedSwitcherTransition(enum.Enum):
    """Visual strategy used while AnimatedSwitcher swaps its content."""
    FADE = "fade"
    ROTATION = "rotation"
    SCALE = "scale"


def _switch_ms(value):
    """Accept flet's DurationValue: a number of milliseconds or a Duration."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    ms = getattr(value, "in_milliseconds", None)
    if ms is None:
        ms = getattr(value, "in_microseconds", 0) / 1000.0
    return float(ms)


class AnimatedSwitcher(Stack):
    """Animates between old and new content, mirroring Flutter's switcher.

    The outgoing child stays in the tree below the incoming one (a centered
    Stack) until its reverse_duration elapses, so layout, attachment and hit
    testing all see a consistent tree; only the draw pass adds the fade or
    transform envelope.
    """

    def __init__(self, content=None, *, duration=1000, reverse_duration=None,
                 switch_in_curve=AnimationCurve.LINEAR,
                 switch_out_curve=AnimationCurve.LINEAR,
                 transition=AnimatedSwitcherTransition.FADE, **base: Unpack[ControlOptions]):
        super().__init__(alignment=Alignment.CENTER, clip_behavior="none", **base)
        self.duration = duration
        self.reverse_duration = (reverse_duration if reverse_duration is not None
                                 else duration)
        self.switch_in_curve = switch_in_curve
        self.switch_out_curve = switch_out_curve
        self.transition = transition
        self._content = content
        self._outgoing = []      # [{control, started, duration, curve, transition}]
        self._in_started = None  # None: current content appeared without animation
        self._sync_children()

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        old = self._content
        if old is value:
            return
        self._content = value
        if self.page is not None:
            now = time.perf_counter()
            # Toggling back to a still-fading control restores it instantly.
            self._outgoing = [entry for entry in self._outgoing
                              if entry["control"] is not value]
            if old is not None:
                self._outgoing.append({
                    "control": old, "started": now,
                    "duration": _switch_ms(self.reverse_duration) / 1000.0,
                    "curve": self.switch_out_curve,
                    "transition": self.transition})
            self._in_started = now
        self._sync_children()
        self.update()

    def _sync_children(self):
        self.controls = ([entry["control"] for entry in self._outgoing]
                         + ([self._content] if self._content is not None else []))

    def _progress(self, started, ms, now):
        duration = ms / 1000.0
        if duration <= 0:
            return 1.0
        return min(1.0, (now - started) / duration)

    def _in_fade(self, now):
        if self._in_started is None:
            return 1.0
        progress = self._progress(self._in_started, _switch_ms(self.duration), now)
        return ease(self.switch_in_curve, progress)

    def _tick_animations(self, now: float) -> bool:
        remaining = [entry for entry in self._outgoing
                     if now - entry["started"] < entry["duration"]]
        if len(remaining) != len(self._outgoing):
            self._outgoing = remaining
            self._sync_children()
            self.update()
        active = super()._tick_animations(now) or bool(self._outgoing)
        return active or self._in_fade(now) < 1.0

    def _draw_all(self, r, ox=0.0, oy=0.0):
        if not self.visible:
            return
        self._effects_begin(r, ox, oy)
        try:
            now = time.perf_counter()
            for entry in self._outgoing:
                progress = self._progress(entry["started"],
                                          entry["duration"] * 1000.0, now)
                fade = 1.0 - ease(entry["curve"], progress)
                if fade > 0.0:
                    self._draw_entry(r, entry["control"], ox, oy, fade,
                                     entry["transition"], 1.0 - progress)
            if self._content is not None:
                self._draw_entry(r, self._content, ox, oy, self._in_fade(now),
                                 self.transition,
                                 1.0 if self._in_started is None else
                                 self._progress(self._in_started,
                                                _switch_ms(self.duration), now))
        finally:
            self._effects_end(r)

    def _draw_entry(self, r, child, ox, oy, opacity, transition, progress):
        mode = getattr(transition, "value", transition)
        pushed_opacity = pushed_transform = False
        try:
            if opacity < 1.0:
                r.opacity_push(max(0.0, min(1.0, opacity)))
                pushed_opacity = True
            if mode == "rotation" and progress < 1.0:
                x, y, w, h = child._rect
                cx, cy = x + w / 2.0, y + h / 2.0
                angle = progress * 2.0 * math.pi
                cosine, sine = math.cos(angle), math.sin(angle)
                r.transform_push((cosine, sine, -sine, cosine,
                                  cx - cosine * cx + sine * cy,
                                  cy - sine * cx - cosine * cy),
                                 bounds=child._paint_bounds(ox, oy))
                pushed_transform = True
            elif mode == "scale" and progress < 1.0:
                if progress <= 0.0:
                    return
                x, y, w, h = child._rect
                cx, cy = x + w / 2.0, y + h / 2.0
                factor = ease(self.switch_in_curve, progress)
                r.transform_push((factor, 0.0, 0.0, factor,
                                  cx * (1.0 - factor), cy * (1.0 - factor)),
                                 bounds=child._paint_bounds(ox, oy))
                pushed_transform = True
            child._draw_all(r, ox, oy)
        finally:
            if pushed_transform:
                r.transform_pop()
            if pushed_opacity:
                r.opacity_pop()
