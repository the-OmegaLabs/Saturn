"""Small Win32 adapter for native capabilities not exposed by SDL."""
from __future__ import annotations

import ctypes
import sys
import uuid
from pathlib import Path
from ctypes import wintypes


class _GUID(ctypes.Structure):
    _fields_ = [("data", ctypes.c_ubyte * 16)]

    @classmethod
    def parse(cls, value):
        return cls((ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID(value).bytes_le))


class _WindowPos(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("after", wintypes.HWND),
                ("x", ctypes.c_int), ("y", ctypes.c_int),
                ("width", ctypes.c_int), ("height", ctypes.c_int),
                ("flags", ctypes.c_uint)]


class NativeWindow:
    _window_event_type = None  # cached on first message; import here is too slow

    def __init__(self, owner):
        self.owner = owner
        self.hwnd = owner.hwnd
        self.callback = None
        self.taskbar = None
        self.badge_icon = None
        self._com_initialized = False
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.dwm = ctypes.WinDLL("dwmapi")
        self.comctl = ctypes.WinDLL("comctl32")
        import pygame
        self.sdl = ctypes.CDLL(str(Path(pygame.__file__).with_name("SDL2.dll")))
        self.sdl.SDL_GetWindowFromID.argtypes = [ctypes.c_uint32]
        self.sdl.SDL_GetWindowFromID.restype = ctypes.c_void_p
        self.sdl.SDL_GetWindowFlags.argtypes = [ctypes.c_void_p]
        self.sdl.SDL_GetWindowFlags.restype = ctypes.c_uint32
        self.sdl.SDL_SetWindowMaximumSize.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        self.sdl.SDL_SetWindowMaximumSize.restype = None
        self.sdl_window = self.sdl.SDL_GetWindowFromID(owner._app._window.id)
        self.get_style = getattr(self.user32, "GetWindowLongPtrW", self.user32.GetWindowLongW)
        self.set_style = getattr(self.user32, "SetWindowLongPtrW", self.user32.SetWindowLongW)
        self.get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        self.get_style.restype = ctypes.c_ssize_t
        self.set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        self.set_style.restype = ctypes.c_ssize_t
        self.user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        self.user32.SetWindowPos.restype = wintypes.BOOL
        self.user32.IsIconic.argtypes = [wintypes.HWND]
        self.user32.IsZoomed.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.SetLayeredWindowAttributes.argtypes = [
            wintypes.HWND, wintypes.DWORD, ctypes.c_ubyte, wintypes.DWORD]
        self.user32.SendMessageW.argtypes = [wintypes.HWND, ctypes.c_uint,
            ctypes.c_size_t, ctypes.c_ssize_t]
        self.user32.SendMessageW.restype = ctypes.c_ssize_t
        self.user32.ReleaseCapture.argtypes = []
        self._install_subclass()

    def _install_subclass(self):
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND,
            ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t,
            ctypes.c_size_t, ctypes.c_size_t)
        self.comctl.DefSubclassProc.argtypes = [wintypes.HWND, ctypes.c_uint,
            ctypes.c_size_t, ctypes.c_ssize_t]
        self.comctl.DefSubclassProc.restype = ctypes.c_ssize_t

        @callback_type
        def callback(hwnd, message, wparam, lparam, _id, _data):
            try:
                event_type = NativeWindow._window_event_type
                if event_type is None:
                    from .window import WindowEventType
                    event_type = NativeWindow._window_event_type = WindowEventType
                if message == 0x0083 and wparam and self.owner.title_bar_hidden:
                    # WM_NCCALCSIZE: hand the entire window to the client area.
                    # For resizable windows, WM_NCHITTEST will provide manual
                    # border hit testing to enable resizing.
                    rect = ctypes.cast(lparam, ctypes.POINTER(wintypes.RECT)).contents
                    if self.user32.IsZoomed(hwnd):
                        # A maximized thickframe window extends past the
                        # monitor by the border width; inset the client so
                        # the content stays on-screen.
                        added = self.user32.GetSystemMetrics(92)  # SM_CXPADDEDBORDER
                        rect.left += self.user32.GetSystemMetrics(32) + added
                        rect.top += self.user32.GetSystemMetrics(33) + added
                        rect.right -= self.user32.GetSystemMetrics(32) + added
                        rect.bottom -= self.user32.GetSystemMetrics(33) + added
                    return 0
                if (message in (0x0086, 0x0085)  # WM_NCACTIVATE, WM_NCPAINT
                        and (self.owner.title_bar_hidden or self.owner.frameless)):
                    # DefWindowProc repaints the cached caption on activation
                    # changes, flashing a ghost title bar even though
                    # WM_NCCALCSIZE removed it. The window owns every pixel,
                    # so the non-client area is never painted.
                    return 0
                if message == 0x0046 and self.owner.always_on_bottom:
                    position = ctypes.cast(lparam, ctypes.POINTER(_WindowPos)).contents
                    position.after = 1  # HWND_BOTTOM
                    position.flags = (position.flags & ~4) | 0x10
                if message == 0x0112 and (wparam & 0xFFF0) == 0xF010:
                    if not self.owner.movable:
                        return 0  # WM_SYSCOMMAND / SC_MOVE
                if message == 0x0214:
                    self.owner._emit(event_type.RESIZE)
                    if self.owner.aspect_ratio:
                        rect = ctypes.cast(lparam, ctypes.POINTER(wintypes.RECT)).contents
                        self.owner._constrain_sizing(rect, wparam)
                        return 1  # WM_SIZING
                if message == 0x0216:
                    self.owner._emit(event_type.MOVE)
                if (message == 0x0084 and self.owner.title_bar_hidden
                        and not self.owner.frameless
                        and not self.user32.IsZoomed(hwnd)
                        and not self.owner.full_screen
                        and self.owner.resizable):
                    # WM_NCHITTEST: with WM_NCCALCSIZE handing the whole
                    # window to the client area, DefWindowProc reports
                    # HTCLIENT everywhere and the resize borders die. Point
                    # at the border zones by hand, like a captioned window.
                    # Only do this if the window is actually resizable.
                    x = ctypes.c_short(lparam & 0xFFFF).value
                    y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
                    rect = wintypes.RECT()
                    if self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                        border = (self.user32.GetSystemMetrics(32)
                                  + self.user32.GetSystemMetrics(92))
                        left = x - rect.left < border
                        top = y - rect.top < border
                        right = rect.right - x <= border
                        bottom = rect.bottom - y <= border
                        if top and left:
                            return 13  # HTTOPLEFT
                        if top and right:
                            return 14  # HTTOPRIGHT
                        if bottom and left:
                            return 16  # HTBOTTOMLEFT
                        if bottom and right:
                            return 17  # HTBOTTOMRIGHT
                        if left:
                            return 10  # HTLEFT
                        if top:
                            return 12  # HTTOP
                        if right:
                            return 11  # HTRIGHT
                        if bottom:
                            return 15  # HTBOTTOM
                result = self.comctl.DefSubclassProc(hwnd, message, wparam, lparam)
                if message == 0x0084 and self.owner.ignore_mouse_events:
                    return -1  # WM_NCHITTEST / HTTRANSPARENT
                return result
            except Exception as e:
                # Window message callback must never leak exceptions to Windows
                import traceback
                print(f"Native window callback error: {e}", file=sys.stderr)
                traceback.print_exc()
                return self.comctl.DefSubclassProc(hwnd, message, wparam, lparam)

        self.comctl.SetWindowSubclass.argtypes = [wintypes.HWND, callback_type,
            ctypes.c_size_t, ctypes.c_size_t]
        self.comctl.SetWindowSubclass.restype = wintypes.BOOL
        self.comctl.RemoveWindowSubclass.argtypes = [wintypes.HWND, callback_type,
            ctypes.c_size_t]
        self.comctl.RemoveWindowSubclass.restype = wintypes.BOOL
        if not self.comctl.SetWindowSubclass(self.hwnd, callback, 0x534154, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        self.callback = callback

    def apply_styles(self):
        owner = self.owner
        style = self.get_style(self.hwnd, -16)
        # Keep WS_CAPTION (0xC00000) for DWM animations, remove only for frameless
        for bit, enabled in ((0x20000, owner.minimizable),
                             (0x10000, owner.maximizable),
                             (0x40000, owner.resizable and not owner.frameless),
                             (0xC00000, not owner.frameless),  # Keep caption for DWM animations
                             # Keep WS_SYSMENU for resizable windows even with hidden title bar
                             # to ensure resize operations work correctly
                             (0x80000, (not owner.title_bar_buttons_hidden and not owner.title_bar_hidden)
                                       or (owner.resizable and owner.title_bar_hidden))):
            style = (style | bit) if enabled else (style & ~bit)
        self.set_style(self.hwnd, -16, style)
        extended = self.get_style(self.hwnd, -20)
        if owner.skip_task_bar:
            extended = (extended | 0x80) & ~0x40000
        else:
            extended = (extended | 0x40000) & ~0x80
        extended = ((extended | 0x20) if owner.ignore_mouse_events
                    else (extended & ~0x20))
        self.set_style(self.hwnd, -20, extended)
        self.user32.SetWindowPos(self.hwnd, None, 0, 0, 0, 0, 0x37)
        if owner.title_bar_hidden:
            # A window without WS_CAPTION loses DWM's rounded corners; opt
            # back in (attribute 33 is Win11+; errors on Win10 are fine).
            preference = ctypes.c_int(2)  # DWMWCP_ROUND
            self.dwm.DwmSetWindowAttribute(self.hwnd, 33,
                                           ctypes.byref(preference),
                                           ctypes.sizeof(preference))
        # Enable DWM transitions (animations for minimize/maximize/close)
        # DWMWA_TRANSITIONS_FORCEDISABLED = 3, FALSE = 0 means enabled
        transitions = ctypes.c_int(0)
        self.dwm.DwmSetWindowAttribute(self.hwnd, 3,
                                       ctypes.byref(transitions),
                                       ctypes.sizeof(transitions))
        if owner.always_on_bottom:
            self.user32.SetWindowPos(self.hwnd, ctypes.c_void_p(1),
                                     0, 0, 0, 0, 0x13)
        self.apply_transparency()

    def apply_transparency(self):
        from .colors import parse_color
        owner = self.owner
        color = parse_color(owner.bgcolor) if owner.bgcolor is not None else None
        keyed = color is not None and color[3] == 0
        layered = keyed or owner.opacity < 1 or owner.ignore_mouse_events
        style = self.get_style(self.hwnd, -20)
        style = (style | 0x80000) if layered else (style & ~0x80000)
        self.set_style(self.hwnd, -20, style)
        if layered:
            key = color[0] | (color[1] << 8) | (color[2] << 16) if keyed else 0
            if not self.user32.SetLayeredWindowAttributes(
                    self.hwnd, key, round(owner.opacity * 255), 2 | int(keyed)):
                raise ctypes.WinError(ctypes.get_last_error())

    def apply_shadow(self):
        self.dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                                  ctypes.c_void_p, wintypes.DWORD]
        policy = ctypes.c_int(2 if self.owner.shadow else 1)
        result = self.dwm.DwmSetWindowAttribute(self.hwnd, 2,
                                               ctypes.byref(policy), ctypes.sizeof(policy))
        if result < 0:
            raise OSError(f"DWM shadow configuration failed: 0x{result & 0xffffffff:08x}")

    def set_maximum_size(self, width, height):
        # SDL uses zero for an unconstrained dimension. pygame's setter
        # rejects zero whenever a minimum size is active.
        self.sdl.SDL_SetWindowMaximumSize(self.sdl_window, width, height)

    def is_full_screen(self):
        return bool(self.sdl.SDL_GetWindowFlags(self.sdl_window) & 1)

    def start_interaction(self, hit):
        self.user32.ReleaseCapture()
        self.user32.SendMessageW(self.hwnd, 0x00A1, hit, 0)

    def release_focus(self):
        user = self.user32
        user.GetWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
        user.GetWindow.restype = wintypes.HWND
        user.SetForegroundWindow.argtypes = [wintypes.HWND]
        target = user.GetWindow(self.hwnd, 2)
        while target and not user.IsWindowVisible(target):
            target = user.GetWindow(target, 2)
        if target:
            user.SetForegroundWindow(target)

    def _taskbar_call(self, index, argtypes, *args):
        vtable = ctypes.cast(self.taskbar, ctypes.POINTER(
            ctypes.POINTER(ctypes.c_void_p))).contents
        method = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(vtable[index])
        result = method(self.taskbar, *args)
        if result < 0:
            raise OSError(f"Taskbar operation failed: 0x{result & 0xffffffff:08x}")

    def _ensure_taskbar(self):
        if self.taskbar is not None:
            return
        ole = ctypes.WinDLL("ole32")
        ole.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        ole.CoInitializeEx.restype = ctypes.c_long
        result = ole.CoInitializeEx(None, 2)
        self._com_initialized = result >= 0
        if result < 0 and (result & 0xffffffff) != 0x80010106:
            raise OSError(f"COM initialization failed: 0x{result & 0xffffffff:08x}")
        clsid = _GUID.parse("56fdf344-fd6d-11d0-958a-006097c9a090")
        iid = _GUID.parse("ea1afb91-9e28-4b86-90e9-9e9f8a5eefaf")
        pointer = ctypes.c_void_p()
        ole.CoCreateInstance.argtypes = [ctypes.POINTER(_GUID), ctypes.c_void_p,
            ctypes.c_uint, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)]
        ole.CoCreateInstance.restype = ctypes.c_long
        result = ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid),
                                       ctypes.byref(pointer))
        if result < 0:
            raise OSError(f"Taskbar initialization failed: 0x{result & 0xffffffff:08x}")
        self.taskbar = pointer
        self._taskbar_call(3, [])  # HrInit

    def apply_progress(self):
        self._ensure_taskbar()
        value = self.owner.progress_bar
        self._taskbar_call(10, [wintypes.HWND, ctypes.c_uint], self.hwnd,
                           0 if value is None else 2)
        if value is not None:
            self._taskbar_call(9, [wintypes.HWND, ctypes.c_ulonglong,
                ctypes.c_ulonglong], self.hwnd, round(value * 1000), 1000)

    def apply_badge(self):
        self._ensure_taskbar()
        label = self.owner.badge_label
        new_icon = self._badge_icon(label) if label else None
        self._taskbar_call(18, [wintypes.HWND, wintypes.HICON, wintypes.LPCWSTR],
                           self.hwnd, new_icon, label or "")
        if self.badge_icon:
            self.user32.DestroyIcon(self.badge_icon)
        self.badge_icon = new_icon

    def _badge_icon(self, label):
        import pygame
        from . import text
        from .colors import parse_color

        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(surface, (190, 35, 45, 255), (16, 16), 15)
        glyph = text.render_line(str(label)[:3], 12, scale=1,
                                 color=parse_color("#FFFFFF"))
        if glyph.get_width() > 28:
            glyph = pygame.transform.smoothscale(glyph, (28, glyph.get_height()))
        surface.blit(glyph, ((32 - glyph.get_width()) // 2,
                             (32 - glyph.get_height()) // 2))

        class Header(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("width", wintypes.LONG),
                ("height", wintypes.LONG), ("planes", wintypes.WORD),
                ("bits", wintypes.WORD), ("compression", wintypes.DWORD),
                ("image_size", wintypes.DWORD), ("xppm", wintypes.LONG),
                ("yppm", wintypes.LONG), ("used", wintypes.DWORD),
                ("important", wintypes.DWORD)]

        class IconInfo(ctypes.Structure):
            _fields_ = [("icon", wintypes.BOOL), ("x", wintypes.DWORD),
                ("y", wintypes.DWORD), ("mask", wintypes.HBITMAP),
                ("color", wintypes.HBITMAP)]

        gdi = ctypes.WinDLL("gdi32")
        gdi.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p,
            ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
        gdi.CreateDIBSection.restype = wintypes.HBITMAP
        gdi.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint,
                                     ctypes.c_uint, ctypes.c_void_p]
        gdi.CreateBitmap.restype = wintypes.HBITMAP
        gdi.DeleteObject.argtypes = [wintypes.HANDLE]
        header = Header(ctypes.sizeof(Header), 32, -32, 1, 32, 0, 4096, 0, 0, 0, 0)
        pixels = ctypes.c_void_p()
        color = gdi.CreateDIBSection(None, ctypes.byref(header), 0,
                                     ctypes.byref(pixels), None, 0)
        if not color:
            raise ctypes.WinError(ctypes.get_last_error())
        data = pygame.image.tobytes(surface, "BGRA")
        ctypes.memmove(pixels, data, len(data))
        mask = gdi.CreateBitmap(32, 32, 1, 1, None)
        self.user32.CreateIconIndirect.argtypes = [ctypes.POINTER(IconInfo)]
        self.user32.CreateIconIndirect.restype = wintypes.HICON
        self.user32.DestroyIcon.argtypes = [wintypes.HICON]
        try:
            icon = self.user32.CreateIconIndirect(ctypes.byref(IconInfo(True, 0, 0, mask, color)))
            if not icon:
                raise ctypes.WinError(ctypes.get_last_error())
            return icon
        finally:
            gdi.DeleteObject(mask)
            gdi.DeleteObject(color)

    def close(self):
        if self.callback is not None:
            self.comctl.RemoveWindowSubclass(self.hwnd, self.callback, 0x534154)
            self.callback = None
        if self.badge_icon:
            self.user32.DestroyIcon(self.badge_icon)
            self.badge_icon = None
        if self.taskbar:
            self._taskbar_call(2, [])  # IUnknown.Release
            self.taskbar = None
        if self._com_initialized:
            ctypes.OleDLL("ole32").CoUninitialize()
            self._com_initialized = False
