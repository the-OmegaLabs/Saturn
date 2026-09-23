"""Layout containers: Container, Row, Column, Stack, Divider.

Layout protocol (two passes, absolute rects):
  _intrinsic(max_w, max_h, scale) -> (w, h)   desired size under constraints
  _place(x, y, w, h, scale)                    final box; sets _rect, recurses
Draw pass: _draw_all walks the tree and renders at the absolute rects.

Row/Column implement the flet flex subset: alignment (MainAxisAlignment),
cross alignment (CrossAxisAlignment), spacing, tight, expand on children.
Container adds padding/margin/bgcolor/border/border_radius/alignment.
Stack children position via their own left/top/right/bottom.
"""
from __future__ import annotations

from .. import colors
from ..control import Control
from ..types import (CrossAxisAlignment, MainAxisAlignment,
                     as_border_radius, as_padding)
from ._material import (draw_state_layer, init_state_layer, press,
                        release, set_hover, tick_state_layer)


def _margins(c):
    m = as_padding(c.margin)
    return m.left, m.top, m.right, m.bottom


class _Multi(Control):
    """Shared flex plumbing for Row/Column."""

    vertical = False  # Row

    def __init__(self, *items, controls=None,
                 alignment=MainAxisAlignment.START,
                 vertical_alignment=None, horizontal_alignment=None,
                 spacing: float = 10, tight: bool = False, **base):
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

    def _children(self):
        return self.controls

    def _visible(self):
        return [c for c in self.controls if c.visible]

    @staticmethod
    def _expand_of(c) -> float:
        e = c.expand
        if e is True:
            return 1.0
        return float(e) if isinstance(e, (int, float)) and e else 0.0

    # -- measuring -----------------------------------------------------------
    def _intrinsic(self, max_w, max_h, scale):
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

    def _footprint(self, k, max_w, scale):
        """Child intrinsic size + its margin (margin sits outside the box)."""
        ml, mt, mr, mb = _margins(k)
        w, h = k._intrinsic(
            (max_w - ml - mr) if max_w is not None else None, None, scale)
        return w + ml + mr, h + mt + mb

    # -- placing -----------------------------------------------------------
    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        kids = self._visible()
        if not kids:
            return
        sizes = [self._footprint(k, w, scale) for k in kids]
        main_sizes = [s[0] if not self.vertical else s[1] for s in sizes]
        box_main = w if not self.vertical else h
        used = sum(main_sizes) + self.spacing * (len(kids) - 1)
        free = box_main - used

        flex = [self._expand_of(k) for k in kids]
        if sum(flex) and free > 0:
            share = free / sum(flex)
            for i, k in enumerate(kids):
                if flex[i]:
                    main_sizes[i] += share * flex[i]
            free = 0.0

        gap = self.spacing
        pos = 0.0
        a = self.alignment
        if a is MainAxisAlignment.END:
            pos = free
        elif a is MainAxisAlignment.CENTER:
            pos = free / 2
        elif a is MainAxisAlignment.SPACE_BETWEEN and len(kids) > 1:
            gap += free / (len(kids) - 1)
        elif a is MainAxisAlignment.SPACE_AROUND and len(kids):
            gap += free / len(kids)
            pos = gap / 2
        elif a is MainAxisAlignment.SPACE_EVENLY and len(kids):
            gap += free / (len(kids) + 1)
            pos = gap

        for i, k in enumerate(kids):
            ml, mt, mr, mb = _margins(k)
            fw, fh = sizes[i]
            if flex[i]:
                if self.vertical:
                    fh = main_sizes[i]
                else:
                    fw = main_sizes[i]
            # margin sits outside the child's box
            cw, ch = fw - ml - mr, fh - mt - mb
            # cross-axis STRETCH fills the inner cross size (unless fixed)
            if not self.vertical:
                if self.vertical_alignment is CrossAxisAlignment.STRETCH and k._height is None:
                    ch = h - mt - mb
            elif self.horizontal_alignment is CrossAxisAlignment.STRETCH and k._width is None:
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
        if a is CrossAxisAlignment.END:
            return inner_cross - child_cross
        if a is CrossAxisAlignment.CENTER:
            return (inner_cross - child_cross) / 2
        return 0.0  # START / BASELINE / STRETCH

    def _draw(self, r, x, y):
        pass  # children render via _draw_all


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
                 on_long_press=None, **base):
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
        if not self.visible or self.disabled:
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
        if not self.ink:
            return
        press(self, x, y)

    def _released_hook(self, _x, _y):
        if not self.ink:
            return
        release(self)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now) if self.ink else False
        return super()._tick_animations(now) or waiting

    def _children(self):
        return [self.content] if self.content is not None else []

    def _intrinsic(self, max_w, max_h, scale):
        padding = as_padding(self.padding)
        pad_w = padding.left + padding.right
        pad_h = padding.top + padding.bottom
        if self.content is not None:
            cw, ch = self.content._intrinsic(
                max(0.0, max_w - pad_w) if max_w is not None else None,
                max(0.0, max_h - pad_h) if max_h is not None else None,
                scale)
        else:
            cw = ch = 0.0
        w = self._width if self._width is not None else cw + pad_w
        h = self._height if self._height is not None else ch + pad_h
        # Flutter's parent constraints win over a child's requested size.
        # This is observable in Flet when, for example, a width=460 card is
        # placed in a 330px-wide page: it shrinks to the available width
        # instead of overflowing symmetrically outside the window.
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
        if self.border is not None and self.border.left.color is not None:
            r.stroke_rect(x, y, w, h, colors.parse_color(self.border.left.color),
                          width=self.border.left.width, radius=self._radius())
        if self.ink:
            draw_state_layer(self, r, (x, y, w, h),
                             colors.Colors.ON_SURFACE, self._radius())
        if self.border_radius:
            r.clip_push(x, y, w, h)

    def _draw_all(self, r, ox: float = 0.0, oy: float = 0.0):
        if not self.visible:
            return
        self._effects_begin(r)
        try:
            self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
            if self.content is not None:
                self.content._draw_all(r, ox, oy)
            if self.border_radius:
                r.clip_pop()
        finally:
            self._effects_end(r)

    def _radius(self):
        return as_border_radius(self.border_radius).top_left


