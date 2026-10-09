"""Buttons: Button base + Filled/FilledTonal/Elevated/Outlined/Text + IconButton.

Button API: label via content= (str or Control), icon=, on_click, on_hover,
color/bgcolor, disabled.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Unpack

from .. import colors, motion, text as txt
from ..control import Control, ControlOptions
from ..event import fire
from ..text import render_icon_cached
from ..painting import draw_shadow
from ..types import as_padding, Alignment
from ._compat import style_value, state_value, shape_radius, constrain, reject_options, value
from ._material import (draw_state_layer, init_state_layer, press,
                        release, set_hover, tick_state_layer)

# M3 button metrics
_HEIGHT = 40.0
_PAD_H = 24.0
_GAP = 8.0
_LABEL_SIZE = 14.0
_LABEL_WEIGHT = 500
_ICON_SIZE = 18.0

# Expressive button dimensions. Each entry is
# (height, horizontal padding, icon, gap, text size, weight,
#  square corner, pressed corner). Extra-small padding/spacing is 12/4.
_EXPRESSIVE_SIZES = {
    "xsmall": (32.0, 12.0, 20.0, 4.0, 14.0, 500, 12.0, 8.0),
    "small": (40.0, 16.0, 20.0, 8.0, 14.0, 500, 12.0, 8.0),
    "medium": (56.0, 24.0, 24.0, 8.0, 16.0, 500, 16.0, 12.0),
    "large": (96.0, 48.0, 32.0, 12.0, 24.0, 400, 28.0, 16.0),
    "xlarge": (136.0, 64.0, 40.0, 16.0, 32.0, 400, 28.0, 16.0),
}


class Button(Control):
    _focusable = True
    variant_bg = None     # class defaults, resolved at draw (theme-aware)
    variant_fg = None
    variant_border = None
    variant_elevation = 0.0

    def __init__(self, content=None, *, icon=None, icon_color=None, color=None,
                 bgcolor=None, elevation: float = 1, style=None, on_click=None,
                 on_hover=None, on_long_press=None, on_focus=None, on_blur=None,
                 autofocus=False, url=None, clip_behavior=None, expressive=False, size=None,
                 shape="round", **base: Unpack[ControlOptions]):
        super().__init__(**base)
        self.expressive = bool(expressive or size is not None)
        self.button_size = (size or "small").replace("_", "").lower()
        if self.expressive and self.button_size not in _EXPRESSIVE_SIZES:
            raise ValueError(f"invalid expressive button size: {size!r}")
        if shape not in ("round", "square"):
            raise ValueError(f"invalid expressive button shape: {shape!r}")
        self.button_shape = shape
        self.content = content      # str or Control
        self.icon = icon
        self.icon_color = icon_color
        self.color = color
        self.bgcolor = bgcolor
        self.elevation = elevation
        self.style = style
        if style is not None:
            if getattr(style,"enable_feedback",None):
                raise NotImplementedError("ButtonStyle.enable_feedback is not supported")
            if getattr(style,"mouse_cursor",None) is not None:
                self.mouse_cursor = style.mouse_cursor
        self.on_click = on_click
        self.on_hover = on_hover
        self.on_long_press = on_long_press
        self.on_focus = on_focus
        self.on_blur = on_blur
        self.autofocus = autofocus
        self.url = url
        self.clip_behavior = clip_behavior
        self._focused = False
        self._hovered = False
        self._pressed = False
        self._elevation_progress = self.variant_elevation
        self._shape_progress = 0.0
        init_state_layer(self)

    def _metrics(self):
        metrics = (_EXPRESSIVE_SIZES[self.button_size] if self.expressive else
                (_HEIGHT, _PAD_H, _ICON_SIZE, _GAP, _LABEL_SIZE,
                 _LABEL_WEIGHT, _HEIGHT / 2, _HEIGHT / 2))
        h,pad,icon,gap,size,weight,a,b = metrics
        ts = style_value(self, "text_style")
        return h,pad,style_value(self,"icon_size",icon),gap, getattr(ts,"size",None) or size, getattr(ts,"weight",None) or weight,a,b

    def _radius(self, height):
        shape = style_value(self, "shape")
        if shape is not None:
            return shape_radius(shape, self._rect[2], height)
        if not self.expressive:
            return height / 2
        _, _, _, _, _, _, square, pressed = self._metrics()
        normal = height / 2 if self.button_shape == "round" else square
        return normal + (pressed - normal) * self._shape_progress

    # -- metrics -----------------------------------------------------------
    def _label(self) -> str:
        return self.content if isinstance(self.content, str) else ""

    def _intrinsic(self, max_w, max_h, scale):
        token_h, pad, icon_size, gap, label_size, label_weight, _, _ = self._metrics()
        w, h = 0.0, token_h
        if label := self._label():
            lw, lh = txt.measure(label, label_size, scale=scale,
                                 weight=label_weight,family=getattr(style_value(self,"text_style"),"font_family",None))
            w += lw
            if not self.expressive:
                h = max(h, lh + 20)
        elif isinstance(self.content, Control):
            cw, ch = self.content._intrinsic(max_w, max_h, scale)
            w += cw
            h = max(h, ch + 20)
        if self.icon is not None:
            iw = self.icon._intrinsic(max_w,max_h,scale)[0] if isinstance(self.icon,Control) else icon_size
            w += iw + (gap if w else 0)
        # Baseline leading-icon buttons use 16/24; Expressive sizes have
        # symmetric content padding from ButtonDefaults.contentPaddingFor.
        start = pad if self.expressive or self.icon is None else 16.0
        w += start + pad
        density = {"compact":-8,"comfortable":-4}.get(value(style_value(self,"visual_density")),0)
        w,h = max(0,w+density),max(0,h+density)
        padding = style_value(self, "padding")
        if padding is not None:
            p = as_padding(padding)
            w += p.left+p.right-start-pad
            h = max(h, txt.line_height(label_size,scale=scale)+p.top+p.bottom)
        if self._width is not None:
            w = self._width
        if self._height is not None:
            h = self._height
        return w, h

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        _, _, icon_size, gap, _, _, _, _ = self._metrics()
        p = self._padding()
        cw,ch = self.content._intrinsic(w,h,scale) if isinstance(self.content,Control) else (txt.line_width(self._label(),self._metrics()[4],scale=scale),0)
        iw,ih = self.icon._intrinsic(w,h,scale) if isinstance(self.icon,Control) else ((icon_size,icon_size) if self.icon is not None else (0,0))
        total = cw+iw+(gap if cw and iw else 0)
        a = style_value(self,"alignment",Alignment.CENTER)
        cx = x+p.left+(w-p.left-p.right-total)*(a.x+1)/2
        if isinstance(self.icon,Control):
            self.icon._place(cx,y+p.top+(h-p.top-p.bottom-ih)*(a.y+1)/2,iw,ih,scale)
        if isinstance(self.content,Control):
            self.content._place(cx+iw+(gap if iw and cw else 0),y+p.top+(h-p.top-p.bottom-ch)*(a.y+1)/2,cw,ch,scale)

    def _padding(self):
        pad = self._metrics()[1]
        default = as_padding(None)
        default.left = pad if self.expressive or self.icon is None else 16
        default.right = pad
        return as_padding(style_value(self,"padding",default))

    def _children(self):
        return [c for c in (self.icon,self.content) if isinstance(c,Control)]

    def focus(self):
        if self.page:
            self.page.focus(self)

    def _style_duration(self,fallback):
        duration = getattr(self.style,"animation_duration",None) if self.style else None
        return fallback if duration is None else getattr(duration,"in_milliseconds",duration)

    def _key(self,e):
        import pygame
        if not self.disabled and e.key in (pygame.K_RETURN,pygame.K_KP_ENTER,pygame.K_SPACE):
            fire(self,"click")

    # -- colors ------------------------------------------------------------
    def _resolve(self, name, fallback):
        v = getattr(self, name)
        if v is None:
            v = fallback
        return colors.parse_color(v) if v is not None else None

    def _bg(self):
        styled = style_value(self,"bgcolor")
        if styled is not None:
            return colors.parse_color(styled)
        if self.disabled and (self.bgcolor is not None or self.variant_bg is not None):
            r, g, b, _ = colors.parse_color(colors.Colors.ON_SURFACE)
            return r, g, b, round(255 * 0.10)
        if self.bgcolor is not None:
            base = colors.parse_color(self.bgcolor)
        elif self.variant_bg is not None:
            base = colors.parse_color(self.variant_bg)
        else:
            return None
        return base

    def _fg_raw(self):
        return style_value(self,"color",self.color or self.variant_fg or colors.Colors.ON_SURFACE)

    def _fg(self):
        if style_value(self,"color") is not None:
            return colors.parse_color(style_value(self,"color"))
        if self.disabled:
            return colors.parse_color(colors.Colors.ON_SURFACE_VARIANT)
        return colors.parse_color(self._fg_raw())

    # -- drawing -----------------------------------------------------------
    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        _, pad, icon_size, gap, label_size, label_weight, _, _ = self._metrics()
        radius = self._radius(h)
        bg = self._bg()
        elevation = style_value(self,"elevation", self.elevation if self.elevation != 1 else self._elevation_progress)
        if elevation > 0 and not self.disabled:
            shadow_color = style_value(self,"shadow_color")
            if shadow_color is None:
                draw_shadow(r,(x,y,w,h),radius,elevation)
            else:
                from .containers import _draw_shadow
                from ..types import BoxShadow,Offset
                _draw_shadow(r,x,y,w,h,BoxShadow(blur_radius=elevation*3,offset=Offset(0,elevation),color=shadow_color),radius)
        if bg is not None:
            r.fill_rect(x, y, w, h, bg, radius=radius)
        side = style_value(self,"side")
        if self.variant_border is not None or side is not None:
            border = (colors.Colors.OUTLINE_VARIANT if self.disabled
                      else self.variant_border)
            border = side.color if side and side.color is not None else border or colors.Colors.OUTLINE
            r.stroke_rect(x, y, w, h, colors.parse_color(border),
                          width=side.width if side else 1, radius=radius)
        if not self.disabled:
            if self._focused:
                fc = colors.parse_color(style_value(self,"overlay_color",self._fg_raw()))
                r.overlay_rect(x,y,w,h,(*fc[:3],round(fc[3]*.12)),radius=radius)
            draw_state_layer(self, r, (x, y, w, h), style_value(self,"overlay_color", self._fg_raw()), radius)
        # content: [icon] gap [label/control]
        scale = r.scale
        icon_surf = label_surf = None
        label_w = icon_w = 0.0
        if self.icon is not None and not isinstance(self.icon,Control):
            icon_surf = render_icon_cached(
                self.icon, round(icon_size * scale),
                colors.parse_color(style_value(self,"icon_color",self.icon_color))
                if style_value(self,"icon_color",self.icon_color) and not self.disabled else self._fg())
            icon_w = icon_surf.get_width() / scale
        elif isinstance(self.icon,Control):
            icon_w = self.icon._rect[2]
        if label := self._label():
            style = style_value(self,"text_style")
            label_surf = txt.render_line_cached(
                label, label_size, scale=scale, weight=label_weight,
                color=self._fg(),family=getattr(style,"font_family",None),italic=getattr(style,"italic",False))
            label_w = label_surf.get_width() / scale
        elif isinstance(self.content, Control):
            label_w = self.content._rect[2]
        total = icon_w + (gap if icon_w and label_w else 0) + label_w
        p = self._padding()
        a = style_value(self,"alignment",Alignment.CENTER)
        content_w = w-p.left-p.right
        cx = x+p.left+(content_w-total)*(a.x+1)/2
        cy = y+p.top+(h-p.top-p.bottom)*(a.y+1)/2
        if icon_surf is not None:
            r.blit_cached(icon_surf, cx, cy - icon_surf.get_height() / (2 * scale),
                   alpha=0.38 if self.disabled else 1.0)
            cx += icon_w + (gap if label_w else 0)
        if label_surf is not None:
            if isinstance(self.icon,Control):
                cx += icon_w+(gap if label_w else 0)
            r.blit_cached(label_surf, cx, cy - label_surf.get_height() / (2 * scale),
                   alpha=0.38 if self.disabled else 1.0)

    def _draw_all(self, r, ox: float = 0.0, oy: float = 0.0):
        if not self.visible:
            return
        self._effects_begin(r, ox, oy)
        try:
            self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
            clipped = value(self.clip_behavior) not in (None,"none")
            if clipped:
                r.clip_push(self._rect[0]+ox,self._rect[1]+oy,*self._rect[2:])
            try:
                for child in self._children():
                    child._draw_all(r,ox,oy)
            finally:
                if clipped:
                    r.clip_pop()
        finally:
            self._effects_end(r)

    # -- pointer hooks (page routes through here) --------------------------
    def _hit_test(self, x, y):
        x,y = self._hit_point(x,y)
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        if self.variant_elevation:
            self._animate_internal(
                "_elevation_progress", 3.0 if on else self.variant_elevation,
                self._style_duration(motion.SHORT3), motion.EMPHASIZED)
        self.repaint()
        fire(self, "hover", "true" if on else "false")

    def _pressed_hook(self, x, y):
        import time
        self._long_press_at = time.perf_counter()+.5 if self.on_long_press else None
        self._consume_click = False
        press(self, x, y, ripple_duration=motion.SHORT4,
              press_duration=75)
        if self.expressive:
            self._animate_internal("_shape_progress", 1.0, self._style_duration(motion.SHORT2),
                                   motion.EMPHASIZED)
        if self.variant_elevation:
            self._animate_internal("_elevation_progress", 1.0, self._style_duration(motion.SHORT3),
                                   motion.EMPHASIZED)

    def _released_hook(self, _x, _y):
        self._long_press_at = None
        release(self, minimum_ms=0, fade_duration=motion.SHORT2)
        if self.expressive:
            self._animate_internal("_shape_progress", 0.0, self._style_duration(motion.SHORT2),
                                   motion.EMPHASIZED)
        if self.variant_elevation:
            self._animate_internal(
                "_elevation_progress",
                3.0 if self._hovered else self.variant_elevation,
                self._style_duration(motion.SHORT3), motion.EMPHASIZED)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        deadline = getattr(self,"_long_press_at",None)
        if deadline is not None and self._pressed:
            if now >= deadline:
                self._long_press_at = None
                self._consume_click = True
                fire(self,"long_press")
            else:
                waiting = True
        return super()._tick_animations(now) or waiting


class FilledButton(Button):
    variant_bg = colors.Colors.PRIMARY
    variant_fg = colors.Colors.ON_PRIMARY


class FilledTonalButton(Button):
    variant_bg = colors.Colors.SECONDARY_CONTAINER
    variant_fg = colors.Colors.ON_SECONDARY_CONTAINER


class ElevatedButton(Button):
    variant_bg = colors.Colors.SURFACE_CONTAINER_LOW
    variant_fg = colors.Colors.PRIMARY
    variant_elevation = 1.0


class OutlinedButton(Button):
    variant_bg = None
    variant_fg = colors.Colors.ON_SURFACE_VARIANT
    variant_border = colors.Colors.OUTLINE_VARIANT


class TextButton(Button):
    variant_bg = None
    variant_fg = colors.Colors.PRIMARY


class ExpressiveButton(Button):
    """Expressive button with size tokens and pressed shape morph."""
    variant_bg = colors.Colors.PRIMARY
    variant_fg = colors.Colors.ON_PRIMARY

    def __init__(self, content=None, *, size="small", shape="round", **kwargs):
        super().__init__(content, size=size, shape=shape, **kwargs)


# Button uses the Material elevated-button surface and elevation.
class _ConcreteButton(Button):
    variant_bg = colors.Colors.SURFACE_CONTAINER_LOW
    variant_fg = colors.Colors.PRIMARY
    variant_elevation = 1.0


Button = _ConcreteButton


class IconButton(Control):
    _focusable = True

    def __init__(self, icon=None, *, icon_size: float | None = None, icon_color=None,
                 selected_icon=None, selected=False, bgcolor=None,
                 hover_color=None, tooltip=None, on_click=None, on_hover=None,
                 selected_icon_color=None, highlight_color=None, style=None,
                 autofocus=False, disabled_color=None, focus_color=None,
                 splash_color=None, splash_radius=None, alignment=None,
                 padding=None, enable_feedback=None, url=None, mouse_cursor=None,
                 visual_density=None, size_constraints=None,
                 on_long_press=None, on_focus=None, on_blur=None,
                 expressive=False, size=None, shape="round", **base: Unpack[ControlOptions]):
        reject_options("IconButton", enable_feedback=True if enable_feedback else None)
        super().__init__(tooltip=tooltip, **base)
        self.expressive = bool(expressive or size is not None)
        self.button_size = (size or "small").replace("_", "").lower()
        if self.button_size not in _EXPRESSIVE_SIZES or shape not in ("round", "square"):
            raise ValueError("invalid expressive icon button size or shape")
        self.button_shape = shape
        self.icon = icon
        default_icon = {"xsmall": 20, "small": 24, "medium": 24,
                        "large": 32, "xlarge": 40}[self.button_size]
        self.icon_size = icon_size if icon_size is not None else default_icon
        self.icon_color = icon_color
        self.selected_icon = selected_icon
        self.selected = selected
        self.bgcolor = bgcolor
        self.hover_color = hover_color
        self.on_click = on_click
        self.on_hover = on_hover
        self.selected_icon_color = selected_icon_color
        self.highlight_color = highlight_color
        self.style = style
        if style is not None and getattr(style,"enable_feedback",None):
            raise NotImplementedError("ButtonStyle.enable_feedback is not supported")
        self.autofocus = autofocus
        self.disabled_color = disabled_color
        self.focus_color = focus_color
        self.splash_color = splash_color
        self.splash_radius = splash_radius
        self.alignment = alignment or Alignment.CENTER
        self.padding = padding
        self.url = url
        self.mouse_cursor = mouse_cursor
        if style is not None and getattr(style,"mouse_cursor",None) is not None:
            self.mouse_cursor = style.mouse_cursor
        self.visual_density = visual_density
        self.size_constraints = size_constraints
        self.on_long_press, self.on_focus, self.on_blur = on_long_press,on_focus,on_blur
        self._focused = False
        self._hovered = False
        self._pressed = False
        self._shape_progress = 0.0
        self._selected_progress = float(bool(selected))
        self._last_selected = bool(selected)
        init_state_layer(self)

    def _intrinsic(self, max_w, max_h, scale):
        side = _EXPRESSIVE_SIZES[self.button_size][0] if self.expressive else 40.0
        side += {"compact":-8,"comfortable":-4}.get(value(style_value(self,"visual_density",self.visual_density)),0)
        s = self._width if self._width is not None else side
        h = self._height if self._height is not None else side
        p = as_padding(style_value(self,"padding",self.padding))
        s,h = max(s,self.icon_size+p.left+p.right),max(h,self.icon_size+p.top+p.bottom)
        return constrain(s,h,self.size_constraints)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        icon = self._current_icon()
        if isinstance(icon,Control):
            iw,ih = icon._intrinsic(w,h,scale)
            a = style_value(self,"alignment",self.alignment)
            icon._place(x+(w-iw)*(a.x+1)/2,y+(h-ih)*(a.y+1)/2,iw,ih,scale)

    def _children(self):
        return [c for c in (self.icon,self.selected_icon) if isinstance(c,Control)]

    focus = Button.focus
    _key = Button._key
    _style_duration = Button._style_duration

    def _current_icon(self):
        if self.selected and self.selected_icon is not None:
            return self.selected_icon
        return self.icon

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        radius = min(w, h) / 2
        if self.expressive:
            square, pressed = _EXPRESSIVE_SIZES[self.button_size][-2:]
            normal, selected = ((radius, square) if self.button_shape == "round"
                                else (square, radius))
            radius = normal + (selected - normal) * self._selected_progress
            radius += (pressed - radius) * self._shape_progress
        radius = shape_radius(style_value(self,"shape"),w,h,radius)
        role = (self.disabled_color or colors.Colors.ON_SURFACE if self.disabled else (self.selected_icon_color if self.selected else None) or self.icon_color or
                (colors.Colors.PRIMARY if self.selected else colors.Colors.ON_SURFACE_VARIANT))
        role = style_value(self,"icon_color",style_value(self,"color",role))
        fg = colors.parse_color(role)
        elevation = style_value(self,"elevation",0)
        if elevation > 0:
            draw_shadow(r,(x,y,w,h),radius,elevation)
        bg = style_value(self,"bgcolor",self.bgcolor)
        if bg is not None:
            r.fill_rect(x, y, w, h, colors.parse_color(bg),
                        radius=radius)
        state_color = (self.splash_color or self.highlight_color if self._pressed else
                       self.focus_color if self._focused else self.hover_color) or role
        state_color = style_value(self,"overlay_color",state_color)
        if not self.disabled:
            if self._focused:
                fc = colors.parse_color(self.focus_color or state_color)
                r.overlay_rect(x,y,w,h,(*fc[:3],round(fc[3]*.12)),radius=radius)
            draw_state_layer(self, r, (x, y, w, h), state_color, radius)
        side = style_value(self,"side")
        if side is not None and side.color is not None and side.width > 0:
            r.stroke_rect(x,y,w,h,colors.parse_color(side.color),width=side.width,radius=radius)
        icon = self._current_icon()
        if isinstance(icon,Control):
            icon._draw_all(r, x-self._rect[0], y-self._rect[1])
            return
        if icon is None:
            return
        surf = render_icon_cached(icon, round(style_value(self,"icon_size",self.icon_size) * r.scale), fg)
        a = style_value(self,"alignment",self.alignment)
        p = as_padding(style_value(self,"padding",self.padding))
        r.blit_cached(surf, x+p.left+(w-p.left-p.right-surf.get_width()/r.scale)*(a.x+1)/2,
               y+p.top+(h-p.top-p.bottom-surf.get_height()/r.scale)*(a.y+1)/2,
               alpha=.38 if self.disabled else 1.0)

    __unsupported_parameters__ = {"enable_feedback"}

    def _draw_all(self,r,ox=0,oy=0):
        if not self.visible:
            return
        self._effects_begin(r, ox, oy)
        try:
            self._draw(r,self._rect[0]+ox,self._rect[1]+oy)
        finally:
            self._effects_end(r)

    def _hit_test(self, x, y):
        x,y = self._hit_point(x,y)
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        self.repaint()
        fire(self, "hover", "true" if on else "false")

    def _pressed_hook(self, x, y):
        import time
        self._long_press_at = time.perf_counter()+.5 if self.on_long_press else None
        self._consume_click = False
        press(self, x, y, ripple_duration=motion.SHORT4,
              press_duration=75)
        if self.expressive:
            self._animate_internal("_shape_progress", 1.0, self._style_duration(motion.SHORT2),
                                   motion.EMPHASIZED)

    def _released_hook(self, _x, _y):
        self._long_press_at = None
        release(self, minimum_ms=0, fade_duration=motion.SHORT2)
        if self.expressive:
            self._animate_internal("_shape_progress", 0.0, self._style_duration(motion.SHORT2),
                                   motion.EMPHASIZED)

    def _prepare_animations(self, now):
        super()._prepare_animations(now)
        if bool(self.selected) != self._last_selected:
            self._last_selected = bool(self.selected)
            self._animate_internal("_selected_progress", float(bool(self.selected)),
                                   self._style_duration(motion.SHORT3), motion.EMPHASIZED, now=now)

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        deadline = getattr(self,"_long_press_at",None)
        if deadline is not None and self._pressed:
            if now >= deadline:
                self._long_press_at = None
                self._consume_click = True
                fire(self,"long_press")
            else:
                waiting = True
        return super()._tick_animations(now) or waiting


class ExpressiveIconButton(IconButton):
    def __init__(self, icon, *, size="small", **kwargs):
        super().__init__(icon, size=size, **kwargs)
