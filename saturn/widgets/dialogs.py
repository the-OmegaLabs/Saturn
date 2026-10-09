"""Dialogs: AlertDialog, SnackBar, DialogControl base.

Usage:
    page.show_dialog(ft.AlertDialog(title=..., content=..., actions=[...]))
    page.pop_dialog()
    snack = ft.SnackBar(ft.Text("saved")); page.show_dialog(snack)
"""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Unpack

import threading

from .. import colors, motion
from .. import text as txt
from ..control import Control, ControlOptions
from ..event import fire
from ..types import AnimationCurve, as_padding, Alignment, MainAxisAlignment
from .containers import Container, Row
from ._compat import value, reject_options, shape_radius
from ..painting import draw_shadow
from .text import Text

_SCRIM = (0, 0, 0, 82)
_DIALOG_PAD = 24.0


class DialogControl(Control):
    """Base: fills the page as an overlay; card area is interactive."""

    _overlay_fill = True
    _barrier = True  # clicks outside the card dismiss and are swallowed

    def __init__(self, *, open: bool = False, modal: bool = False,
                 on_dismiss=None, **base: Unpack[ControlOptions]):
        super().__init__(**base)
        self.open = bool(open)
        self.modal = modal
        self.on_dismiss = on_dismiss
        self._card_rect = (0.0, 0.0, 0.0, 0.0)

    # barrier handling -----------------------------------------------------
    def _interactive_rect(self):
        return self._card_rect

    def _hit_test(self, x, y):
        if not self.visible:
            return None
        cx, cy, cw, ch = self._interactive_rect()
        if cx <= x < cx + cw and cy <= y < cy + ch:
            hit = super()._hit_test(x, y)
            return hit if hit is not None and hit is not self else self
        # barrier click: dismiss (unless modal) and swallow the event;
        # non-barrier dialogs (SnackBar) let the page handle it
        if self._barrier:
            if not self.modal:
                self._dismiss()
            return self
        return None

    def _hit_test_hover(self, x, y):
        return None

    def _dismiss(self):
        if self.page is not None:
            self.page.pop_dialog(self)

    def _closed(self):
        self.open = False
        fire(self, "dismiss")


