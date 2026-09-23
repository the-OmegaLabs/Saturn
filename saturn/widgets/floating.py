"""Expressive floating toolbars and anchored FAB action menus."""
import pygame

from .. import colors, motion
from ..control import Control
from ..event import fire
from ..painting import draw_shadow
from .._gen.icons import Icons
from .buttons import ExpressiveButton
from .fab import FloatingActionButton
from .scrolling import ListView


def _slots(value):
    return [] if value is None else [value] if isinstance(value, Control) else list(value)


class FloatingToolbar(Control):
    """64dp capsule toolbar, with animated optional leading/trailing slots."""
    def __init__(self, *items, controls=None, leading=None, trailing=None,
                 expanded=True, vertical=False, vibrant=False, bgcolor=None,
                 elevation=6, **base):
        super().__init__(**base)
        if controls is not None and items:
            raise TypeError('use either controls or positional items')
        self.controls = list(controls) if controls is not None else _slots(items[0]) if len(items)==1 and isinstance(items[0], (list, tuple)) else list(items)
        self.leading_controls, self.trailing_controls = _slots(leading), _slots(trailing)
        if not all(isinstance(c, Control) for c in self._children()):
            raise TypeError('toolbar slots must be controls')
        self.expanded, self.vertical, self.vibrant = bool(expanded), vertical, vibrant
        self.bgcolor, self.elevation = bgcolor, elevation
        self._reveal = float(self.expanded)
        self._last_expanded = self.expanded
        self._clips = {}

    def _children(self):
        return self.leading_controls + self.controls + self.trailing_controls

    def toggle(self):
        self.expanded = not self.expanded
        self.update()

    def _prepare_animations(self, now):
        super()._prepare_animations(now)
        if self.expanded != self._last_expanded:
            self._last_expanded = self.expanded
            self._animate_internal('_reveal', float(self.expanded), motion.MEDIUM1,
                                   motion.EMPHASIZED, now=now)

    def _measure(self, scale):
        result = []
        for group, fraction in ((self.leading_controls, self._reveal),
                                (self.controls, 1), (self.trailing_controls, self._reveal)):
            for child in group:
                if child.visible:
                    w, h = child._intrinsic(None, None, scale)
                    result.append((child, w, h, fraction))
        return result

    def _intrinsic(self, max_w, max_h, scale):
        entries = self._measure(scale)
        main = 16 + sum(((h if self.vertical else w)+4)*p for _, w, h, p in entries)
        if entries:
            main -= 4 * entries[-1][3]
        cross = max(64, max((w if self.vertical else h for _,w,h,_ in entries), default=0)+16)
        w, h = (cross, main) if self.vertical else (main, cross)
        return self._width if self._width is not None else w, self._height if self._height is not None else h

    def _place(self, x, y, w, h, scale):
        self._rect = x, y, w, h
        cursor = (y if self.vertical else x)+8
        self._clips = {}
        for child, cw, ch, p in self._measure(scale):
            if p <= 0:
                continue
            if self.vertical:
                child._place(x+(w-cw)/2, cursor, cw, ch, scale)
                clip = (x, cursor, w, ch*p)
                cursor += (ch+4)*p
            else:
                child._place(cursor, y+(h-ch)/2, cw, ch, scale)
                clip = (cursor, y, cw*p, h)
                cursor += (cw+4)*p
            self._clips[child] = clip

    def _draw_all(self, r, ox=0, oy=0):
        if not self.visible:
            return
        self._effects_begin(r)
        try:
            x,y,w,h = self._rect
            rect = (x+ox,y+oy,w,h)
            draw_shadow(r, rect, min(w,h)/2, self.elevation)
            role = colors.Colors.PRIMARY_CONTAINER if self.vibrant else colors.Colors.SURFACE_CONTAINER
            r.fill_rect(*rect, colors.parse_color(self.bgcolor or role), radius=min(w,h)/2)
            r.clip_push(*rect)
            for child, (cx,cy,cw,ch) in self._clips.items():
                r.clip_push(cx+ox,cy+oy,cw,ch)
                child._draw_all(r,ox,oy)
                r.clip_pop()
            r.clip_pop()
        finally:
            self._effects_end(r)

    def _hit(self, x, y, hover):
        if not self.visible or self.disabled or not self._contains(x,y):
            return None
        for child, (cx,cy,cw,ch) in reversed(list(self._clips.items())):
            if cx <= x < cx+cw and cy <= y < cy+ch:
                hit = child._hit_test_hover(x,y) if hover else child._hit_test(x,y)
                if hit is not None:
                    return hit
        return None

    def _hit_test(self,x,y):
        return self._hit(x,y,False)

    def _hit_test_hover(self,x,y):
        return self._hit(x,y,True)


class HorizontalFloatingToolbar(FloatingToolbar):
    pass


class VerticalFloatingToolbar(FloatingToolbar):
    def __init__(self, *items, **kwargs):
        super().__init__(*items, vertical=True, **kwargs)


