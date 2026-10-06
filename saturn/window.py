"""Native desktop window properties and events; mutations use the UI queue."""
from __future__ import annotations

import asyncio
import ctypes
import enum
import math
import sys
from dataclasses import dataclass

import pygame

from .event import _invoke


class WindowEventType(enum.Enum):
    CLOSE = "close"
    FOCUS = "focus"
    BLUR = "blur"
    HIDE = "hide"
    SHOW = "show"
    MAXIMIZE = "maximize"
    UNMAXIMIZE = "unmaximize"
    MINIMIZE = "minimize"
    RESTORE = "restore"
    RESIZE = "resize"
    RESIZED = "resized"
    MOVE = "move"
    MOVED = "moved"
    LEAVE_FULL_SCREEN = "leave-full-screen"
    ENTER_FULL_SCREEN = "enter-full-screen"


class WindowResizeEdge(enum.Enum):
    TOP = "top"
    LEFT = "left"
    RIGHT = "right"
    BOTTOM = "bottom"
    TOP_LEFT = "topLeft"
    BOTTOM_LEFT = "bottomLeft"
    TOP_RIGHT = "topRight"
    BOTTOM_RIGHT = "bottomRight"


@dataclass
class WindowEvent:
    control: "Window"
    type: WindowEventType

    @property
    def page(self):
        return self.control.page

    @property
    def name(self):
        return self.type.value


def _setting(name, default, apply=None, validate=None, windows_only=False):
    def get(window):
        return window._values.get(name, default)

    def set(window, value):
        if windows_only and sys.platform != "win32":
            raise NotImplementedError(f"window.{name} currently requires Windows")
        if validate:
            value = validate(value)
        elif isinstance(default, bool):
            if not isinstance(value, bool):
                raise TypeError(f"window.{name} must be a bool")
        window._validate_setting(name, value)
        if window._values.get(name, default) == value:
            return
        window._values[name] = value
        if apply:
            window._post(lambda: getattr(window, apply)())
    return property(get, set, doc=f"Native window {name} setting.")


def _unit(value):
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("value must be between 0 and 1")
    return value


def _positive(value):
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("value must be a positive finite number or None")
    return value


def _color(value):
    if value is not None:
        from .colors import parse_color
        parse_color(value)
    return value


def _brightness(value):
    if value is not None and getattr(value, "value", value) not in ("light", "dark"):
        raise ValueError("brightness must be light, dark, or None")
    return value


def _alignment(value):
    if value is not None:
        if not hasattr(value, "x") or not hasattr(value, "y"):
            raise TypeError("alignment must have x/y coordinates")
        if not all(math.isfinite(float(v)) and -1 <= v <= 1 for v in (value.x, value.y)):
            raise ValueError("alignment coordinates must be between -1 and 1")
    return value