class AlertDialog(DialogControl):
    def __init__(self, title=None, content=None, *, actions=None, modal=False,
                 bgcolor=None, open=False, on_dismiss=None, elevation=None,
                 icon=None, title_padding=None, content_padding=None, actions_padding=None,
                 actions_alignment=None, shape=None, inset_padding=None, icon_padding=None,
                 action_button_padding=None, shadow_color=None, icon_color=None,
                 scrollable=False, actions_overflow_button_spacing=None, alignment=None,
                 content_text_style=None, title_text_style=None, clip_behavior="none",
                 semantics_label=None, barrier_color=None, **base: Unpack[ControlOptions]):
        reject_options("AlertDialog",content_text_style=content_text_style,shadow_color=shadow_color)
        if isinstance(content,str):
            content = Text(content)
        super().__init__(open=open, modal=modal, on_dismiss=on_dismiss, **base)
        self.title = title          # str | Control
        self.content = content      # Control
        self.actions = list(actions or [])
        self.bgcolor = bgcolor
        self.elevation = 6 if elevation is None else elevation
        self.icon = icon
        self.title_padding = 24 if title_padding is None else title_padding
        self.content_padding = 24 if content_padding is None else content_padding
        self.actions_padding = as_padding(24 if actions_padding is None else actions_padding)
        self.actions_alignment = actions_alignment or MainAxisAlignment.END
        self.shape = shape
        self.inset_padding = as_padding(40 if inset_padding is None else inset_padding)
        self.icon_padding = 24 if icon_padding is None else icon_padding
        self.action_button_padding = action_button_padding
        self.icon_color = icon_color
        self.scrollable = scrollable
        self.actions_overflow_button_spacing = actions_overflow_button_spacing or 8
        self.alignment = alignment or Alignment.CENTER
        self.title_text_style = title_text_style
        self.clip_behavior = clip_behavior
        self.semantics_label = semantics_label
        self.barrier_color = barrier_color
        self._icon_control = None
        self._content_view = None
        self._reveal = 0.0
        self._timeline = 0.0
        self._dismissing = False
        self._dismiss_timer = None

    def _attach(self, page, parent=None):
        super()._attach(page, parent)
        for c in self._dialog_children():
            c._attach(page, self)

    def _children(self):
        return self._dialog_children()

    def _dialog_children(self):
        out = []
        if isinstance(self.icon,Control):
            out.append(self.icon)
        elif self._icon_control is not None:
            out.append(self._icon_control)
        if isinstance(self.title, Control):
            out.append(self.title)
        if self.content is not None:
            out.append(self._content_view or self.content)
        out += self.actions
        return out

    def _title_text(self) -> str:
        return self.title if isinstance(self.title, str) else ""

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        inset = self.inset_padding
        available_w,available_h = max(0,w-inset.left-inset.right),max(0,h-inset.top-inset.bottom)
        tp,cp,ip,ap = as_padding(self.title_padding),as_padding(self.content_padding),as_padding(self.icon_padding),as_padding(self.actions_padding)
        if self.icon is not None and not isinstance(self.icon,Control):
            from .basic import Icon
            self._icon_control = Icon(self.icon,color=self.icon_color or colors.Colors.SECONDARY)
            if self.page:
                self._icon_control._attach(self.page,self)
        ic = self.icon if isinstance(self.icon,Control) else self._icon_control
        iw,ih = ic._intrinsic(available_w,available_h,scale) if ic else (0,0)
        style = self.title_text_style
        title_size = getattr(style,"size",None) or 24
        tw = th = 0.0
        if self._title_text():
            tw = txt.line_width(self._title_text(), title_size, scale=scale, bold=True)
            th = txt.line_height(title_size, scale=scale, bold=True)
        elif isinstance(self.title, Control):
            tw, th = self.title._intrinsic(w, h, scale)
        cw = ch = 0.0
        if self.content is not None:
            cw, ch = self.content._intrinsic(max(0,available_w-cp.left-cp.right), None, scale)
        aw = sum(a._intrinsic(w, h, scale)[0] for a in self.actions)
        aw += 8.0 * max(0, len(self.actions) - 1)
        ah = max((a._intrinsic(w, h, scale)[1] for a in self.actions), default=0.0)
        card_w = min(available_w,max(280,tw+tp.left+tp.right,cw+cp.left+cp.right,aw+ap.left+ap.right,iw+ip.left+ip.right))
        action_controls = ([Container(action,padding=self.action_button_padding) for action in self.actions]
                           if self.action_button_padding is not None else self.actions)
        action_row = Row(controls=action_controls,wrap=True,tight=True,alignment=self.actions_alignment,
                         run_spacing=self.actions_overflow_button_spacing,spacing=8)
        _,ah = action_row._intrinsic(max(0,card_w-ap.left-ap.right),None,scale)
        fixed_h = (ih+ip.top+ip.bottom if ic else 0)+(th+tp.top+tp.bottom if th else 0)+(ah+ap.top+ap.bottom if ah else 0)
        if self.content is not None:
            cw,ch = self.content._intrinsic(max(0,card_w-cp.left-cp.right),None,scale)
            ch = min(ch,max(0,available_h-fixed_h-cp.top-cp.bottom))
        card_h = min(available_h,fixed_h+(ch+cp.top+cp.bottom if self.content else 0))
        cx = x+inset.left+(available_w-card_w)*(self.alignment.x+1)/2
        cy = y+inset.top+(available_h-card_h)*(self.alignment.y+1)/2
        self._card_rect = (cx, cy, card_w, card_h)
        # place children inside the card
        py = cy
        if ic:
            ic._place(cx+(card_w-iw)/2,py+ip.top,iw,ih,scale)
            py += ip.top+ih+ip.bottom
        px = cx+tp.left
        inner_w = max(0,card_w-tp.left-tp.right)
        if isinstance(self.title, Control):
            self.title._place(px, py+tp.top, inner_w, th, scale)
            py += tp.top+th+tp.bottom
        elif self._title_text():
            self._title_rect = (px,py+tp.top,inner_w,th)
            py += tp.top+th+tp.bottom
        if self.content is not None:
            host = self.content
            if self.scrollable:
                from .scrolling import ListView
                if self._content_view is None:
                    self._content_view = ListView(controls=[self.content],scroll="auto")
                    if self.page:
                        self._content_view._attach(self.page,self)
                host = self._content_view
            host._place(cx+cp.left,py+cp.top,max(0,card_w-cp.left-cp.right),ch,scale)
            py += cp.top+ch+cp.bottom
        action_row._place(cx+ap.left,py+ap.top,max(0,card_w-ap.left-ap.right),ah,scale)

    def _draw(self, r, x, y):
        pass

    def _draw_all(self, r):
        if not self.visible:
            return
        self._effects_begin(r)
        try:
            base_scrim = colors.parse_color(self.barrier_color) if self.barrier_color else _SCRIM
            scrim = (*base_scrim[:3],round(base_scrim[3]*self._timeline))
            r.overlay_rect(*self._rect[:2], self._rect[2], self._rect[3], scrim)
            cx, cy, cw, ch = self._card_rect
            dy = -50.0 * (1.0 - self._reveal)
            visible_h = ch * (0.35 + 0.65 * self._reveal)
            if self._dismissing:
                card_alpha = min(1.0, self._timeline * 3.0)
                content_alpha = max(
                    0.0, min(1.0, (self._timeline - 1 / 3) / (2 / 3)))
                action_alpha = content_alpha
            else:
                card_alpha = min(1.0, self._timeline * 10.0)
                content_alpha = max(
                    0.0, min(1.0, (self._timeline - 0.1) / 0.4))
                action_alpha = max(
                    0.0, min(1.0, (self._timeline - 0.3) / 0.3))
            r.translate_push(0, dy)
            r.opacity_push(card_alpha)
            radius = shape_radius(self.shape,cw,ch,28)
            draw_shadow(r,(cx,cy,cw,visible_h),radius,self.elevation)
            r.fill_rect(cx, cy, cw, visible_h,
                        colors.parse_color(
                            self.bgcolor or colors.Colors.SURFACE_CONTAINER_HIGH),
                        radius=radius)
            r.opacity_pop()
            r.clip_push(cx, cy, cw, visible_h)
            r.opacity_push(content_alpha)
            ic = self.icon if isinstance(self.icon,Control) else self._icon_control
            if ic:
                ic._draw_all(r)
            if isinstance(self.title, str) and self.title:
                r.blit_cached(txt.render_line_cached(
                    self.title,getattr(self.title_text_style,"size",None) or 24,scale=r.scale,bold=True,
                    color=colors.parse_color(getattr(self.title_text_style,"color",None) or colors.Colors.ON_SURFACE)),
                    self._title_rect[0], self._title_rect[1])
            elif isinstance(self.title, Control):
                self.title._draw_all(r)
            if self.content is not None:
                (self._content_view or self.content)._draw_all(r)
            r.opacity_pop()
            r.opacity_push(action_alpha)
            for action in self.actions:
                action._draw_all(r)
            r.opacity_pop()
            r.clip_pop()
            r.translate_pop()
        finally:
            self._effects_end(r)

    def _shown(self):
        self._dismissing = False
        self._reveal = 0.0
        self._timeline = 0.0
        self._animation_targets["_reveal"] = 0.0
        self._animation_targets["_timeline"] = 0.0
        self._animate_internal("_reveal", 1.0, motion.MEDIUM2,
                               motion.EMPHASIZED)
        self._animate_internal("_timeline", 1.0, motion.MEDIUM2,
                               AnimationCurve.LINEAR)

    def _begin_dismiss(self, page):
        if self._dismissing:
            return True
        self._dismissing = True
        self._animate_internal("_reveal", 0.35, motion.SHORT3,
                               motion.EMPHASIZED_ACCELERATE)
        self._animate_internal("_timeline", 0.0, motion.SHORT3,
                               AnimationCurve.LINEAR)
        self._dismiss_timer = threading.Timer(
            motion.SHORT3 / 1000.0, lambda: page._finish_pop_dialog(self))
        self._dismiss_timer.daemon = True
        self._dismiss_timer.start()
        return True

    def _closed(self):
        if self._dismiss_timer is not None:
            self._dismiss_timer.cancel()
        super()._closed()

    __unsupported_parameters__ = {"content_text_style", "shadow_color"}


