"""PopupMenuButton: a button that opens a Material menu overlay.

The menu surface lives in page.overlay (like Dropdown's menu) and acts as a
modal barrier: clicks on the item rows select, any other click closes the
menu instead of reaching the controls underneath.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Unpack

import time

from .. import colors, motion
from .._gen.icons import Icons
from ..control import Control, ControlOptions
from ..event import fire
from ..painting import draw_shadow
from ..types import Alignment, AnimationCurve, Padding, as_padding
from ._compat import value
from ._material import (draw_state_layer, init_state_layer, press, release,
                        set_hover, tick_state_layer)
from ..text import render_icon_cached
from .basic import Icon
from .containers import Container, Row
from .text import Text

_ITEM_PAD = 12.0
_MIN_MENU_WIDTH = 112.0


class PopupMenuItem(Control):
    """One menu row: text or a custom content control plus optional icons."""

    def __init__(self, text=None, *, content=None, icon=None, leading=None,
                 trailing=None, height=None, on_click=None, disabled=False,
                 checked=None, **base: Unpack[ControlOptions]):
        super().__init__(**base)
        self.text = text
        self.content = content
        self.icon = icon
        self.leading = leading
        self.trailing = trailing
        self.height = 40 if height is None else float(height)
        self.on_click = on_click
        self.disabled = bool(disabled)
        self.checked = checked


class _PopupMenuSurface(Control):
    def __init__(self, owner, items, width, height):
        super().__init__()
        self.owner = owner
        self.items = items
        self._width = width
        self._height = height
        self.on_click = owner._barrier_click  # clicks that miss every row

    def _attach(self, page, parent=None):
        super()._attach(page, parent)
        for item in self.items:
            item._attach(page, self)

    def _children(self):
        return self.items

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        cursor = y
        for item in self.items:
            item._place(x, cursor, w, item.height, scale)
            cursor += item.height

    def _owner_available(self):
        return (self.page is not None and self.owner.page is self.page
                and self.page._control_enabled(self.owner))

    def _draw_all(self, r, ox=0.0, oy=0.0):
        progress = self.owner._menu_progress
        if progress <= 0.0 or not self.items or not self._owner_available():
            return
        x, y, w, full_h = self._rect
        visible_h = full_h * progress
        surface_alpha = min(1.0, self.owner._menu_timeline * 10.0)
        r.opacity_push(surface_alpha)
        draw_shadow(r, (x, y, w, visible_h), 4,
                    value(self.owner.elevation) or 8)
        r.fill_rect(x, y, w, visible_h,
                    colors.parse_color(colors.Colors.SURFACE_CONTAINER), radius=4)
        r.opacity_pop()
        r.clip_push(x, y, w, visible_h)
        count = len(self.items)
        for index, item in enumerate(self.items):
            if self.owner._menu_closing:
                elapsed_ms = (1.0 - self.owner._menu_timeline) * 150.0
                reverse_index = count - 1 - index
                delay_ms = 50.0 + 50.0 * reverse_index / count
                alpha = 1.0 - max(0.0, min(1.0, (elapsed_ms - delay_ms) / 50.0))
            else:
                delay = 0.5 * index / count
                alpha = max(0.0, min(1.0, (self.owner._menu_timeline - delay) / 0.5))
            if alpha <= 0.0:
                continue
            r.opacity_push(alpha)
            item._draw_all(r, ox, oy)
            r.opacity_pop()
        r.clip_pop()

    def _hit_test(self, x, y):
        if self.owner._menu_closing or not self._owner_available():
            return None
        if self._contains(x, y):
            return super()._hit_test(x, y)
        # Modal barrier: the click lands here instead of the page below and
        # closes the menu through on_click.
        return self

    def _hit_test_hover(self, x, y):
        if self.owner._menu_closing or not self._owner_available():
            return None
        if not self._contains(x, y):
            return None
        return super()._hit_test_hover(x, y)

    def _find_scrollable(self, x, y):
        return None


class PopupMenuButton(Control):
    """Material popup menu button (flet-compatible surface).

    Shows `content` (or an icon) and opens `items` in an overlay menu on
    click. width/height/padding/tooltip pass through the base control.
    """

    def __init__(self, items=None, *, content=None, icon=None, icon_color=None,
                 icon_size=None, width=None, height=None, padding=None,
                 tooltip=None, bgcolor=None, elevation=8, on_opened=None,
                 on_closed=None, **base: Unpack[ControlOptions]):
        base.setdefault("width", width)
        base.setdefault("height", height)
        super().__init__(tooltip=tooltip, **base)
        self.items = list(items or [])
        self.content = content
        self.icon = icon if content is None else None
        self.icon_color = icon_color
        self.icon_size = 24 if icon_size is None else float(icon_size)
        self.padding = padding
        self.bgcolor = bgcolor
        self.elevation = elevation
        self.on_opened = on_opened
        self.on_closed = on_closed
        self.open = False
        self._menu_closing = False
        self._menu_close_deadline = None
        self._menu_progress = 0.0
        self._menu_timeline = 0.0
        self._menu_surface = None
        self._menu = []
        self.on_click = self._toggle_menu  # internal routing, like Dropdown
        self._hovered = False
        self._pressed = False
        init_state_layer(self)

    # -- visual content ----------------------------------------------------
    def _children(self):
        return [self.content] if isinstance(self.content, Control) else []

    def _padding(self):
        return as_padding(self.padding) if self.padding is not None else as_padding(0)

    def _intrinsic(self, max_w, max_h, scale):
        if isinstance(self.content, Control):
            w, h = self.content._intrinsic(max_w, max_h, scale)
        else:
            w, h = self.icon_size + 16.0, self.icon_size + 16.0
        p = self._padding()
        w += p.left + p.right
        h += p.top + p.bottom
        return (self._width if self._width is not None else w,
                self._height if self._height is not None else h)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        if isinstance(self.content, Control):
            p = self._padding()
            cw, ch = self.content._intrinsic(w - p.left - p.right,
                                             h - p.top - p.bottom, scale)
            self.content._place(x + p.left + (w - p.left - p.right - cw) / 2,
                                y + p.top + (h - p.top - p.bottom - ch) / 2,
                                cw, ch, scale)
        if self.open:
            self._position_menu()

    def _draw(self, r, x, y):
        _, _, w, h = self._rect
        radius = min(w, h) / 2
        bg = value(self.bgcolor)
        if bg is not None:
            r.fill_rect(x, y, w, h, colors.parse_color(bg), radius=radius)
        if not self.disabled:
            draw_state_layer(self, r, (x, y, w, h),
                             colors.Colors.ON_SURFACE, radius)
        if isinstance(self.content, Control):
            self.content._draw_all(r, x - self._rect[0], y - self._rect[1])
        elif self.icon is not None:
            fg = colors.parse_color(self.icon_color or colors.Colors.ON_SURFACE_VARIANT)
            surf = render_icon_cached(self.icon, round(self.icon_size * r.scale), fg)
            r.blit_cached(surf, x + (w - surf.get_width() / r.scale) / 2,
                          y + (h - surf.get_height() / r.scale) / 2)

    def _draw_all(self, r, ox=0.0, oy=0.0):
        if not self.visible:
            return
        self._effects_begin(r, ox, oy)
        try:
            self._draw(r, self._rect[0] + ox, self._rect[1] + oy)
        finally:
            self._effects_end(r)

    # -- interaction ---------------------------------------------------------
    def _hit_test(self, x, y):
        x, y = self._hit_point(x, y)
        if not self.visible or self.disabled:
            return None
        return self if self._contains(x, y) else None

    def _hit_test_hover(self, x, y):
        return self._hit_test(x, y)

    def _set_hover(self, on: bool):
        set_hover(self, on)
        self.repaint()

    def _pressed_hook(self, x, y):
        press(self, x, y)

    def _released_hook(self, _x, _y):
        release(self)

    # -- menu plumbing (mirrors Dropdown) -------------------------------------
    def _toggle_menu(self, e=None):
        if self.open:
            self._close_menu()
            return
        self.open = True
        self._menu_closing = False
        self._menu_close_deadline = None
        page = self.page
        if page is not None and self._menu_surface is None:
            self._build_menu(page)
        self._animate_internal("_menu_progress", 1.0, motion.MEDIUM2,
                               motion.EMPHASIZED)
        self._animate_internal("_menu_timeline", 1.0, motion.MEDIUM2,
                               AnimationCurve.LINEAR)
        self.update()
        if self.on_opened is not None:
            fire(self, "opened")

    def _close_menu(self):
        if not self.open or self._menu_closing:
            return
        self.open = False
        self._menu_closing = True
        now = time.perf_counter()
        self._menu_close_deadline = now + motion.SHORT3 / 1000.0
        self._animate_internal("_menu_progress", 0.35, motion.SHORT3,
                               motion.EMPHASIZED_ACCELERATE, now=now)
        self._animate_internal("_menu_timeline", 0.0, motion.SHORT3,
                               AnimationCurve.LINEAR, now=now)
        self.update()
        if self.on_closed is not None:
            fire(self, "closed")

    def _finish_menu_close(self):
        page = self.page
        if page is not None and self._menu_surface in page.overlay:
            page.overlay.remove(self._menu_surface)
        self._menu = []
        self._menu_surface = None
        self._menu_closing = False
        self._menu_close_deadline = None
        self._menu_progress = 0.0
        self._menu_timeline = 0.0
        self._animation_targets["_menu_progress"] = 0.0
        self._animation_targets["_menu_timeline"] = 0.0

    def _tick_animations(self, now: float) -> bool:
        waiting = tick_state_layer(self, now)
        if self._menu_close_deadline is not None and now >= self._menu_close_deadline:
            self._finish_menu_close()
        closing = self._menu_close_deadline is not None
        return super()._tick_animations(now) or waiting or closing

    def _barrier_click(self, e=None):
        self._close_menu()

    def _pick_item(self, item):
        self._close_menu()
        self.update()
        # PopupMenuItem objects are data holders, never attached to the tree,
        # so their handlers go through page._dispatch instead of fire().
        if item.on_click is not None and not item.disabled and self.page is not None:
            self.page._dispatch(item.on_click)

    def _build_menu(self, page):
        width = max(_MIN_MENU_WIDTH, self._rect[2])
        for item in self.items:
            width = max(width, self._item_width(item))
        rows = [self._item_row(item) for item in self.items]
        height = sum(item.height for item in self.items)
        self._menu = rows
        self._menu_surface = _PopupMenuSurface(self, rows, width, height)
        self._menu_surface._attach(page, None)
        self._position_menu()
        page.overlay.append(self._menu_surface)

    def _item_width(self, item):
        needed = 2 * _ITEM_PAD
        content = item.content if item.content is not None else (
            Text(item.text) if item.text else None)
        if isinstance(content, Control):
            needed += content._intrinsic(None, None, 1.0)[0]
        for part in (item.leading, item.icon, item.trailing):
            if isinstance(part, Control):
                needed += part._intrinsic(None, None, 1.0)[0] + 12.0
            elif part is not None:
                needed += 24.0 + 12.0
        return needed

    def _item_row(self, item):
        leading = item.leading or item.icon
        children = []
        if isinstance(leading, Control):
            children.append(leading)
        elif leading is not None:
            children.append(Icon(leading, size=24,
                                 color=colors.Colors.ON_SURFACE_VARIANT))
        if item.content is not None:
            children.append(item.content)
        elif item.text is not None:
            color = (colors.with_opacity(0.38, colors.Colors.ON_SURFACE)
                     if item.disabled else colors.Colors.ON_SURFACE)
            children.append(Text(item.text, color=color))
        if item.checked or item.trailing is not None:
            children.append(item.trailing if isinstance(item.trailing, Control)
                            else Icon(item.trailing or Icons.CHECK, size=24,
                                      color=colors.Colors.ON_SURFACE))
        return Container(Row(*children, spacing=12),
                         height=item.height,
                         padding=Padding(_ITEM_PAD, 0, _ITEM_PAD, 0),
                         alignment=Alignment.CENTER_LEFT, border_radius=4,
                         ink=True, disabled=item.disabled,
                         on_click=lambda event=None, selected=item: self._pick_item(selected))

    def _position_menu(self):
        if self._menu_surface is None or self.page is None:
            return
        x, y, w, h = self._rect
        corners = [self._screen_point(px, py) for px, py in
                   ((x, y), (x + w, y), (x, y + h), (x + w, y + h))]
        anchor_left = min(px for px, _ in corners)
        anchor_top = min(py for _, py in corners)
        anchor_bottom = max(py for _, py in corners)
        width = self._menu_surface._width
        height = min(self._menu_surface._height,
                     max(0, self.page.height - 8))
        left = min(max(0, anchor_left), max(0, self.page.width - width))
        top = anchor_bottom + 4
        if top + height > self.page.height:
            top = max(0, anchor_top - height - 4)
        self._menu_surface._height = height
        self._menu_surface._place(left, top, width, height,
                                  self.page._app.renderer.scale)
