"""Page and Window (flet 1.0 subset; dialogs/services land in later milestones)."""
from __future__ import annotations

import pygame

from . import colors
from .control import Control
from .types import CrossAxisAlignment, MainAxisAlignment, ThemeMode


class Window:
    """flet `page.window` subset."""

    def __init__(self, app):
        self._app = app

    @property
    def width(self) -> int:
        return self._app.size[0]

    @width.setter
    def width(self, v: int):
        self._set_size(int(v), self._app.size[1])

    @property
    def height(self) -> int:
        return self._app.size[1]

    @height.setter
    def height(self, v: int):
        self._set_size(self._app.size[0], int(v))

    @property
    def title(self) -> str:
        return self._app._title

    @title.setter
    def title(self, v: str):
        self._app._title = v
        self._app.post(lambda: pygame.display.set_caption(v))

    # flet Window booleans; all SDL calls marshaled to the UI thread
    @property
    def maximized(self) -> bool:
        return self._app._window.maximized

    @maximized.setter
    def maximized(self, v: bool):
        win = self._app._window
        self._app.post(win.maximize if v else win.restore)

    @property
    def full_screen(self) -> bool:
        return getattr(self._app._window, "fullscreen", False)

    @full_screen.setter
    def full_screen(self, v: bool):
        win = self._app._window
        self._app.post(win.set_fullscreen if v else win.set_windowed)

    @property
    def minimized(self) -> bool:
        return False

    @minimized.setter
    def minimized(self, v: bool):
        if v:
            self._app.post(self._app._window.minimize)

    def _set_size(self, w, h):
        def _do():
            self._app._window.size = (w, h)
        self._app._size = [w, h]
        self._app.post(_do)
        self._app.renderer.on_resize(w, h)
        self._app.mark_dirty()

    def close(self):
        self._app.close()

    def destroy(self):
        self._app.close()

    async def center(self):
        # posted: SDL display calls are main-thread-only; runs after any
        # size changes queued earlier, so it centers the final size
        def _do():
            sw, sh = pygame.display.get_desktop_sizes()[0]
            w, h = self._app._window.size
            self._app._window.position = ((sw - w) // 2, (sh - h) // 2)
        self._app.post(_do)


class Page(Control):
    """Root control container. Handlers (on_resize etc.) run off the UI thread."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self.window = Window(app)
        self.controls: list[Control] = []
        self.bgcolor = None       # None → theme surface color
        self.padding = 10
        self._title = ""
        self._theme_mode = ThemeMode.SYSTEM
        self.theme = None       # ft.Theme(font_family=...) overrides default font
        self.dark_theme = None
        self._fonts: dict[str, str] = {}  # flet page.fonts: alias -> file path
        self.vertical_alignment = MainAxisAlignment.START    # flet BasePage
        self.horizontal_alignment = CrossAxisAlignment.START
        self.spacing = 10
        self.overlay: list[Control] = []  # drawn + hit-tested above the tree
        self.on_resize: list = []  # flet-style event handler lists
        self.on_keyboard_event: list = []
        self._pressed = None
        self._hovered = None
        self._focused = None

    # -- flet API ---------------------------------------------------------
    @property
    def width(self) -> float:
        return self._app.size[0]

    @property
    def height(self) -> float:
        return self._app.size[1]

    @property
    def theme_mode(self) -> ThemeMode:
        return self._theme_mode

    @theme_mode.setter
    def theme_mode(self, mode):
        self._theme_mode = mode if isinstance(mode, ThemeMode) else ThemeMode(mode)
        # ponytail: SYSTEM always resolves light; OS-theme detection when needed
        colors.theme_dark = self._theme_mode is ThemeMode.DARK
        self.update()

    @property
    def theme(self):
        return self._theme

    @theme.setter
    def theme(self, t):
        self._theme = t
        from . import text as _txt
        _txt.default_family = t.font_family if t is not None else None
        self.update()

    @property
    def fonts(self) -> dict[str, str]:
        return self._fonts

    @fonts.setter
    def fonts(self, fonts: dict[str, str]):
        self._fonts = dict(fonts or {})
        from . import text as _txt
        _txt.register_fonts(self._fonts)

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, v: str):
        self._title = v
        self.window.title = v or "saturn"

    def add(self, *ctrls: Control):
        self.controls.extend(ctrls)
        for c in ctrls:
            c._attach(self, self)
        self.update()

    def insert(self, index, ctrl):
        self.controls.insert(index, ctrl)
        ctrl._attach(self, self)
        self.update()

    def remove(self, ctrl):
        self.controls.remove(ctrl)
        self.update()

    def remove_at(self, index):
        self.controls.pop(index)
        self.update()

    def clean(self):
        self.controls.clear()
        self.update()

    # -- dialogs (overlay) ---------------------------------------------------
    def show_dialog(self, dialog):
        from .widgets.dialogs import DialogControl
        if not isinstance(dialog, DialogControl):
            raise TypeError("show_dialog expects a DialogControl (AlertDialog/SnackBar)")
        if dialog in self.overlay:
            return
        dialog._attach(self, None)
        dialog.open = True
        self.overlay.append(dialog)
        if hasattr(dialog, "_start_timer"):
            dialog._start_timer(self)
        self.update()

    def pop_dialog(self, dialog=None):
        from .widgets.dialogs import DialogControl
        if dialog is None:
            if not self.overlay:
                return
            dialog = self.overlay[-1]
        if dialog in self.overlay:
            self.overlay.remove(dialog)
        dialog._closed()
        self.update()

    def update(self):
        self._app.mark_dirty()

    def run_task(self, handler, *args):
        """flet run_task: schedule a coroutine handler on the app's loop."""
        return self._app.call(handler, *args)

    async def take_screenshot(self, path: str | None = None):
        """flet-style async screenshot; returns the frame surface (and saves
        to `path` when given)."""
        return self._app.screenshot(path)

    def _dispatch(self, handlers: list):
        for h in list(handlers):
            self._app.call(h, self)

    # -- internals ---------------------------------------------------------
    def _hit_test(self, x, y):
        for c in reversed(self.overlay):
            hit = c._hit_test(x, y)
            if hit is not None:
                return hit
        return super()._hit_test(x, y)

    def draw(self):
        r = self._app.renderer
        r.clear(self.bgcolor or colors.Colors.SURFACE)
        from .widgets.containers import Column
        p = self.padding
        col = Column(*self.controls, alignment=self.vertical_alignment,
                     horizontal_alignment=self.horizontal_alignment,
                     spacing=self.spacing)
        col._place(p, p, self.width - 2 * p, self.height - 2 * p, r.scale)
        self._draw_all(r)
        for c in self.overlay:
            if getattr(c, "_overlay_fill", False):
                c._place(0, 0, self.width, self.height, r.scale)
            c._draw_all(r)

    def handle_event(self, e):
        if e.type == pygame.WINDOWRESIZED:
            self._dispatch(self.on_resize)
            return
        if e.type == pygame.MOUSEWHEEL:
            self._wheel(e.y * 40)
            return
        if e.type == pygame.TEXTINPUT:
            if self._focused is not None:
                self._focused._text_input(e.text)
            return
        if e.type == pygame.KEYDOWN:
            self._dispatch(self.on_keyboard_event)
            if self._focused is not None:
                self._focused._key(e)

    def _wheel(self, delta, x=None, y=None):
        if x is None or y is None:
            x, y = pygame.mouse.get_pos()
        lv = self._find_scrollable(x, y)
        if lv is not None:
            lv._wheel(delta)

    def _find_scrollable(self, x, y):
        best = None
        for c in list(reversed(self.overlay)) + list(reversed(self.controls)):
            best = c._find_scrollable(x, y) or best
        return best

    # -- focus ---------------------------------------------------------------
    def focus(self, control):
        if self._focused is control:
            return
        from .event import fire
        old, self._focused = self._focused, control
        if old is not None:
            old._focused = False
            fire(old, "blur")
        if control is not None:
            control._focused = True
            pygame.key.start_text_input()
            fire(control, "focus")
        else:
            pygame.key.stop_text_input()
        self.update()

    # -- pointer plumbing (called from the UI loop) ------------------------
    def pointer_down(self, x, y):
        hit = self._hit_test(x, y)
        if hit is not None and getattr(hit, "_focusable", False):
            self.focus(hit)
            if hasattr(hit, "_caret_at"):
                hit._caret_at(x)
        elif hit is None and self._focused is not None:
            self.focus(None)
        self._pressed = hit
        if hit is not None:
            hit._pressed = True
            if hasattr(hit, "_pressed_hook"):
                hit._pressed_hook(x, y)
            if hasattr(hit, "_drag_start"):
                hit._drag_start(x, y)
            self.update()

    def pointer_up(self, x, y):
        hit = self._hit_test(x, y)
        if self._pressed is not None:
            self._pressed._pressed = False
            if hasattr(self._pressed, "_drag_end"):
                self._pressed._drag_end()
            if hit is self._pressed:
                from .event import fire
                fire(hit, "click")
            self._pressed = None
            self.update()

    def pointer_move(self, x, y):
        if self._pressed is not None and hasattr(self._pressed, "_drag"):
            self._pressed._drag(x, y)
        target = self._hit_test_hover(x, y)
        prev = getattr(self, "_hovered", None)
        if target is prev:
            return
        from .event import fire
        if prev is not None:
            prev._hovered = False
            fire(prev, "hover", "false")
        if target is not None:
            target._hovered = True
            fire(target, "hover", "true")
        self._hovered = target
        if prev is not None or target is not None:
            self.update()