class SnackBar(DialogControl):
    # a SnackBar is a notice, not a modal barrier — page stays live
    _barrier = False

    def __init__(self, content, *, action=None, bgcolor=None, duration: int = 4000,
                 on_action=None, open=False, on_dismiss=None, behavior=None,
                 dismiss_direction=None, show_close_icon=False, close_icon_color=None,
                 margin=None, padding=None, width=None, elevation=None, shape=None,
                 clip_behavior="hardEdge", action_overflow_threshold=.25,
                 persist=None, on_visible=None, **base: Unpack[ControlOptions]):
        reject_options("SnackBar",dismiss_direction=dismiss_direction)
        super().__init__(open=open, on_dismiss=on_dismiss, **base)
        self.content = content      # str | Control
        self.action = action        # str label
        self.bgcolor = bgcolor
        self.duration = duration
        self.on_action = on_action
        self.behavior = behavior
        self.show_close_icon = show_close_icon
        self.close_icon_color = close_icon_color
        self.margin = as_padding(16 if value(behavior) == "floating" and margin is None else margin)
        self.padding = as_padding(24 if padding is None else padding)
        self._width = width
        self.elevation = 6 if elevation is None else elevation
        self.shape = shape
        self.clip_behavior = clip_behavior
        self.action_overflow_threshold = action_overflow_threshold
        self.persist = persist
        self.on_visible = on_visible
        self._close_control = None
        self._action_key = None
        self._timer = None
        self._dismiss_timer = None
        self._dismissing = False
        self._reveal = 0.0

    def _attach(self, page, parent=None):
        super()._attach(page, parent)
        if isinstance(self.content, Control):
            self.content._attach(page, self)
        if self._action_btn is not None:
            self._action_btn._attach(page, self)

    @property
    def _action_btn(self):
        return getattr(self, "_action_control", None)

    def _children(self):
        out = []
        if isinstance(self.content, Control):
            out.append(self.content)
        if self._action_btn is not None:
            out.append(self._action_btn)
        if self._close_control is not None:
            out.append(self._close_control)
        return out

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        p,m = self.padding,self.margin
        bar_w = min(w-m.left-m.right,self._width or w-m.left-m.right)
        cw = ch = 0.0
        if isinstance(self.content, Control):
            cw, ch = self.content._intrinsic(max(0,bar_w-p.left-p.right),h,scale)
        else:
            cw, ch = txt.measure(str(self.content), 14, scale=scale)
        action_w = 0.0
        if self.action:
            from .buttons import TextButton
            label = self.action if isinstance(self.action,str) else getattr(self.action,"label",str(self.action))
            action_key = (label,getattr(self.action,"text_color",None))
            if self._action_key != action_key:
                self._action_control = TextButton(label,on_click=self._on_action,color=action_key[1])
                self._action_key = action_key
            action_w = self._action_control._intrinsic(w, h, scale)[0] + 16
            if self.page:
                self._action_control._attach(self.page,self)
        else:
            self._action_control = None
        if self.show_close_icon:
            from .buttons import IconButton
            from .._gen.icons import Icons
            if self._close_control is None:
                self._close_control = IconButton(Icons.CLOSE,on_click=lambda _: self._dismiss())
            self._close_control.icon_color = self.close_icon_color
            if self.page:
                self._close_control._attach(self.page,self)
        else:
            self._close_control = None
        close_w = 40 if self._close_control else 0
        overflow = bool(self.action and action_w > max(0,bar_w)*self.action_overflow_threshold)
        content_width = max(0,bar_w-p.left-p.right-close_w-(0 if overflow else action_w))
        if isinstance(self.content,Control):
            cw,ch = self.content._intrinsic(content_width,None,scale)
        bar_h = max(48,ch+p.top+p.bottom)+(40 if overflow else 0)
        bx = x+m.left+(w-m.left-m.right-bar_w)/2
        self._bar_rect = (bx,y+h-m.bottom-bar_h,bar_w,bar_h)
        if isinstance(self.content, Control):
            self.content._place(bx+p.left,self._bar_rect[1]+p.top,content_width,ch,scale)
        else:
            self._text_position = (bx+p.left,self._bar_rect[1]+p.top)
        if self.action:
            ab = self._action_control
            aw, ah = ab._intrinsic(bar_w, bar_h, scale)
            ab._place(bx+bar_w-aw-p.right-close_w,
                      self._bar_rect[1]+bar_h-ah-p.bottom if overflow else self._bar_rect[1]+(bar_h-ah)/2,aw,ah,scale)
        if self._close_control:
            self._close_control._place(bx+bar_w-p.right-40,self._bar_rect[1]+(bar_h-40)/2,40,40,scale)

    def _draw(self, r, x, y):
        bx, by, bw, bh = self._bar_rect
        radius = shape_radius(self.shape,bw,bh,4 if value(self.behavior) == "floating" else 0)
        draw_shadow(r,self._bar_rect,radius,self.elevation)
        r.fill_rect(bx, by, bw, bh,
                    colors.parse_color(self.bgcolor or
                                       colors.Colors.INVERSE_SURFACE),
                    radius=radius)
        if isinstance(self.content, str):
            r.blit_cached(txt.render_line_cached(
                   str(self.content), 14, scale=r.scale,
                   color=colors.parse_color(colors.Colors.ON_INVERSE_SURFACE)),
                   *self._text_position)

    def _interactive_rect(self):
        return self._bar_rect

    def _draw_all(self, r):
        if not self.visible:
            return
        r.translate_push(0, (1.0 - self._reveal) * 48.0)
        r.opacity_push(min(1.0, self._reveal * 4.0))
        self._effects_begin(r)
        try:
            self._draw(r, *self._rect[:2])
            for c in self._children():
                c._draw_all(r)
        finally:
            self._effects_end(r)
            r.opacity_pop()
            r.translate_pop()

    def _shown(self):
        fire(self,"visible")
        self._dismissing = False
        self._reveal = 0.0
        self._animation_targets["_reveal"] = 0.0
        self._animate_internal("_reveal", 1.0, motion.MEDIUM1,
                               motion.STANDARD)

    def _begin_dismiss(self, page):
        if self._dismissing:
            return True
        self._dismissing = True
        self._animate_internal("_reveal", 0.0, motion.SHORT4,
                               motion.STANDARD_ACCELERATE)
        self._dismiss_timer = threading.Timer(
            motion.SHORT4 / 1000.0, lambda: page._finish_pop_dialog(self))
        self._dismiss_timer.daemon = True
        self._dismiss_timer.start()
        return True

    def _closed(self):
        if self._timer is not None:
            self._timer.cancel()
        if self._dismiss_timer is not None:
            self._dismiss_timer.cancel()
        super()._closed()

    def _on_action(self, e=None):
        fire(self, "action")
        handler = getattr(self.action,"on_click",None)
        if handler and self.page:
            from ..event import _invoke,ControlEvent
            self.page._app.call(_invoke,handler,ControlEvent("action",self))
        self._dismiss()

    def _start_timer(self, page):
        duration = getattr(self.duration,"in_milliseconds",self.duration)
        if self.persist is True or (self.persist is None and self.action):
            return
        if duration and duration > 0:
            self._timer = threading.Timer(
                duration / 1000.0,
                lambda: page.pop_dialog(self) if self in page.overlay else None)
            self._timer.daemon = True
            self._timer.start()

    __unsupported_parameters__ = {"dismiss_direction"}