class FloatingActionButtonMenuItem(ExpressiveButton):
    variant_bg = colors.Colors.PRIMARY_CONTAINER
    variant_fg = colors.Colors.ON_PRIMARY_CONTAINER
    variant_elevation = 6

    def __init__(self, content, *, icon=None, on_click=None, **base):
        self.on_action = on_click
        self._menu = None
        super().__init__(content, icon=icon, size='medium', on_click=self._activate, **base)

    def _activate(self, _event=None):
        if self._menu is not None:
            self._menu.close()
            fire(self._menu, 'select', self)
        fire(self, 'action')


class _MenuFab(FloatingActionButton):
    def __init__(self, owner, icon):
        self.owner = owner
        super().__init__(icon, on_click=lambda _: owner.toggle())

    def _metrics(self):
        side, radius, icon, *rest = super()._metrics()
        p = self.owner._reveal
        return side, radius+(28-radius)*p, icon+(20-icon)*p, *rest


class _FabMenuOverlay(Control):
    _overlay_fill = True

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.list = ListView(controls=owner.items, spacing=4, padding=20)
        self.on_click = lambda _: owner.close()

    def _children(self):
        return [self.list]

    def _place(self,x,y,w,h,scale):
        self._rect = x,y,w,h
        ax,ay,aw,ah = self.owner._anchor
        width = min(max((c._intrinsic(None,None,scale)[0] for c in self.owner.items),default=56)+40,max(0,w-16))
        desired = len(self.owner.items)*60+36
        above = max(0,ay-8)
        below = max(0,h-ay-ah-8)
        height = min(desired,max(above,below))
        top = ay-height+12 if above >= below else ay+ah-12
        top = max(0,min(h-height,top))
        left = max(8,min(w-width-8,ax+aw+20-width))
        self.list._place(left,top,width,height,scale)

    def _draw_all(self,r,ox=0,oy=0):
        owner = self.owner
        if not owner.visible:
            return
        r.overlay_rect(*self._rect, (0,0,0,round(64*owner._reveal)))
        r.opacity_push(owner._reveal)
        self.list._draw_all(r)
        r.opacity_pop()
        owner.fab._draw_all(r,*owner._paint_offset)

    def _hit_test(self,x,y):
        owner = self.owner
        if not owner.visible or owner.disabled:
            return None
        if not owner.expanded:
            return self
        ax,ay,aw,ah = owner._anchor
        if ax <= x < ax+aw and ay <= y < ay+ah:
            return owner.fab
        return self.list._hit_test(x,y) or self

    def _hit_test_hover(self,x,y):
        if not self.owner.visible or self.owner.disabled:
            return None
        if not self.owner.expanded:
            return self
        ax,ay,aw,ah = self.owner._anchor
        if ax <= x < ax+aw and ay <= y < ay+ah:
            return self.owner.fab
        return self.list._hit_test_hover(x,y) or self

    def handle_event(self,event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.owner.close()
            return True
        return False


class FloatingActionButtonMenu(Control):
    """An anchored FAB with scrollable actions. Outside click or Escape closes it."""
    def __init__(self, items=None, *, icon=Icons.ADD, expanded=False, on_select=None, **base):
        super().__init__(**base)
        self.items = list(items or [])
        if not all(isinstance(c,FloatingActionButtonMenuItem) for c in self.items):
            raise TypeError('items must be FloatingActionButtonMenuItem instances')
        for item in self.items:
            item._menu = self
        self.icon, self.expanded, self.on_select = icon, bool(expanded), on_select
        self._last_expanded = False
        self._reveal = 0.0
        self._overlay = None
        self._anchor = (0,0,56,56)
        self._paint_offset = (0,0)
        self.fab = _MenuFab(self,icon)

    def _children(self):
        return [self.fab]

    def _intrinsic(self,max_w,max_h,scale):
        return self._width if self._width is not None else 56, self._height if self._height is not None else 56

    def _place(self,x,y,w,h,scale):
        self._rect = self._anchor = (x,y,w,h)
        self.fab.disabled = self.disabled
        self.fab._place(x,y,w,h,scale)

    def toggle(self):
        self.expanded = not self.expanded
        self.update()

    def close(self):
        self.expanded = False
        self.update()

    def _prepare_animations(self,now):
        super()._prepare_animations(now)
        if self.page is None:
            return
        if self.expanded and self._overlay is None:
            self._overlay = _FabMenuOverlay(self)
            self._overlay._attach(self.page,self)
            self.page.overlay.append(self._overlay)
        if self.expanded != self._last_expanded:
            self._last_expanded = self.expanded
            self.fab.icon = Icons.CLOSE if self.expanded else self.icon
            self._animate_internal('_reveal',float(self.expanded),motion.MEDIUM1,
                                   motion.EMPHASIZED,now=now)

    def _tick_animations(self,now):
        if self.expanded and (not self.visible or self.disabled):
            self.expanded = False
            self._prepare_animations(now)
        active = super()._tick_animations(now)
        if not self.expanded and self._reveal <= 0 and self._overlay is not None:
            if self._overlay in self.page.overlay:
                self.page.overlay.remove(self._overlay)
            self._overlay = None
        return active

    def _draw_all(self,r,ox=0,oy=0):
        self._paint_offset = ox,oy
        x,y,w,h = self._rect
        self._anchor = x+ox,y+oy,w,h
        if self._overlay is None:
            super()._draw_all(r,ox,oy)
