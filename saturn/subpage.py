"""Owned native windows, comparable to tkinter.Toplevel."""
from __future__ import annotations

import ctypes
import sys
from .app import App
from .page import Page
from .types import Alignment, Offset


class Subpage(Page):
    """Independent native child window with its own Page and renderer.

    Creation is queued on the UI thread. Configure the returned Page
    immediately; ``main(subpage)`` runs after native creation. Closing the
    parent closes descendants; closing a child leaves the parent running.
    """

    def __init__(self, parent: Page, *, main=None, title="Settings", modal=False,
                 anchor="center", offset=None, follow_parent=False, backend=None, gpu=None):
        if not isinstance(parent, Page):
            raise TypeError("parent must be a Page")
        if parent._app._closed.is_set():
            raise RuntimeError("Cannot create a child of a closed window")
        if main is not None and not callable(main):
            raise TypeError("main must be callable")
        self._validate_attachment(anchor, offset)
        self.parent_page = parent
        self.modal = bool(modal)
        self._anchor = anchor
        self._attachment_offset = offset or Offset()
        self.follow_parent = bool(follow_parent)
        self._attachment_key = None
        self._error = None
        app = App(main or (lambda page: None), backend or parent._app._backend,
                  title=title, gpu=(parent._app._gpu if gpu is None and
                      (backend is None or backend is parent._app._backend) else gpu),
                  _parent_app=parent._app)
        super().__init__(app)
        app.page = self
        self._theme_mode = parent.theme_mode
        self._theme, self._dark_theme = parent.theme, parent.dark_theme
        self._fonts = dict(parent.fonts)
        self._theme_key = None
        self._apply_theme()
        parent._app._children.append(app)
        def create():
            if app._closed.is_set() or parent._app._closed.is_set():
                app.close()
                return
            try:
                app.start()
                app._drain_commands()
                self._set_owner()
                self._sync_attachment(force=True)
                if self.window._values.get("visible", True):
                    app._window.show()
                parent._app._activate()
            except Exception as error:
                self._error = error
                app.close()
                app._dispose()
                raise
        parent._app.post(create)

    @property
    def ready(self):
        return self._app._window is not None and not self.closed

    @property
    def closed(self):
        return self._app._closed.is_set()

    @property
    def creation_error(self):
        return self._error

    def _set_owner(self):
        if sys.platform == "win32":
            user = ctypes.windll.user32
            setter = user.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user.SetWindowLongW
            setter.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
            setter.restype = ctypes.c_void_p
            setter(self.window.hwnd, -8, self.parent_page.window.hwnd)
            if self.modal:
                user.EnableWindow(ctypes.c_void_p(self.parent_page.window.hwnd), False)
        elif self.modal:
            self._app._window.set_modal_for(self.parent_page._app._window)

    def attach(self, anchor="center", *, offset=None, follow_parent=False):
        """Place relative to the owner's outer window; optionally follow it."""
        self._validate_attachment(anchor, offset)
        self._anchor = anchor
        self._attachment_offset = offset or Offset()
        self.follow_parent = bool(follow_parent)
        self._attachment_key = None
        self._app.post(lambda: self._sync_attachment(force=True))

    @staticmethod
    def _validate_attachment(anchor, offset):
        import math
        if not isinstance(anchor, Alignment) and anchor not in (
                "center", "left", "right", "top", "bottom", "top_left",
                "top_right", "bottom_left", "bottom_right"):
            raise ValueError(f"Unknown child-window anchor: {anchor!r}")
        if offset is not None:
            values = offset if isinstance(offset, tuple) else (offset.x, offset.y)
            if len(values) != 2 or not all(math.isfinite(float(v)) for v in values):
                raise ValueError("offset must contain two finite coordinates")

    def _sync_attachment(self, force=False):
        parent, child = self.parent_page._app, self._app
        if not self.ready or parent._window is None or (not force and not self.follow_parent):
            return
        px, py = parent._window.position
        pw, ph = parent.physical_size_for_logical(*parent.outer_size)
        cw, ch = child.physical_size_for_logical(*child.outer_size)
        offset = self._attachment_offset
        dx, dy = offset if isinstance(offset, tuple) else (offset.x, offset.y)
        key = (px, py, pw, ph, cw, ch, self._anchor, dx, dy)
        if key == self._attachment_key:
            return
        anchor = self._anchor
        if isinstance(anchor, Alignment):
            x = px+(pw-cw)*(anchor.x+1)/2
            y = py+(ph-ch)*(anchor.y+1)/2
        else:
            placements = {
                "center": (px+(pw-cw)/2, py+(ph-ch)/2),
                "left": (px-cw, py+(ph-ch)/2), "right": (px+pw, py+(ph-ch)/2),
                "top": (px+(pw-cw)/2, py-ch), "bottom": (px+(pw-cw)/2, py+ph),
                "top_left": (px, py), "top_right": (px+pw-cw, py),
                "bottom_left": (px, py+ph-ch), "bottom_right": (px+pw-cw, py+ph-ch),
            }
            if anchor not in placements:
                raise ValueError(f"Unknown child-window anchor: {anchor!r}")
            x, y = placements[anchor]
        x, y = round(x+dx*parent.pixel_ratio), round(y+dy*parent.pixel_ratio)
        child._window.position = (x, y)
        self.window._values.update(left=x/child.pixel_ratio, top=y/child.pixel_ratio)
        self._attachment_key = key

    def show(self):
        """Show this existing native window, preserving its controls."""
        self.window.visible = True

    def hide(self):
        """Hide this native window without destroying its Page."""
        self.window.visible = False

    def to_front(self):
        """Request focus for this native window."""
        self._app.post(lambda: self._app._window.focus())

    def close(self):
        """Request closing, honoring window.prevent_close and on_event."""
        self.window.close()

    def destroy(self):
        """Force closing this window and its descendants."""
        self._app.close()
