"""Page and Window (flet 1.0 subset; dialogs/services land in later milestones)."""
from __future__ import annotations

import ctypes
import sys
import time

import pygame

from . import colors
from .control import Control
from .types import CrossAxisAlignment, MainAxisAlignment, ThemeMode


def _set_windows_dark_title_bar(hwnd: int, dark: bool) -> bool:
    """Match an HWND's non-client frame to the active light/dark theme."""
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        dwmapi = ctypes.windll.dwmapi
        set_attribute = dwmapi.DwmSetWindowAttribute
        set_attribute.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint,
        ]
        set_attribute.restype = ctypes.c_long
        enabled = ctypes.c_int(1 if dark else 0)
        # Windows 10 20H1+ uses 20. Earlier Windows 10 builds used 19.
        applied = any(
            set_attribute(
                ctypes.c_void_p(hwnd), attribute,
                ctypes.byref(enabled), ctypes.sizeof(enabled)) == 0
            for attribute in (20, 19)
        )
        if applied:
            # Recalculate the non-client frame immediately after a live theme
            # change instead of waiting for the next resize/maximize action.
            user32 = ctypes.windll.user32
            user32.SetWindowPos(
                ctypes.c_void_p(hwnd), None, 0, 0, 0, 0,
                0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
        return applied
    except (AttributeError, OSError, TypeError, ValueError):
        return False


class Window:
    """flet `page.window` subset."""

    def __init__(self, app):
        self._app = app
        self._maximized = False
        self._full_screen = False
        self._minimized = False

    @property
    def width(self) -> int:
        return self._app.outer_size[0]

    @width.setter
    def width(self, v: int):
        self._set_size(int(v), self._app.outer_size[1])

    @property
    def height(self) -> int:
        return self._app.outer_size[1]

    @height.setter
    def height(self, v: int):
        self._set_size(self._app.outer_size[0], int(v))

    @property
    def title(self) -> str:
        return self._app._title

    @title.setter
    def title(self, v: str):
        self._app._title = v
        self._app.post(lambda: setattr(self._app._window, "title", v))

    @property
    def icon(self):
        return self._app._window_icon

    @icon.setter
    def icon(self, path):
        self._app._window_icon = path

        def _set_icon():
            if path:
                self._app._window.set_icon(pygame.image.load(path))
            else:
                self._app._apply_default_window_icon()

        self._app.post(_set_icon)

    # flet Window booleans; all SDL calls marshaled to the UI thread
    @property
    def maximized(self) -> bool:
        return self._maximized

    @maximized.setter
    def maximized(self, v: bool):
        self._maximized = bool(v)
        win = self._app._window
        self._app.post(win.maximize if v else win.restore)

    @property
    def full_screen(self) -> bool:
        return self._full_screen

    @full_screen.setter
    def full_screen(self, v: bool):
        self._full_screen = bool(v)
        win = self._app._window
        self._app.post(win.set_fullscreen if v else win.set_windowed)

    @property
    def minimized(self) -> bool:
        return self._minimized

    @minimized.setter
    def minimized(self, v: bool):
        self._minimized = bool(v)
        if v:
            self._app.post(self._app._window.minimize)
        else:
            self._app.post(self._app._window.restore)

    def _set_size(self, w, h):
        # pygame-ce fires no WINDOWRESIZED for programmatic sets, and the GL
        # context is UI-thread-bound — so the renderer update rides along
        # with the SDL size change on the UI thread. Manual resizes still
        # come through the WINDOWRESIZED event.
        client_w, client_h = self._app.client_size_for_outer(w, h)
        pixel_client = self._app.physical_size_for_logical(
            client_w, client_h)

        def _do():
            self._app._window.size = pixel_client
            self._app.renderer.on_resize(
                client_w, client_h, pixel_size=pixel_client,
                pixel_ratio=self._app.pixel_ratio)
        self._app._outer_size[:] = [w, h]
        self._app._size[:] = [client_w, client_h]
        self._app.post(_do)
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
            w, h = self._app.outer_size
            pw, ph = self._app.physical_size_for_logical(w, h)
            self._app._window.position = ((sw - pw) // 2, (sh - ph) // 2)
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
        colors.theme_dark = colors.system_prefers_dark()  # SYSTEM default
        self._sync_native_title_bar()
        self.theme = None       # ft.Theme(font_family=...) overrides default font
        self.dark_theme = None
        self._fonts: dict[str, str] = {}  # flet page.fonts: alias -> file path
        self.vertical_alignment = MainAxisAlignment.START    # flet BasePage
        self.horizontal_alignment = CrossAxisAlignment.START
        self.spacing = 10
        self.overlay: list[Control] = []  # drawn + hit-tested above the tree
        self.services: list = []          # Flet 1.0 service registration parity
        self.on_resize: list = []  # flet-style event handler lists
        self.on_keyboard_event: list = []
        self._pressed = None
        self._hovered = None
        self._focused = None
        self._pointer_pos = None
        self._last_click_at = 0.0
        self._last_click_pos = None
        self._last_click_target = None
        self._click_count = 0

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
        # SYSTEM follows the OS app-mode preference (Windows dark mode)
        colors.theme_dark = (self._theme_mode is ThemeMode.DARK
                             or (self._theme_mode is ThemeMode.SYSTEM
                                 and colors.system_prefers_dark()))
        colors.apply_seed(getattr(self._theme, "color_scheme_seed", None),
                          expressive=getattr(self._theme, "expressive", False))
        self._sync_native_title_bar()
        self.update()

    def _sync_native_title_bar(self):
        dark = colors.theme_dark
        self._app.post(lambda: _set_windows_dark_title_bar(
            self._app._window.handle, dark))

    @property
    def theme(self):
        return self._theme

    @theme.setter
    def theme(self, t):
        self._theme = t
        from . import text as _txt
        _txt.default_family = t.font_family if t is not None else None
        colors.apply_seed(getattr(t, "color_scheme_seed", None),
                          expressive=getattr(t, "expressive", False))
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
        if hasattr(dialog, "_shown"):
            dialog._shown()
        if hasattr(dialog, "_start_timer"):
            dialog._start_timer(self)
        self.update()

    def pop_dialog(self, dialog=None):
        from .widgets.dialogs import DialogControl
        if dialog is None:
            if not self.overlay:
                return
            dialog = self.overlay[-1]
        if (hasattr(dialog, "_begin_dismiss")
                and dialog._begin_dismiss(self)):
            return
        self._finish_pop_dialog(dialog)

    def _finish_pop_dialog(self, dialog):
        if dialog in self.overlay:
            self.overlay.remove(dialog)
            dialog._closed()
            self.update()

    def update(self):
        now = time.perf_counter()
        for control in [*getattr(self, "controls", []),
                        *getattr(self, "overlay", [])]:
            control._prepare_animation_tree(now)
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

    def _hit_test_hover(self, x, y):
        for control in reversed(self.overlay):
            hit = control._hit_test_hover(x, y)
            if hit is not None:
                return hit
        return super()._hit_test_hover(x, y)

    def draw(self):
        now = time.perf_counter()
        animating = False
        for control in [*self.controls, *self.overlay]:
            animating = control._tick_animation_tree(now) or animating
        if animating:
            self._app.mark_dirty()
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
        self._draw_tooltip(r)

    def _draw_tooltip(self, r):
        target = self._hovered
        tip = getattr(target, "tooltip", None) if target is not None else None
        if not tip:
            return
        from . import text as _text
        from .types import Padding, Tooltip, as_padding

        value = tip if isinstance(tip, Tooltip) else Tooltip(str(tip))
        style = value.text_style
        size = (style.size if style and style.size is not None else 12)
        fg = (style.color if style and style.color is not None else
              (colors.Colors.BLACK if self._dark else colors.Colors.WHITE))
        bg = value.bgcolor or colors.with_opacity(
            0.9, colors.Colors.WHITE if self._dark else colors.Colors.GREY_700)
        pad = as_padding(value.padding if value.padding is not None else
                         Padding.symmetric(horizontal=8, vertical=4))
        surface = _text.render_line(
            value.message, size, scale=r.scale,
            weight=style.weight if style else None,
            italic=style.italic if style else False,
            family=style.font_family if style else None,
            color=colors.parse_color(fg))
        w = surface.get_width() / r.scale + pad.left + pad.right
        h = surface.get_height() / r.scale + pad.top + pad.bottom
        tx, ty, tw, th = target._rect
        x = max(4, min(self.width - w - 4, tx + (tw - w) / 2))
        gap = value.vertical_offset if value.vertical_offset is not None else 8
        below = value.prefer_below is not False
        y = ty + th + gap if below else ty - h - gap
        if y + h > self.height:
            y = ty - h - gap
        if y < 0:
            y = ty + th + gap
        r.overlay_rect(x, y, w, h, colors.parse_color(bg), radius=4)
        r.blit(surface, x + pad.left, y + pad.top)

    def handle_event(self, e):
        if e.type == pygame.WINDOWRESIZED:
            self._dispatch(self.on_resize)
            return
        if e.type == pygame.MOUSEWHEEL:
            # pygame reports wheel-up as positive; content offsets increase
            # toward later items, so down-scrolling needs the opposite sign.
            pointer = self._pointer_pos or pygame.mouse.get_pos()
            self._wheel(-e.y * 40, *pointer)
            return
        if e.type == pygame.TEXTINPUT:
            if self._focused is not None:
                self._focused._text_input(e.text)
            return
        if e.type == pygame.TEXTEDITING:
            if (self._focused is not None
                    and hasattr(self._focused, "_text_editing")):
                self._focused._text_editing(
                    e.text, getattr(e, "start", 0), getattr(e, "length", 0))
            return
        if e.type == pygame.KEYDOWN:
            for control in reversed(self.overlay):
                if control.handle_event(e):
                    return
            self._dispatch(self.on_keyboard_event)
            if self._focused is not None:
                self._focused._key(e)

    def _wheel(self, delta, x=None, y=None):
        if x is None or y is None:
            x, y = self._app.logical_point(*pygame.mouse.get_pos())
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
            if hasattr(old, "_set_focused"):
                old._set_focused(False)
            else:
                old._focused = False
            if hasattr(old, "_clear_composition"):
                old._clear_composition(update=False)
            fire(old, "blur")
        if control is not None:
            if hasattr(control, "_set_focused"):
                control._set_focused(True)
            else:
                control._focused = True
            if not getattr(control, "read_only", False):
                if hasattr(control, "_update_ime_rect"):
                    control._update_ime_rect()
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
            fire(control, "focus")
        else:
            pygame.key.stop_text_input()
        self.update()

    # -- pointer plumbing (called from the UI loop) ------------------------
    def pointer_down(self, x, y, clicks=None):
        self._pointer_pos = (x, y)
        hit = self._hit_test(x, y)
        now = time.perf_counter()
        if clicks is None:
            close = (self._last_click_pos is not None
                     and (x - self._last_click_pos[0]) ** 2
                     + (y - self._last_click_pos[1]) ** 2 <= 16)
            if (hit is self._last_click_target and close
                    and now - self._last_click_at <= 0.5):
                self._click_count = self._click_count % 3 + 1
            else:
                self._click_count = 1
            clicks = self._click_count
        else:
            clicks = max(1, int(clicks))
            self._click_count = clicks
        self._last_click_at = now
        self._last_click_pos = (x, y)
        self._last_click_target = hit
        if hit is not None and getattr(hit, "_focusable", False):
            self.focus(hit)
            if hasattr(hit, "_pointer_down"):
                hit._pointer_down(x, y, clicks)
            elif hasattr(hit, "_caret_at"):
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
        self._pointer_pos = (x, y)
        hit = self._hit_test(x, y)
        if self._pressed is not None:
            self._pressed._pressed = False
            if hasattr(self._pressed, "_drag_end"):
                self._pressed._drag_end()
            if hasattr(self._pressed, "_released_hook"):
                self._pressed._released_hook(x, y)
            consume_click = bool(getattr(self._pressed, "_consume_click", False))
            self._pressed._consume_click = False
            if hit is self._pressed and not consume_click:
                from .event import fire
                fire(hit, "click")
            self._pressed = None
            self.update()

    def pointer_move(self, x, y):
        self._pointer_pos = (x, y)
        if self._pressed is not None and hasattr(self._pressed, "_drag"):
            self._pressed._drag(x, y)
        target = self._hit_test_hover(x, y)
        prev = getattr(self, "_hovered", None)
        if target is prev:
            return
        from .event import fire
        if prev is not None:
            if hasattr(prev, "_set_hover"):
                prev._set_hover(False)
            else:
                prev._hovered = False
                fire(prev, "hover", "false")
        if target is not None:
            if hasattr(target, "_set_hover"):
                target._set_hover(True)
            else:
                target._hovered = True
                fire(target, "hover", "true")
        self._hovered = target
        if prev is not None or target is not None:
            self.update()
