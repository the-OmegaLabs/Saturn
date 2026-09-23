"""Dialogs: AlertDialog, SnackBar, DialogControl base.

Usage (flet 1.0):
    page.show_dialog(ft.AlertDialog(title=..., content=..., actions=[...]))
    page.pop_dialog()
    snack = ft.SnackBar(ft.Text("saved")); page.show_dialog(snack)
"""
from __future__ import annotations

import threading

from .. import colors, motion
from .. import text as txt
from ..control import Control
from ..event import fire
from ..types import AnimationCurve
from .containers import Container
from .text import Text

_SCRIM = (0, 0, 0, 82)
_DIALOG_PAD = 24.0


class DialogControl(Control):
    """Base: fills the page as an overlay; card area is interactive."""

    _overlay_fill = True
    _barrier = True  # clicks outside the card dismiss and are swallowed

    def __init__(self, *, open: bool = False, modal: bool = False,
                 on_dismiss=None, **base):
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
                 bgcolor=None, open=False, on_dismiss=None, **base):
        super().__init__(open=open, modal=modal, on_dismiss=on_dismiss, **base)
        self.title = title          # str | Control
        self.content = content      # Control
        self.actions = list(actions or [])
        self.bgcolor = bgcolor
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
        if isinstance(self.title, Control):
            out.append(self.title)
        if self.content is not None:
            out.append(self.content)
        out += self.actions
        return out

    def _title_text(self) -> str:
        return self.title if isinstance(self.title, str) else ""

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        # measure the card
        tw = th = 0.0
        if self._title_text():
            tw = txt.line_width(self._title_text(), 24, scale=scale, bold=True)
            th = txt.line_height(24, scale=scale, bold=True)
        elif isinstance(self.title, Control):
            tw, th = self.title._intrinsic(w, h, scale)
        cw = ch = 0.0
        if self.content is not None:
            cw, ch = self.content._intrinsic(w - 2 * _DIALOG_PAD, h, scale)
        aw = sum(a._intrinsic(w, h, scale)[0] for a in self.actions)
        aw += 8.0 * max(0, len(self.actions) - 1)
        ah = max((a._intrinsic(w, h, scale)[1] for a in self.actions), default=0.0)
        card_w = max(tw, cw, aw) + 2 * _DIALOG_PAD
        card_h = (_DIALOG_PAD if th or cw else _DIALOG_PAD * 0.6) + th + \
            (12.0 if th and ch else 0) + ch + \
            (16.0 if ah else 0) + ah + _DIALOG_PAD
        card_w = min(card_w, w * 0.9)
        cx = x + (w - card_w) / 2
        cy = y + (h - card_h) / 2
        self._card_rect = (cx, cy, card_w, card_h)
        # place children inside the card
        py = cy + _DIALOG_PAD
        px = cx + _DIALOG_PAD
        inner_w = card_w - 2 * _DIALOG_PAD
        if isinstance(self.title, Control):
            self.title._place(px, py, inner_w, th, scale)
            py += th + 12.0
        elif self._title_text():
            self._title_rect = (px, py, inner_w, th)
            py += th + 12.0
        if self.content is not None:
            self.content._place(px, py, inner_w, ch, scale)
            py += ch + 16.0
        ax = px
        for a in self.actions:
            aw2, ah2 = a._intrinsic(inner_w, ah, scale)
            a._place(ax, py, aw2, ah2, scale)
            ax += aw2 + 8.0

    def _draw(self, r, x, y):
        pass

    def _draw_all(self, r):
        if not self.visible:
            return
        self._effects_begin(r)
        try:
            scrim = (*_SCRIM[:3], round(_SCRIM[3] * self._timeline))
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
            r.fill_rect(cx, cy, cw, visible_h,
                        colors.parse_color(
                            self.bgcolor or colors.Colors.SURFACE_CONTAINER_HIGH),
                        radius=28)
            r.opacity_pop()
            r.clip_push(cx, cy, cw, visible_h)
            r.opacity_push(content_alpha)
            if isinstance(self.title, str) and self.title:
                r.blit_cached(txt.render_line_cached(
                    self.title, 24, scale=r.scale, bold=True,
                    color=colors.parse_color(colors.Colors.ON_SURFACE)),
                    self._title_rect[0], self._title_rect[1])
            elif isinstance(self.title, Control):
                self.title._draw_all(r)
            if self.content is not None:
                self.content._draw_all(r)
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


class SnackBar(DialogControl):
    # flet: a SnackBar is a notice, not a modal barrier — page stays live
    _barrier = False

    def __init__(self, content, *, action=None, bgcolor=None, duration: int = 4000,
                 on_action=None, open=False, on_dismiss=None, **base):
        super().__init__(open=open, on_dismiss=on_dismiss, **base)
        self.content = content      # str | Control
        self.action = action        # str label
        self.bgcolor = bgcolor
        self.duration = duration
        self.on_action = on_action
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
        return out

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        cw = ch = 0.0
        if isinstance(self.content, Control):
            cw, ch = self.content._intrinsic(w, h, scale)
        else:
            cw, ch = txt.measure(str(self.content), 14, scale=scale)
        action_w = 0.0
        if self.action:
            from .buttons import TextButton
            self._action_control = TextButton(
                self.action, on_click=self._on_action)
            action_w = self._action_control._intrinsic(w, h, scale)[0] + 16
            self._action_control._attach(self.page, self)
        # Flet's default SnackBarBehavior is FIXED: a full-width, square
        # bar flush with the bottom edge. Floating/margined styling requires
        # explicit behavior/margin properties and is not the default.
        bar_w = w
        bar_h = 48.0
        self._bar_rect = (x, y + h - bar_h, bar_w, bar_h)
        if isinstance(self.content, Control):
            self.content._place(self._bar_rect[0] + 24,
                                self._bar_rect[1] + (bar_h - ch) / 2, cw, ch, scale)
        if self.action:
            ab = self._action_control
            aw, ah = ab._intrinsic(bar_w, bar_h, scale)
            ab._place(self._bar_rect[0] + bar_w - aw - 24,
                      self._bar_rect[1] + (bar_h - ah) / 2, aw, ah, scale)

    def _draw(self, r, x, y):
        bx, by, bw, bh = self._bar_rect
        r.fill_rect(bx, by, bw, bh,
                    colors.parse_color(self.bgcolor or
                                       colors.Colors.INVERSE_SURFACE),
                    radius=0)
        if isinstance(self.content, str):
            r.blit_cached(txt.render_line_cached(
                   str(self.content), 14, scale=r.scale,
                   color=colors.parse_color(colors.Colors.ON_INVERSE_SURFACE)),
                   bx + 24, by + (bh - 20) / 2)

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
        self._dismiss()

    def _start_timer(self, page):
        if self.duration and self.duration > 0:
            self._timer = threading.Timer(
                self.duration / 1000.0,
                lambda: page.pop_dialog(self) if self in page.overlay else None)
            self._timer.daemon = True
            self._timer.start()