class Stack(Control):
    def __init__(self, *items, controls=None, **base):
        if controls is not None:
            if items:
                raise TypeError("controls cannot be combined with positional children")
            items = tuple(controls)
        elif len(items) == 1 and isinstance(items[0], list):
            items = tuple(items[0])
        super().__init__(**base)
        self.controls = list(items)

    def _children(self):
        return self.controls

    def _intrinsic(self, max_w, max_h, scale):
        ws, hs = 0.0, 0.0
        for k in self.controls:
            if not k.visible:
                continue
            w, h = k._intrinsic(max_w, max_h, scale)
            ws, hs = max(ws, w), max(hs, h)
        w = self._width if self._width is not None else ws
        h = self._height if self._height is not None else hs
        # flet/Flutter: the Stack itself fits its constraints; oversized
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
                # flet: an expand child of a Stack stretches to the stack
                k._place(x, y, w, h, scale)
                continue
            ml, mt, mr, mb = _margins(k)
            kw, kh = k._intrinsic(w, h, scale)
            if k._width is not None:
                kw = k._width
            if k._height is not None:
                kh = k._height
            kw -= ml + mr
            kh -= mt + mb
            left = k.left if k.left is not None else (
                w - kw - (k.right or 0) if k.right is not None else 0)
            top = k.top if k.top is not None else (
                h - kh - (k.bottom or 0) if k.bottom is not None else 0)
            k._place(x + left + ml, y + top + mt, kw, kh, scale)

    def _draw(self, r, x, y):
        pass


class Divider(Control):
    def __init__(self, *, height: float = 16, thickness: float = 1,
                 color=None, leading_indent: float = 0, trailing_indent: float = 0,
                 **base):
        super().__init__(**base)
        self.height = height
        self.thickness = thickness
        self.color = color
        self.leading_indent = leading_indent
        self.trailing_indent = trailing_indent

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
                    colors.parse_color(self.color or colors.Colors.OUTLINE_VARIANT))
