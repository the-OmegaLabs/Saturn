"""Root page and native window configuration."""
from __future__ import annotations

import ctypes
import sys
import time
from types import SimpleNamespace

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


from .window import Window


class _RendererSettings:
    """Renderer options applied on the application's UI thread."""

    def __init__(self, app):
        self._app = app

    @property
    def name(self) -> str | None:
        """Active backend: software, opengl or vulkan; None before startup."""
        context = self.context
        return context.name if context is not None else None

    @property
    def gpu_name(self) -> str | None:
        """Actual GPU model; None before startup or with Software rendering."""
        return self.context.gpu_name if self.context is not None else None

    @property
    def gpu_index(self) -> int | None:
        """Index of the active GPU in this context's gpus tuple."""
        return self.context.gpu_index if self.context is not None else None

    @property
    def gpus(self) -> tuple[str, ...]:
        """GPU names available to this backend/context, in selector index order."""
        return self.context.gpus if self.context is not None else ()

    @property
    def anti_aliasing(self) -> bool:
        return self._app._anti_aliasing

    @anti_aliasing.setter
    def anti_aliasing(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError("anti_aliasing must be a bool")
        self._app.configure_renderer(anti_aliasing=value)

    @property
    def vsync(self) -> bool:
        return self._app._vsync

    @vsync.setter
    def vsync(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError("vsync must be a bool")
        self._app.configure_renderer(vsync=value)

    @property
    def context(self):
        """The active renderer; use its GPU operations on the UI thread."""
        return self._app.renderer


class Page(Control):
    """Root control container. Handlers (on_resize etc.) run off the UI thread."""

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._renderer_settings = _RendererSettings(app)
        self.window = Window(app)
        self.controls: list[Control] = []
        self.on_route_change = None
        self.on_render_failed = None
        self.on_render_ready = None
        self.on_font_optimize = None
        self.bgcolor = None       # None → theme surface color
        self.padding = 10
        self._theme_mode = ThemeMode.SYSTEM
        self._platform_brightness = ("dark" if colors.system_prefers_dark()
                                     else "light")
        self._theme = None
        self._dark_theme = None
        self._theme_key = None
        self._fonts: dict[str, str] = {}
        self._fonts_snapshot = None
        self.vertical_alignment = MainAxisAlignment.START
        self.horizontal_alignment = CrossAxisAlignment.START
        self.spacing = 10
        self.overlay: list[Control] = []  # drawn + hit-tested above the tree
        self.services: list = []          # Registered application services
        self.on_resize: list = []  # Resize event handlers
        self.on_keyboard_event: list = []
        self.on_platform_brightness_change = None
        self._pressed = None
        self._hovered = None
        self._focused = None
        self._pointer_pos = None
        self._last_click_at = 0.0
        self._last_click_pos = None
        self._last_click_target = None
        self._click_count = 0
        self._layout_dirty = True
        self._layout_key = None
        self._active_animations = set()
        self._animation_scan_needed = True
        self._attached_roots = {}
        self._attached_services = {}
        self.page = self
        from .routing import RouteState
        if not hasattr(app, "_router"):
            app._router = RouteState()
        app._router.register(self)
        self._apply_theme()

    # -- public API ---------------------------------------------------------
    @property
    def renderer(self):
        """Rendering settings and the active backend context."""
        return self._renderer_settings

    @property
    def route(self):
        return self._app._router.route

    @route.setter
    def route(self, value):
        self.go(value)

    def go(self, route):
        """Set the application route and notify each window's route handler."""
        self._app._router.go(route)

    def open_subpage(self, main=None, *, title="Settings", modal=False,
                     anchor="center", offset=None, follow_parent=False, backend=None, gpu=None):
        """Create an owned native child window and return its Subpage handle."""
        from .subpage import Subpage
        return Subpage(self, main=main, title=title, modal=modal, anchor=anchor,
                       offset=offset, follow_parent=follow_parent, backend=backend, gpu=gpu)

    @property
    def subpages(self):
        """Direct child-window Pages that have not been destroyed."""
        return tuple(app.page for app in getattr(self._app, "_children", ())
                     if app.page is not None and not app._closed.is_set())

    @property
    def width(self) -> float:
        return self._app.size[0]

    @property
    def height(self) -> float:
        return self._app.size[1]

    @property
    def media(self):
        """Measured native display density; dimensions remain logical pixels."""
        return SimpleNamespace(device_pixel_ratio=self._app.pixel_ratio)

    @property
    def theme_mode(self) -> ThemeMode:
        return self._theme_mode

    @theme_mode.setter
    def theme_mode(self, mode):
        self._theme_mode = mode if isinstance(mode, ThemeMode) else ThemeMode(mode)
        self.update()

    @property
    def platform_brightness(self) -> str:
        """Current OS application color preference: light or dark."""
        return self._platform_brightness

    def _refresh_platform_brightness(self):
        colors._system_dark_cache = None
        value = "dark" if colors.system_prefers_dark() else "light"
        if value == self._platform_brightness:
            return False
        self._platform_brightness = value
        self.update()
        from .event import PlatformBrightnessChangeEvent
        self._dispatch(self.on_platform_brightness_change,
                       PlatformBrightnessChangeEvent(
                           "platform_brightness_change", self,
                           brightness=value))
        return True

    def _apply_theme(self):
        dark = (self._theme_mode is ThemeMode.DARK or
                (self._theme_mode is ThemeMode.SYSTEM and
                 self._platform_brightness == "dark"))
        effective = self._dark_theme if dark and self._dark_theme is not None else self._theme
        key = (dark, getattr(effective, "font_family", None),
               getattr(effective, "color_scheme_seed", None),
               getattr(effective, "expressive", False))
        if key == self._theme_key:
            return
        self._theme_key = key
        if hasattr(self._app, "_root"):
            self._app._root._active_theme = None
        colors.theme_dark = dark
        colors.apply_seed(key[2], expressive=key[3])
        from . import text
        text.set_default_family(key[1])
        self._sync_native_title_bar()

    def _sync_native_title_bar(self):
        dark = colors.theme_dark
        brightness = getattr(self.window, "brightness", None)
        if brightness is not None:
            dark = getattr(brightness, "value", brightness) == "dark"
        self._app.post(lambda: _set_windows_dark_title_bar(
            self._app._window.handle, dark))

    @property
    def theme(self):
        return self._theme

    @theme.setter
    def theme(self, t):
        self._theme = t
        self.update()

    @property
    def dark_theme(self):
        return self._dark_theme

    @dark_theme.setter
    def dark_theme(self, theme):
        self._dark_theme = theme
        self.update()

    @property
    def fonts(self) -> dict[str, str]:
        return self._fonts

    @fonts.setter
    def fonts(self, fonts: dict[str, str]):
        self._fonts = dict(fonts or {})
        self.update()

    def _sync_fonts(self):
        if self._fonts != self._fonts_snapshot:
            from . import text
            text.register_fonts(self._fonts, on_ready=self._font_ready)
            self._fonts_snapshot = dict(self._fonts)

    def _font_ready(self):
        self._layout_dirty = True
        self._app.mark_dirty()

    @property
    def title(self) -> str:
        return self.window.title

    @title.setter
    def title(self, v: str):
        self.window.title = v or "saturn"

    def add(self, *ctrls: Control):
        self.controls.extend(ctrls)
        self.update()

    def insert(self, index, ctrl):
        self.controls.insert(index, ctrl)
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

    def _reconcile_roots(self):
        """Attach direct list mutations without reattaching unchanged trees."""
        roots = {id(control): (control, self) for control in self.controls}
        roots.update({id(control): (control, None) for control in self.overlay})
        previous = tuple(self._attached_roots.values())
        self._attached_roots = roots
        self._reconcile_trees(tuple(roots.values()), previous)

    def _reconcile_branch(self, control):
        """Keep an updated subtree attached without scanning unrelated rows."""
        self._reconcile_trees(((control, control.parent),), ((control, control.parent),))

    def _reconcile_trees(self, roots, previous_roots):
        previous, current = set(), set()
        def collect_old(control):
            if control in previous:
                return
            previous.add(control)
            for child in getattr(control, "_attached_child_controls", ()):
                collect_old(child)
        for control, _ in previous_roots:
            collect_old(control)
        def reconcile(control, parent):
            if control in current:
                raise ValueError("A control cannot occur twice in the same control tree")
            current.add(control)
            if control.page is not self:
                control._attach(self, parent)
            else:
                control.parent = parent
            children = tuple(control._children())
            control._attached_child_controls = children
            for child in children:
                reconcile(child, control)
        for control, parent in roots:
            reconcile(control, parent)
        detached = previous-current
        # Branch updates preserve controls already reparented into another tree.
        if len(roots) == 1 and roots[0][0] not in [*self.controls, *self.overlay]:
            detached = {control for control in detached if control.parent in previous}
        if self._focused in detached:
            self.focus(None)
        if self._pressed in detached:
            if hasattr(self._pressed, "_cancel_pointer"):
                self._pressed._cancel_pointer()
            self._pressed._pressed = False
            self._pressed = None
        if self._hovered in detached:
            self._hovered._hovered = False
            self._hovered = None
        self._active_animations.difference_update(detached)
        for control in detached:
            control.page, control.parent = None, None

    def _reconcile_services(self):
        current = {id(service): service for service in self.services}
        previous, self._attached_services = self._attached_services, current
        for ident, service in previous.items():
            if ident not in current and getattr(service, "page", None) is self:
                service.page = None
        for service in current.values():
            if getattr(service, "page", None) is not self:
                if hasattr(service, "_attach"):
                    service._attach(self, self)
                else:
                    service.page = self

    def update(self):
        if not hasattr(self, "_attached_roots"):
            return
        self._apply_theme()
        self._sync_fonts()
        self._reconcile_roots()
        self._reconcile_services()
        if self.disabled:
            self._cancel_input()
        now = time.perf_counter()
        for control in [*self._children(),
                        *getattr(self, "overlay", [])]:
            control._prepare_animation_tree(now)
        self._layout_dirty = True
        self._animation_scan_needed = True
        self._app.mark_dirty()

    def repaint(self):
        """Redraw when geometry has not changed (scroll, hover, ripple)."""
        self._app.mark_dirty()

    def run_task(self, handler, *args):
        """Schedule a coroutine handler on the application event loop."""
        return self._app.call(handler, *args)

    async def take_screenshot(self, path: str | None = None):
        """Return the captured frame surface (and save
        to `path` when given)."""
        return self._app.screenshot(path)

    def _dispatch(self, handlers, event=None):
        from .event import ControlEvent, _invoke, normalize_handlers
        event = event or ControlEvent("event", self)
        for handler in normalize_handlers(handlers):
            self._app.call(_invoke, handler, event)

    def _notify_resize(self):
        from .event import PageResizeEvent
        self._dispatch(self.on_resize, PageResizeEvent(
            "resize", self, width=self.width, height=self.height))

    # -- internals ---------------------------------------------------------
    def _hit_test(self, x, y):
        if self.disabled or not self.visible:
            return None
        for c in reversed(self.overlay):
            hit = c._hit_test(x, y)
            if hit is not None:
                return hit
        return super()._hit_test(x, y)

    def _hit_test_hover(self, x, y):
        if self.disabled or not self.visible:
            return None
        for control in reversed(self.overlay):
            hit = control._hit_test_hover(x, y)
            if hit is not None:
                return hit
        return super()._hit_test_hover(x, y)

    def draw(self):
        now = time.perf_counter()
        animating = False
        if self._animation_scan_needed:
            for control in [*self._children(), *self.overlay]:
                animating = control._tick_animation_tree(now) or animating
            self._animation_scan_needed = False
        else:
            for control in tuple(self._active_animations):
                if not self._control_enabled(control):
                    self._active_animations.discard(control)
                    continue
                if control._tick_animations(now):
                    animating = True
                else:
                    self._active_animations.discard(control)
        if animating:
            self._app.mark_dirty()
        r = self._app.renderer
        r.clear(self.bgcolor or self.window.bgcolor or colors.Colors.SURFACE)
        from .widgets.containers import Column
        from .types import as_padding
        p = as_padding(self.padding)
        layout_key = (self.width, self.height, r.scale,
                      p.left, p.top, p.right, p.bottom,
                      self.vertical_alignment, self.horizontal_alignment,
                      self.spacing, tuple(self._children()))
        if self._layout_dirty or layout_key != self._layout_key:
            col = Column(*self._children(), alignment=self.vertical_alignment,
                         horizontal_alignment=self.horizontal_alignment,
                         spacing=self.spacing)
            col._place(p.left, p.top,
                       max(0, self.width - p.left - p.right),
                       max(0, self.height - p.top - p.bottom), r.scale)
            self._layout_key = layout_key
            self._layout_dirty = False
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
            self._notify_resize()
            return
        if self.disabled or not self.visible:
            self._cancel_input()
            return
        if e.type == pygame.MOUSEWHEEL:
            # pygame reports wheel-up as positive; content offsets increase
            # toward later items, so down-scrolling needs the opposite sign.
            pointer = self._pointer_pos
            if pointer is None:
                pointer = self._app.logical_point(*pygame.mouse.get_pos())
            self._wheel(-e.y * 40, *pointer)
            return
        if e.type == pygame.TEXTINPUT:
            if self._control_enabled(self._focused):
                self._focused._text_input(e.text)
            return
        if e.type == pygame.TEXTEDITING:
            if (self._control_enabled(self._focused)
                    and hasattr(self._focused, "_text_editing")):
                self._focused._text_editing(
                    e.text, getattr(e, "start", 0), getattr(e, "length", 0))
            return
        if e.type == pygame.KEYDOWN:
            from .event import KeyboardEvent
            key_names = {
                pygame.K_RETURN: "Enter", pygame.K_KP_ENTER: "Enter",
                pygame.K_ESCAPE: "Escape", pygame.K_SPACE: " ",
                pygame.K_BACKSPACE: "Backspace", pygame.K_TAB: "Tab",
                pygame.K_DELETE: "Delete", pygame.K_INSERT: "Insert",
                pygame.K_LEFT: "Arrow Left", pygame.K_RIGHT: "Arrow Right",
                pygame.K_UP: "Arrow Up", pygame.K_DOWN: "Arrow Down",
                pygame.K_HOME: "Home", pygame.K_END: "End",
                pygame.K_PAGEUP: "Page Up", pygame.K_PAGEDOWN: "Page Down",
            }
            key = key_names.get(e.key, pygame.key.name(e.key))
            if len(key) == 1 or key.startswith("f") and key[1:].isdigit():
                key = key.upper()
            mods = getattr(e, "mod", 0)
            self._dispatch(self.on_keyboard_event, KeyboardEvent(
                "keyboard_event", self, key=key,
                shift=bool(mods & pygame.KMOD_SHIFT),
                ctrl=bool(mods & pygame.KMOD_CTRL),
                alt=bool(mods & pygame.KMOD_ALT),
                meta=bool(mods & pygame.KMOD_GUI)))
            for control in reversed(self.overlay):
                if self._control_enabled(control) and control.handle_event(e):
                    return
            if e.key == pygame.K_TAB:
                self._focus_next(reverse=bool(mods & pygame.KMOD_SHIFT))
                return
            if self._control_enabled(self._focused):
                self._focused._key(e)

    def _wheel(self, delta, x=None, y=None):
        if self.disabled or not self.visible:
            return
        if x is None or y is None:
            x, y = self._app.logical_point(*pygame.mouse.get_pos())
        lv = self._find_scrollable(x, y)
        if self._control_enabled(lv):
            lv._wheel(delta)

    def _find_scrollable(self, x, y):
        if self.disabled or not self.visible:
            return None
        best = None
        for c in list(reversed(self.overlay)) + list(reversed(self._children())):
            best = c._find_scrollable(x, y) or best
        return best

    # -- focus ---------------------------------------------------------------
    def focus(self, control):
        if control is not None and (not self._control_enabled(control) or
                                    not getattr(control, "can_request_focus", True)):
            return
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
            if hasattr(control, "_update_ime_rect") and not getattr(control, "read_only", False):
                if hasattr(control, "_update_ime_rect"):
                    control._update_ime_rect()
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
            fire(control, "focus")
        else:
            pygame.key.stop_text_input()
        self.update()

    def _focus_next(self, reverse=False):
        controls = []
        def visit(control):
            if not self._control_enabled(control):
                return
            if getattr(control, "_focusable", False) and getattr(control, "can_request_focus", True):
                controls.append(control)
            for child in control._children():
                visit(child)
        from .widgets.dialogs import AlertDialog
        blockers = [root for root in self.overlay if isinstance(root, AlertDialog)
                    and root.open and root.visible]
        roots = blockers[-1:] if blockers else [*self._children(), *self.overlay]
        for root in roots:
            visit(root)
        if not controls:
            return
        step = -1 if reverse else 1
        index = controls.index(self._focused) if self._focused in controls else (0 if reverse else -1)
        self.focus(controls[(index + step) % len(controls)])

    def _control_enabled(self, control):
        if control is None or self.disabled or not self.visible:
            return False
        node = control
        root = control
        while node is not None and node is not self:
            if node.disabled or not node.visible:
                return False
            root = node
            node = node.parent
        if root is not self and root not in [*self._children(), *self.overlay]:
            return False
        owner = getattr(root, "owner", None)
        if isinstance(owner, Control) and owner is not control and not self._control_enabled(owner):
            return False
        return control.page is self

    def _cancel_input(self):
        if self._focused is not None:
            self.focus(None)
        if self._pressed is not None:
            if hasattr(self._pressed, "_cancel_pointer"):
                self._pressed._cancel_pointer()
            self._pressed._pressed = False
            self._pressed = None
        if self._hovered is not None:
            self._hovered._hovered = False
            self._hovered = None
        self._sync_mouse_cursor(None)

    # -- pointer plumbing (called from the UI loop) ------------------------
    def pointer_down(self, x, y, clicks=None):
        if self.disabled or not self.visible:
            self._cancel_input()
            return
        self._pointer_pos = (x, y)
        hit = self._hit_test(x, y)
        if self._focused is not None and hit is not self._focused:
            from .event import fire
            fire(self._focused, "tap_outside", (x, y))
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
            local_x, local_y = hit._event_point(x, y)
            if hasattr(hit, "_pointer_down"):
                hit._pointer_down(local_x, local_y, clicks)
            elif hasattr(hit, "_caret_at"):
                hit._caret_at(local_x)
        elif hit is None and self._focused is not None:
            self.focus(None)
        self._pressed = hit
        if hit is not None:
            local_x, local_y = hit._event_point(x, y)
            hit._pressed = True
            if hasattr(hit, "_pressed_hook"):
                hit._pressed_hook(local_x, local_y)
            if hasattr(hit, "_drag_start"):
                hit._drag_start(local_x, local_y)
            self.update()

    def pointer_up(self, x, y):
        if self.disabled or not self.visible:
            self._cancel_input()
            return
        self._pointer_pos = (x, y)
        hit = self._hit_test(x, y)
        if self._pressed is not None:
            self._pressed._pressed = False
            if hasattr(self._pressed, "_drag_end"):
                self._pressed._drag_end()
            if hasattr(self._pressed, "_released_hook"):
                self._pressed._released_hook(*self._pressed._event_point(x, y))
            consume_click = bool(getattr(self._pressed, "_consume_click", False))
            self._pressed._consume_click = False
            if hit is self._pressed and not consume_click:
                from .event import fire
                fire(hit, "click")
            self._pressed = None
            self.update()

    def pointer_move(self, x, y):
        if self.disabled or not self.visible:
            self._cancel_input()
            return
        self._pointer_pos = (x, y)
        if self._pressed is not None and hasattr(self._pressed, "_drag"):
            self._pressed._drag(*self._pressed._event_point(x, y))
        target = self._hit_test_hover(x, y)
        self._sync_mouse_cursor(target)
        if target is not None and hasattr(target, "_hover_move"):
            target._hover_move(*target._event_point(x, y))
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
            self.repaint()

    def _sync_mouse_cursor(self, target):
        cursor = getattr(target, "mouse_cursor", None)
        if cursor is None and getattr(target, "_update_ime_rect", None):
            cursor = "text"
        value = getattr(cursor, "value", cursor) or "basic"
        if value == getattr(self, "_mouse_cursor_value", None):
            return
        constants = {
            "basic": pygame.SYSTEM_CURSOR_ARROW, "click": pygame.SYSTEM_CURSOR_HAND,
            "text": pygame.SYSTEM_CURSOR_IBEAM, "verticalText": pygame.SYSTEM_CURSOR_IBEAM,
            "forbidden": pygame.SYSTEM_CURSOR_NO, "noDrop": pygame.SYSTEM_CURSOR_NO,
            "move": pygame.SYSTEM_CURSOR_SIZEALL, "allScroll": pygame.SYSTEM_CURSOR_SIZEALL,
            "grab": pygame.SYSTEM_CURSOR_HAND, "grabbing": pygame.SYSTEM_CURSOR_HAND,
            "precise": pygame.SYSTEM_CURSOR_CROSSHAIR, "cell": pygame.SYSTEM_CURSOR_CROSSHAIR,
            "wait": pygame.SYSTEM_CURSOR_WAIT, "progress": pygame.SYSTEM_CURSOR_WAITARROW,
            "resizeLeftRight": pygame.SYSTEM_CURSOR_SIZEWE, "resizeColumn": pygame.SYSTEM_CURSOR_SIZEWE,
            "resizeLeft": pygame.SYSTEM_CURSOR_SIZEWE, "resizeRight": pygame.SYSTEM_CURSOR_SIZEWE,
            "resizeUpDown": pygame.SYSTEM_CURSOR_SIZENS, "resizeRow": pygame.SYSTEM_CURSOR_SIZENS,
            "resizeUp": pygame.SYSTEM_CURSOR_SIZENS, "resizeDown": pygame.SYSTEM_CURSOR_SIZENS,
            "resizeUpLeftDownRight": pygame.SYSTEM_CURSOR_SIZENWSE,
            "resizeUpRightDownLeft": pygame.SYSTEM_CURSOR_SIZENESW,
            "resizeUpLeft": pygame.SYSTEM_CURSOR_SIZENWSE, "resizeDownRight": pygame.SYSTEM_CURSOR_SIZENWSE,
            "resizeUpRight": pygame.SYSTEM_CURSOR_SIZENESW, "resizeDownLeft": pygame.SYSTEM_CURSOR_SIZENESW,
        }
        try:
            pygame.mouse.set_visible(value != "none")
            if value != "none":
                pygame.mouse.set_cursor(constants.get(value, pygame.SYSTEM_CURSOR_ARROW))
            self._mouse_cursor_value = value
        except pygame.error:
            pass
