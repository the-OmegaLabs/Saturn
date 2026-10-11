"""Windows platform adapter.

All Win32 and Windows-specific SDL event-watch code lives here.  The portable
``saturn.app``, ``saturn.window`` and ``saturn.page`` modules call this
adapter through the methods defined in :mod:`saturn.platform.base`.
"""
from __future__ import annotations

import ctypes
import sys
import time
import threading
from pathlib import Path
from ctypes import wintypes

import pygame

from .base import PlatformAdapter, PlatformCapabilities
from .windows_native import NativeWindow


class WindowsPlatform(PlatformAdapter):
    name = "windows"
    is_windows = True
    capabilities = PlatformCapabilities(
        native_window=True,
        hwnd=True,
        native_window_dragging=True,
        native_window_resizing=True,
        window_frame_metrics=True,
        live_resize_watch=True,
        dark_title_bar=True,
        modal_owner=True,
        module_watch=True,
    )

    _window_features = frozenset({
        "aspect_ratio", "minimizable", "maximizable", "movable",
        "always_on_bottom", "skip_task_bar", "title_bar_hidden",
        "title_bar_buttons_hidden", "shadow", "ignore_mouse_events",
        "progress_bar", "badge_label",
    })

    def __init__(self):
        self._resize_watches = {}
        self._last_resize_frames = {}

    def supports_window_feature(self, name: str) -> bool:
        return name in self._window_features or self.supports(name)

    def prepare_environment(self) -> None:
        super().prepare_environment()
        # SDL must opt into Per-Monitor V2 before initializing the video
        # subsystem. Other platforms simply ignore this Windows setting.
        import os
        os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")

    def create_native_window(self, owner):
        if owner.hwnd:
            return NativeWindow(owner)
        return None

    def create_gl_gpu_binding(self, context, gpu):
        from .windows_gl import WindowsGLBinding
        return WindowsGLBinding(context, gpu)

    def system_pixel_ratio(self) -> float:
        try:
            dpi = int(ctypes.windll.user32.GetDpiForSystem())
            return max(1.0, dpi / 96.0) if dpi > 0 else 1.0
        except (AttributeError, OSError, TypeError, ValueError):
            return 1.0

    def system_prefers_dark(self) -> bool:
        try:
            import winreg
            with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
        except (OSError, AttributeError, TypeError, ValueError):
            return False

    def snapshot_modules(self) -> list[str]:
        # Keep module enumeration in the Windows adapter; the watchdog itself
        # should not know about PSAPI or ctypes.WinDLL.
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.EnumProcessModulesEx.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), wintypes.DWORD,
        ]
        psapi.GetModuleFileNameExW.argtypes = [
            wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD,
        ]
        psapi.GetModuleFileNameExW.restype = wintypes.DWORD

        handle = kernel32.GetCurrentProcess()
        size = 256
        for _ in range(4):
            buf = (wintypes.HMODULE * size)()
            needed = wintypes.DWORD()
            if not psapi.EnumProcessModulesEx(
                    handle, buf, ctypes.sizeof(buf), ctypes.byref(needed), 0x03):
                return []
            count = needed.value // ctypes.sizeof(wintypes.HMODULE)
            if count <= size:
                out = []
                for index in range(count):
                    name = ctypes.create_unicode_buffer(512)
                    length = psapi.GetModuleFileNameExW(handle, buf[index], name, 512)
                    if length:
                        out.append(name.value.lower())
                return out
            size = count
        return []

    def window_pixel_ratio(self, handle: int) -> float:
        if not handle:
            return self.system_pixel_ratio()
        try:
            dpi = int(ctypes.windll.user32.GetDpiForWindow(handle))
            return max(1.0, dpi / 96.0) if dpi > 0 else 1.0
        except (AttributeError, OSError, TypeError, ValueError):
            return self.system_pixel_ratio()

    def set_default_window_icon(self, window) -> bool:
        # Accept an HWND too for the compatibility helper kept in
        # ``saturn.app``; the normal runtime passes pygame's Window object.
        hwnd = int(window) if isinstance(window, int) else self.hwnd(window)
        if not hwnd:
            return False
        try:
            user32 = ctypes.windll.user32
            user32.LoadIconW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            user32.LoadIconW.restype = ctypes.c_void_p
            user32.SendMessageW.argtypes = [
                ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t,
            ]
            user32.SendMessageW.restype = ctypes.c_ssize_t
            # IDI_APPLICATION is a shared system resource and must not be freed.
            icon = user32.LoadIconW(None, ctypes.c_void_p(32512))
            if not icon:
                return False
            wm_seticon = 0x0080
            user32.SendMessageW(hwnd, wm_seticon, 0, icon)  # ICON_SMALL
            user32.SendMessageW(hwnd, wm_seticon, 1, icon)  # ICON_BIG
            return True
        except (AttributeError, OSError, TypeError, ValueError):
            return False

    def window_rects(self, window):
        if window is None:
            return None
        try:
            hwnd = window.handle
            outer = wintypes.RECT()
            client = wintypes.RECT()
            user32 = ctypes.windll.user32
            user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            user32.GetWindowRect.restype = wintypes.BOOL
            user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            user32.GetClientRect.restype = wintypes.BOOL
            if not user32.GetWindowRect(hwnd, ctypes.byref(outer)):
                return None
            if not user32.GetClientRect(hwnd, ctypes.byref(client)):
                return None
            return outer, client
        except (AttributeError, KeyError, OSError, TypeError, ValueError, pygame.error):
            return None

    def work_area(self, window):
        native = getattr(window, "_native", None)
        if native is not None:
            user = native.user32
            user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            user.MonitorFromWindow.restype = wintypes.HMONITOR

            class MonitorInfo(ctypes.Structure):
                _fields_ = [
                    ("size", wintypes.DWORD),
                    ("monitor", wintypes.RECT),
                    ("work", wintypes.RECT),
                    ("flags", wintypes.DWORD),
                ]

            user.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.c_void_p]
            user.GetMonitorInfoW.restype = wintypes.BOOL
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            monitor = user.MonitorFromWindow(window.hwnd, 2)  # MONITOR_DEFAULTTONEAREST
            if monitor and user.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return (
                    info.work.left,
                    info.work.top,
                    info.work.right - info.work.left,
                    info.work.bottom - info.work.top,
                )
        return super().work_area(window)

    def set_dark_title_bar(self, hwnd: int, dark: bool) -> bool:
        if not hwnd:
            return False
        try:
            dwmapi = ctypes.windll.dwmapi
            set_attribute = dwmapi.DwmSetWindowAttribute
            set_attribute.argtypes = [
                ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint,
            ]
            set_attribute.restype = ctypes.c_long
            enabled = ctypes.c_int(1 if dark else 0)
            # Windows 10 20H1+ uses 20; earlier Windows 10 used 19.
            applied = any(
                set_attribute(
                    ctypes.c_void_p(hwnd), attribute,
                    ctypes.byref(enabled), ctypes.sizeof(enabled),
                ) == 0
                for attribute in (20, 19)
            )
            if applied:
                # Recalculate the non-client frame after a live theme change.
                ctypes.windll.user32.SetWindowPos(
                    ctypes.c_void_p(hwnd), None, 0, 0, 0, 0,
                    0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020,
                )
            return applied
        except (AttributeError, OSError, TypeError, ValueError):
            return False

    def set_window_owner(self, child_hwnd: int, parent_hwnd: int, modal: bool) -> bool:
        if not child_hwnd or not parent_hwnd:
            return False
        user = ctypes.windll.user32
        setter = user.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user.SetWindowLongW
        setter.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        setter.restype = ctypes.c_void_p
        setter(child_hwnd, -8, parent_hwnd)  # GWLP_HWNDPARENT
        if modal:
            self.enable_window(parent_hwnd, False)
        return True

    def enable_window(self, hwnd: int, enabled: bool) -> bool:
        if not hwnd:
            return False
        user = ctypes.windll.user32
        user.EnableWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
        user.EnableWindow.restype = wintypes.BOOL
        user.EnableWindow(hwnd, bool(enabled))
        return True

    def install_live_resize_watch(self, app) -> None:
        """Redraw during the Win32 modal move/size loop.

        pygame does not expose SDL_AddEventWatch, so this hook binds the SDL2
        library bundled with pygame.  The callback remains owned by ``app``
        through the two legacy state fields until the watch is removed.
        """
        key = id(app)
        if key in self._resize_watches or app._window is None or app._closed.is_set():
            return
        try:
            dll = ctypes.CDLL(str(Path(pygame.__file__).with_name("SDL2.dll")))

            class SDLWindowEvent(ctypes.Structure):
                _fields_ = [
                    ("type", ctypes.c_uint32), ("timestamp", ctypes.c_uint32),
                    ("window_id", ctypes.c_uint32), ("event", ctypes.c_uint8),
                    ("padding1", ctypes.c_uint8), ("padding2", ctypes.c_uint8),
                    ("padding3", ctypes.c_uint8), ("data1", ctypes.c_int32),
                    ("data2", ctypes.c_int32),
                ]

            class SDLEvent(ctypes.Union):
                _fields_ = [
                    ("type", ctypes.c_uint32),
                    ("window", SDLWindowEvent),
                    ("padding", ctypes.c_uint8 * 56),
                ]

            callback_type = ctypes.CFUNCTYPE(
                ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(SDLEvent),
            )
            window_id = app._window.id

            @callback_type
            def watch(_userdata, event_ptr):
                if threading.get_ident() != app._ui_thread or app._closed.is_set():
                    return 1
                event = event_ptr.contents
                # SDL2: WINDOWEVENT=0x200; RESIZED=5; SIZE_CHANGED=6.
                if (event.type == 0x200 and event.window.window_id == window_id
                        and event.window.event in (5, 6)):
                    size = (event.window.data1, event.window.data2)
                    now = time.perf_counter()
                    last = self._last_resize_frames.get(key, 0.0)
                    if size != tuple(app._size) or now - last > 0.1:
                        self._last_resize_frames[key] = now
                        try:
                            app._resize_frame(*size, present=True, dispatch=True)
                        except (RuntimeError, ValueError, AttributeError) as error:
                            # ctypes callbacks must never leak exceptions into SDL.
                            print(f"Resize frame error: {error}", file=sys.stderr)
                            import traceback
                            traceback.print_exc()
                return 1

            dll.SDL_AddEventWatch.argtypes = [callback_type, ctypes.c_void_p]
            dll.SDL_AddEventWatch.restype = None
            dll.SDL_DelEventWatch.argtypes = [callback_type, ctypes.c_void_p]
            dll.SDL_DelEventWatch.restype = None
            dll.SDL_AddEventWatch(watch, None)
            self._resize_watches[key] = (dll, watch)
        except (AttributeError, OSError):
            self._resize_watches.pop(key, None)
            self._last_resize_frames.pop(key, None)

    def remove_live_resize_watch(self, app) -> None:
        key = id(app)
        watch = self._resize_watches.pop(key, None)
        if watch is not None:
            dll, callback = watch
            dll.SDL_DelEventWatch(callback, None)
        self._last_resize_frames.pop(key, None)