def _coordinate(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("position must be a finite number")
    return value


class Window:
    """Desktop window configuration. All sizes and positions are logical pixels."""
    __slots__ = ("_app", "_values", "_native", "_size_pending", "_pending_size",
                 "_applied_limits", "_last_resize_event", "on_event", "data", "key")

    def __init__(self, app):
        self._app = app
        self._values = {}
        self._native = None
        self._size_pending = False
        self._pending_size = None
        self._last_resize_event = None
        self.on_event = None
        self.data = None
        self.key = None
        self._post(self._install_native)

    def _post(self, fn):
        self._app.post(fn)
        self._app.mark_dirty()

    @property
    def hwnd(self) -> int:
        """The real HWND on Windows; zero on platforms without HWNDs."""
        window = getattr(self._app, "_window", None)
        try:
            return int(window.handle) if sys.platform == "win32" and window is not None else 0
        except pygame.error:
            return 0

    @property
    def native_handle(self) -> int:
        window = getattr(self._app, "_window", None)
        try:
            return int(window.handle) if window is not None else 0
        except pygame.error:
            return 0

    @property
    def page(self):
        return getattr(self._app, "page", None)

    @property
    def parent(self):
        return self.page

    @property
    def width(self):
        return self._app.outer_size[0]

    @width.setter
    def width(self, value):
        self._set_size(_positive(value), self.height)

    @property
    def height(self):
        return self._app.outer_size[1]

    @height.setter
    def height(self, value):
        self._set_size(self.width, _positive(value))

    @property
    def title(self):
        return self._app._title

    @title.setter
    def title(self, value):
        self._app._title = str(value or "saturn")
        self._post(lambda: setattr(self._app._window, "title", self._app._title))

    @property
    def icon(self):
        return self._app._window_icon

    @icon.setter
    def icon(self, path):
        self._app._window_icon = path
        def apply():
            if path:
                self._app._window.set_icon(pygame.image.load(path))
            else:
                self._app._apply_default_window_icon()
        self._post(apply)

    @property
    def left(self):
        return self._position()[0]

    @left.setter
    def left(self, value):
        if value is not None:
            self._values["left"] = _coordinate(value)
            self._post(self._apply_position)
        else:
            self._values.pop("left", None)

    @property
    def top(self):
        return self._position()[1]

    @top.setter
    def top(self, value):
        if value is not None:
            self._values["top"] = _coordinate(value)
            self._post(self._apply_position)
        else:
            self._values.pop("top", None)

    def _position(self):
        window = getattr(self._app, "_window", None)
        ratio = getattr(self._app, "pixel_ratio", 1)
        position = window.position if window is not None else (0, 0)
        return tuple(self._values.get(name, position[i] / ratio)
                     for i, name in enumerate(("left", "top")))

    def _apply_position(self):
        self._app._window.position = tuple(
            round(v * self._app.pixel_ratio) for v in self._position())

    @property
    def maximized(self):
        return (bool(self._native.user32.IsZoomed(self.hwnd)) if self._native
                else self._values.get("maximized", False))

    @maximized.setter
    def maximized(self, value):
        self._values["maximized"] = bool(value)
        self._post(lambda: (self._app._window.maximize() if value
                            else self._app._window.restore()))

    @property
    def minimized(self):
        return (bool(self._native.user32.IsIconic(self.hwnd)) if self._native
                else self._values.get("minimized", False))

    @minimized.setter
    def minimized(self, value):
        self._values["minimized"] = bool(value)
        self._post(lambda: (self._app._window.minimize() if value
                            else self._app._window.restore()))

    @property
    def focused(self):
        window = getattr(self._app, "_window", None)
        return bool(window.focused) if window is not None else False

    @focused.setter
    def focused(self, value):
        if value:
            self._post(lambda: self._app._window.focus())
        elif self._native is not None:
            self._post(self._native.release_focus)

    @property
    def visible(self):
        return (bool(self._native.user32.IsWindowVisible(self.hwnd)) if self._native
                else self._values.get("visible", True))

    @visible.setter
    def visible(self, value):
        self._values["visible"] = bool(value)
        self._post(lambda: (self._app._window.show() if value
                            else self._app._window.hide()))

    @property
    def full_screen(self):
        return (self._native.is_full_screen() if self._native
                else self._values.get("full_screen", False))

    @full_screen.setter
    def full_screen(self, value):
        value = bool(value)
        self._values["full_screen"] = value
        def apply():
            changed = value != self.full_screen
            if not changed:
                return
            if value:
                self._app._window.set_fullscreen(desktop=True)
            else:
                self._app._window.set_windowed()
            self._app._frame_size = self._app._measure_frame_size()
            self._app._resize_frame(*self._app._window.size, present=False, dispatch=True)
            if changed:
                self._emit(WindowEventType.ENTER_FULL_SCREEN if value
                           else WindowEventType.LEAVE_FULL_SCREEN)
        self._post(apply)

    min_width = _setting("min_width", None, "_apply_limits", _positive)
    min_height = _setting("min_height", None, "_apply_limits", _positive)
    max_width = _setting("max_width", None, "_apply_limits", _positive)
    max_height = _setting("max_height", None, "_apply_limits", _positive)
    aspect_ratio = _setting("aspect_ratio", None, "_apply_limits", _positive, True)
    opacity = _setting("opacity", 1.0, "_apply_transparency", _unit)
    resizable = _setting("resizable", True, "_apply_resizable")
    minimizable = _setting("minimizable", True, "_apply_styles", windows_only=True)
    maximizable = _setting("maximizable", True, "_apply_styles", windows_only=True)
    movable = _setting("movable", True, windows_only=True)
    always_on_top = _setting("always_on_top", False, "_apply_stacking")
    always_on_bottom = _setting("always_on_bottom", False, "_apply_stacking", windows_only=True)
    prevent_close = _setting("prevent_close", False)
    skip_task_bar = _setting("skip_task_bar", False, "_apply_styles", windows_only=True)
    title_bar_hidden = _setting("title_bar_hidden", False, "_apply_styles", windows_only=True)
    title_bar_buttons_hidden = _setting("title_bar_buttons_hidden", False,
                                        "_apply_styles", windows_only=True)
    frameless = _setting("frameless", False, "_apply_frameless")
    shadow = _setting("shadow", True, "_apply_shadow", windows_only=True)
    ignore_mouse_events = _setting("ignore_mouse_events", False, "_apply_styles", windows_only=True)
    progress_bar = _setting("progress_bar", None, "_apply_progress",
                            lambda v: None if v is None else _unit(v), True)
    badge_label = _setting("badge_label", None, "_apply_badge",
                           lambda v: None if v is None else str(v), True)
    bgcolor = _setting("bgcolor", None, "_apply_background", _color)
    brightness = _setting("brightness", None, "_apply_brightness", _brightness)
    alignment = _setting("alignment", None, "_apply_alignment", _alignment)

    def _validate_setting(self, name, value):
        for minimum, maximum in (("min_width", "max_width"), ("min_height", "max_height")):
            low = value if name == minimum else getattr(self, minimum)
            high = value if name == maximum else getattr(self, maximum)
            if low is not None and high is not None and low > high:
                raise ValueError("minimum window size exceeds maximum size")
        if name in ("aspect_ratio", "min_width", "max_width", "min_height", "max_height"):
            settings = {field: value if field == name else getattr(self, field)
                        for field in ("aspect_ratio", "min_width", "max_width", "min_height", "max_height")}
            ratio = settings["aspect_ratio"]
            if ratio:
                low = max(settings["min_width"] or 1, (settings["min_height"] or 1) * ratio)
                high = min(settings["max_width"] or math.inf,
                           (settings["max_height"] or math.inf) * ratio)
                if low > high:
                    raise ValueError("size bounds cannot satisfy aspect_ratio")
        if name in ("always_on_top", "always_on_bottom") and value:
            other = "always_on_bottom" if name == "always_on_top" else "always_on_top"
            if getattr(self, other):
                raise ValueError("always_on_top and always_on_bottom are mutually exclusive")

    def _install_native(self):
        if sys.platform == "win32" and self.hwnd:
            from ._native_window import NativeWindow
            self._native = NativeWindow(self)

    def _apply_styles(self):
        if self._native:
            self._native.apply_styles()
            self._app._frame_size = self._app._measure_frame_size()
            # A style change alters the client/outer split without an SDL
            # resize, so take the new split from the actual rects before
            # anything re-derives sizes from the tracked (stale) values.
            outer = self._app._actual_outer_size()
            self._app._outer_size[:] = outer
            self._app._size[:] = self._app.client_size_for_outer(*outer)
            if not self._size_pending:
                # A queued resize target was clamped and frame-adjusted at
                # queue time and re-derives the client at apply time; don't
                # overwrite it with the pre-change size.
                self._apply_limits()

    def _apply_resizable(self):
        self._app._window.resizable = self.resizable
        self._apply_styles()

    def _apply_frameless(self):
        self._app._window.borderless = self.frameless
        self._apply_styles()

    def _apply_stacking(self):
        if self.always_on_top and self.always_on_bottom:
            raise ValueError("always_on_top and always_on_bottom are mutually exclusive")
        self._app._window.always_on_top = self.always_on_top
        self._apply_styles()

    def _apply_transparency(self):
        if self._native:
            self._native.apply_transparency()
        else:
            self._app._window.opacity = self.opacity

    def _apply_background(self):
        if self.bgcolor is not None:
            from .colors import parse_color
            parse_color(self.bgcolor)
        self._apply_transparency()
        if self.page:
            self.page.update()

    def _apply_brightness(self):
        if self.page:
            self.page._sync_native_title_bar()

    def _apply_shadow(self):
        if self._native:
            self._native.apply_shadow()

    def _apply_progress(self):
        if self._native:
            self._native.apply_progress()

    def _apply_badge(self):
        if self._native:
            self._native.apply_badge()

    def _normalize_size(self, width, height):
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        width, height = max(1, round(width)), max(1, round(height))
        for minimum, maximum in ((self.min_width, self.max_width),
                                 (self.min_height, self.max_height)):
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError("minimum window size exceeds maximum size")
        width = max(round(self.min_width or 1), width)
        height = max(round(self.min_height or 1), height)
        if self.max_width is not None:
            width = min(round(self.max_width), width)
        if self.max_height is not None:
            height = min(round(self.max_height), height)
        if self.aspect_ratio:
            low = max(self.min_width or 1, (self.min_height or 1) * self.aspect_ratio)
            high = min(self.max_width or math.inf,
                       (self.max_height or math.inf) * self.aspect_ratio)
            if low > high:
                raise ValueError("size bounds cannot satisfy aspect_ratio")
            width = round(min(high, max(low, width)))
            height = max(1, round(width / self.aspect_ratio))
        return width, height

    def _set_size(self, width, height):
        width, height = self._normalize_size(width, height)
        self._app._outer_size[:] = [width, height]
        client = self._app.client_size_for_outer(width, height)
        self._app._size[:] = client
        self._pending_size = (width, height)
        if self._size_pending:
            return
        self._size_pending = True
        self._post(self._apply_pending_size)

    def _apply_pending_size(self):
        if not self._size_pending:
            return
        if self._native is not None and self._native.user32.IsZoomed(self.hwnd):
            # Resizing a maximized window rewrites its saved restore bounds
            # instead of the visible size; keep the target queued until the
            # window is restored.
            return
        target = self._pending_size
        self._size_pending = False
        client = self._app.client_size_for_outer(*target)
        pixels = self._app.physical_size_for_logical(*client)
        if self._native is None or not self._set_native_client(pixels):
            self._app._window.size = pixels
        self._app._resize_frame(*pixels, present=False, dispatch=True)
        self._emit(WindowEventType.RESIZED)

    def _set_native_client(self, pixels):
        """Size the window so its client area lands exactly on `pixels`.

        SDL's SetWindowSize adds the frame AdjustWindowRectEx reports, which
        overshoots once WM_NCCALCSIZE hands that frame to the client area.
        Setting the Win32 outer rect from the frame measured at this instant
        stays exact across style changes.
        """
        rects = self._app._window_rects()
        if rects is None:
            return False
        outer, client = rects
        frame_w = (outer.right - outer.left) - (client.right - client.left)
        frame_h = (outer.bottom - outer.top) - (client.bottom - client.top)
        self._native.user32.SetWindowPos(
            self.hwnd, None, 0, 0,
            max(1, pixels[0] + frame_w), max(1, pixels[1] + frame_h),
            0x2 | 0x4 | 0x10)  # SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
        return True

    def _apply_limits(self):
        frame = self._app._frame_size
        ratio = self._app.pixel_ratio
        def client(value, border, default):
            return default if value is None else max(1, round((value - border) * ratio))
        minimum = (client(self.min_width, frame[0], 1), client(self.min_height, frame[1], 1))
        maximum = (client(self.max_width, frame[0], 0),
                   client(self.max_height, frame[1], 0))
        # SDL's SetWindowMinimumSize/MaximumSize always force a SetWindowSize
        # call, which re-applies the style frame and overshoots once
        # WM_NCCALCSIZE hands that frame to the client area. Skip SDL when
        # the limits are the defaults and re-apply only on change.
        applied = getattr(self, "_applied_limits", None)
        if applied != (minimum, maximum):
            if (self.min_width, self.min_height) != (None, None):
                self._app._window.minimum_size = minimum
            if (self.max_width, self.max_height) != (None, None):
                if self._native:
                    self._native.set_maximum_size(*maximum)
                else:
                    self._app._window.maximum_size = tuple(
                        value or 2147483647 for value in maximum)
            self._applied_limits = (minimum, maximum)
        self._set_size(*self._normalize_size(self.width, self.height))

    def _constrain_sizing(self, rect, edge):
        ratio = self._app.pixel_ratio
        width, height = rect.right - rect.left, rect.bottom - rect.top
        if edge in (3, 6):
            width = round(height * self.aspect_ratio)
        width, height = self._normalize_size(width / ratio, height / ratio)
        width, height = round(width * ratio), round(height * ratio)
        if edge in (1, 4, 7):
            rect.left = rect.right - width
        else:
            rect.right = rect.left + width
        if edge in (3, 4, 5):
            rect.top = rect.bottom - height
        else:
            rect.bottom = rect.top + height

    def _work_area(self):
        if self._native:
            import ctypes
            from ctypes import wintypes
            user = self._native.user32
            user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            user.MonitorFromWindow.restype = wintypes.HMONITOR
            class MonitorInfo(ctypes.Structure):
                _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                            ("work", wintypes.RECT), ("flags", wintypes.DWORD)]
            user.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.c_void_p]
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            monitor = user.MonitorFromWindow(self.hwnd, 2)
            if user.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return (info.work.left, info.work.top,
                        info.work.right - info.work.left, info.work.bottom - info.work.top)
        width, height = pygame.display.get_desktop_sizes()[0]
        return (0, 0, width, height)

    def _apply_alignment(self):
        if self.alignment is None:
            return
        align = self.alignment
        if not hasattr(align, "x") or not hasattr(align, "y"):
            raise TypeError("window.alignment must have x/y coordinates")
        left, top, width, height = self._work_area()
        w, h = self._app.physical_size_for_logical(self.width, self.height)
        x = left + round((width - w) * (max(-1, min(1, align.x)) + 1) / 2)
        y = top + round((height - h) * (max(-1, min(1, align.y)) + 1) / 2)
        self._app._window.position = (x, y)
        self._values["left"], self._values["top"] = (
            x / self._app.pixel_ratio, y / self._app.pixel_ratio)

    def _emit(self, kind):
        if kind is WindowEventType.RESIZED:
            size = self._app.outer_size
            if size == self._last_resize_event:
                return
            self._last_resize_event = size
        handlers = self.on_event
        if handlers is None:
            return
        event = WindowEvent(self, kind)
        for handler in ([handlers] if callable(handlers) else list(handlers)):
            self._app.call(_invoke, handler, event)

    def _handle_event(self, event):
        mapping = {
            pygame.WINDOWFOCUSGAINED: WindowEventType.FOCUS,
            pygame.WINDOWFOCUSLOST: WindowEventType.BLUR,
            pygame.WINDOWHIDDEN: WindowEventType.HIDE,
            pygame.WINDOWSHOWN: WindowEventType.SHOW,
            pygame.WINDOWMAXIMIZED: WindowEventType.MAXIMIZE,
            pygame.WINDOWMINIMIZED: WindowEventType.MINIMIZE,
            pygame.WINDOWRESTORED: WindowEventType.RESTORE,
            pygame.WINDOWMOVED: WindowEventType.MOVED,
        }
        kind = mapping.get(event.type)
        if kind is None:
            return
        if kind is WindowEventType.MOVED:
            self._values.pop("left", None)
            self._values.pop("top", None)
        elif kind is WindowEventType.MAXIMIZE:
            self._values.update(maximized=True, minimized=False)
        elif kind is WindowEventType.MINIMIZE:
            self._values["minimized"] = True
        elif kind is WindowEventType.RESTORE:
            was_maximized = self._values.get("maximized", False)
            self._values.update(maximized=False, minimized=False)
            if was_maximized:
                self._emit(WindowEventType.UNMAXIMIZE)
            self._post(self._apply_pending_size)
        self._emit(kind)

    def _request_close(self):
        self._emit(WindowEventType.CLOSE)
        if not self.prevent_close:
            self._app.close()

    def close(self):
        """Request closing; respects prevent_close and emits CLOSE."""
        self._post(self._request_close)

    def destroy(self):
        """Force application shutdown even when prevent_close is set."""
        self._app.close()

    async def center(self):
        from .types import Alignment
        self.alignment = Alignment.CENTER

    async def wait_until_ready_to_show(self):
        event = asyncio.Event()
        loop = asyncio.get_running_loop()
        self._post(lambda: loop.call_soon_threadsafe(event.set))
        await event.wait()

    async def to_front(self):
        self._post(lambda: self._app._window.focus())

    async def start_dragging(self):
        if sys.platform != "win32":
            raise NotImplementedError("native dragging currently requires Windows")
        if self.movable:
            self._post(lambda: self._native.start_interaction(2))

    async def start_resizing(self, edge):
        if sys.platform != "win32":
            raise NotImplementedError("native resizing currently requires Windows")
        edge = edge if isinstance(edge, WindowResizeEdge) else WindowResizeEdge(edge)
        hits = {WindowResizeEdge.LEFT: 10, WindowResizeEdge.RIGHT: 11,
                WindowResizeEdge.TOP: 12, WindowResizeEdge.TOP_LEFT: 13,
                WindowResizeEdge.TOP_RIGHT: 14, WindowResizeEdge.BOTTOM: 15,
                WindowResizeEdge.BOTTOM_LEFT: 16, WindowResizeEdge.BOTTOM_RIGHT: 17}
        if self.resizable:
            self._post(lambda: self._native.start_interaction(hits[edge]))

    def _dispose(self):
        if self._native is not None:
            self._native.close()
            self._native = None
