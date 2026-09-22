"""Window, event loop and threading model.

Thread rules:
- The thread that calls run() owns the window: it pumps SDL events, re-layouts
  and redraws when dirty, then presents at the active display refresh rate.
- main(page) and every event handler run off the UI thread (sync -> daemon
  thread, async -> the app's asyncio loop), so blocking handlers never freeze
  the window. Control state changes from those threads are only safe between
  update() calls; update() just raises the dirty flag.
"""
from __future__ import annotations

import asyncio
import ctypes
import enum
import inspect
import os
import queue
import sys
import threading
import time
from pathlib import Path

import pygame

from .renderer import create_renderer
from .renderer.base import Renderer


class Render(enum.Enum):
    """Rendering backend."""
    SOFTWARE = "software"
    OPENGL = "opengl"
    VULKAN = "vulkan"  # placeholder, see TODO

def _system_refresh_rate() -> int:
    """Return the active display refresh rate, with a conservative fallback."""
    try:
        rate = int(pygame.display.get_current_refresh_rate())
        if rate > 0:
            return rate
    except (AttributeError, pygame.error, TypeError, ValueError):
        pass
    try:
        rates = pygame.display.get_desktop_refresh_rates()
        if rates and int(rates[0]) > 0:
            return int(rates[0])
    except (AttributeError, pygame.error, TypeError, ValueError):
        pass
    return 60


def _set_windows_default_icon(hwnd: int) -> bool:
    """Apply Windows' shared generic application icon to an HWND."""
    if sys.platform != "win32" or not hwnd:
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


def _set_gl_swap_interval(interval: int = 1) -> bool:
    """Request v-sync for the current SDL OpenGL context."""
    try:
        dll = ctypes.CDLL(str(Path(pygame.__file__).with_name("SDL2.dll")))
        dll.SDL_GL_SetSwapInterval.argtypes = [ctypes.c_int]
        dll.SDL_GL_SetSwapInterval.restype = ctypes.c_int
        return dll.SDL_GL_SetSwapInterval(interval) == 0
    except (AttributeError, OSError):
        return False


class App:
    def __init__(self, main, backend: Render, width: int, height: int, title: str):
        self._main = main
        self._backend = backend
        # Flet Window.width/height describe the native outer window. Page
        # width/height describe the drawable client area. SDL's Window.size
        # is client-only, so keep the two coordinate spaces separate.
        self._outer_size = [int(width), int(height)]
        self._size = list(self._outer_size)
        self._frame_size = (0, 0)
        self._title = title
        self._dirty = threading.Event()
        self._closed = threading.Event()
        self._ui_q: queue.SimpleQueue = queue.SimpleQueue()
        # background loop for async handlers / main coroutines
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True,
                         name="saturn-async").start()
        self.renderer: Renderer | None = None
        self.page = None  # set in start()
        self._live_resize_dll = None
        self._live_resize_callback = None
        self._last_live_resize_frame = 0.0
        self._last_resize_dispatched_size = None
        self._refresh_rate = 60
        self._window_icon = None

    # -- lifecycle ------------------------------------------------------
    def start(self):
        pygame.init()
        if self._backend is Render.OPENGL:
            pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
        self._window = pygame.Window(
            title=self._title,
            size=tuple(self._size),
            resizable=True,
            opengl=self._backend is Render.OPENGL,
        )
        if self._backend is Render.OPENGL:
            _set_gl_swap_interval(1)
        self._refresh_rate = _system_refresh_rate()
        self._apply_default_window_icon()
        self._frame_size = self._measure_frame_size()
        client = self.client_size_for_outer(*self._outer_size)
        if tuple(self._window.size) != client:
            self._window.size = client
        self._size[:] = client
        self.renderer = create_renderer(self._backend, self._window)
        # SDL/pygame can retain the set_mode creation size after the native
        # Window client area is adjusted for Flet's outer-size semantics.
        # Seed every renderer from the authoritative final client size so
        # GL's viewport/scissor and screenshot dimensions match SOFTWARE.
        self.renderer.on_resize(*client)
        from .page import Page  # deferred: page imports app bits
        self.page = Page(self)
        from . import text as _text
        _text.on_weight_ready = self.mark_dirty  # Regular -> real weight swap
        autoclose = os.environ.get("SATURN_AUTOCLOSE")  # test hook
        if autoclose:
            threading.Timer(float(autoclose), self.close).start()
        shot = os.environ.get("SATURN_SHOT")  # test hook: save a frame
        if shot:
            threading.Timer(2.0, lambda: _swallow(self.screenshot, shot)).start()
        threading.Thread(target=self.call, args=(self._main, self.page),
                         daemon=True, name="saturn-main").start()
        self._dirty.set()

    def close(self):
        self._closed.set()

    def run_until_closed(self):
        # Bind the SDL watcher to the actual event-loop lifetime. Some unit
        # tests use start() only and create several displays in one process;
        # leaving a watcher attached across those displays is unsafe.
        self._install_live_resize_watch()
        clock = pygame.time.Clock()
        while not self._closed.is_set():
            # drain display-mutation commands from worker threads: SDL video
            # calls are main-thread-only, calling them from workers deadlocks
            while True:
                try:
                    self._ui_q.get_nowait()()
                except queue.Empty:
                    break
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                    self._closed.set()
                elif e.type == pygame.WINDOWRESIZED:
                    self._resize_frame(e.x, e.y, present=False, dispatch=True)
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.page.pointer_down(*e.pos)
                elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                    self.page.pointer_up(*e.pos)
                elif e.type == pygame.MOUSEMOTION:
                    self.page.pointer_move(*e.pos)
                elif e.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT,
                                pygame.TEXTEDITING, pygame.MOUSEWHEEL):
                    self.page.handle_event(e)
                else:
                    self.page.handle_event(e)
            if self._dirty.is_set():
                self._dirty.clear()
                self.page.draw()
                self.renderer.flip()
            # Do not assume a 60 Hz monitor. OpenGL's swap is synchronized by
            # SDL; the cap also provides safe pacing if a driver ignores it.
            clock.tick(self._refresh_rate)
        self._remove_live_resize_watch()
        self._window.destroy()
        pygame.display.quit()

    # -- cross-thread helpers -------------------------------------------
    def call(self, fn, *args):
        """Run a user callable off the UI thread (sync: thread, async: loop)."""
        if inspect.iscoroutinefunction(fn):
            asyncio.run_coroutine_threadsafe(fn(*args), self._loop)
        else:
            # ponytail: one thread per handler, sequential dispatch if races show up
            threading.Thread(target=_swallow, args=(fn, *args), daemon=True).start()

    def mark_dirty(self):
        self._dirty.set()

    def post(self, fn):
        """Run a callable on the UI thread (required for SDL display calls)."""
        self._ui_q.put(fn)

    def _apply_default_window_icon(self):
        return _set_windows_default_icon(self._window.handle)

    def _resize_frame(self, width: int, height: int, *, present: bool,
                      dispatch: bool = False):
        """Apply a client-area resize, optionally drawing immediately.

        ``present=True`` is used by the SDL event watch while Win32 owns the
        modal move/size loop and Saturn's normal event loop cannot advance.
        """
        width, height = max(1, int(width)), max(1, int(height))
        self._size[:] = [width, height]
        self._outer_size[0] = width + self._frame_size[0]
        self._outer_size[1] = height + self._frame_size[1]
        if self.renderer is not None:
            self.renderer.on_resize(width, height)
        size = (width, height)
        if (dispatch and self.page is not None
                and size != self._last_resize_dispatched_size):
            self._last_resize_dispatched_size = size
            self.page._dispatch(self.page.on_resize)
        if present and self.page is not None and self.renderer is not None:
            self.page.draw()
            self.renderer.flip()
            self._dirty.clear()
        else:
            self._dirty.set()

    def _install_live_resize_watch(self):
        """Redraw inside SDL's Win32 modal resize loop.

        pygame does not expose SDL_AddEventWatch, so bind the SDL2 bundled
        beside pygame. SDL invokes this callback on the window/UI thread;
        that preserves the renderer's strict thread-affinity requirement.
        """
        if sys.platform != "win32":
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
                _fields_ = [("type", ctypes.c_uint32),
                            ("window", SDLWindowEvent),
                            ("padding", ctypes.c_uint8 * 56)]

            callback_type = ctypes.CFUNCTYPE(
                ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(SDLEvent))
            window_id = self._window.id

            @callback_type
            def watch(_userdata, event_ptr):
                event = event_ptr.contents
                # SDL2: WINDOWEVENT=0x200; RESIZED=5; SIZE_CHANGED=6.
                if (event.type == 0x200 and event.window.window_id == window_id
                        and event.window.event in (5, 6)):
                    # RESIZED and SIZE_CHANGED can arrive back-to-back for the
                    # same dimensions. Avoid presenting an identical frame.
                    size = (event.window.data1, event.window.data2)
                    now = time.perf_counter()
                    if size != tuple(self._size) or now - self._last_live_resize_frame > 0.1:
                        self._last_live_resize_frame = now
                        try:
                            self._resize_frame(*size, present=True, dispatch=True)
                        except Exception:
                            # ctypes callbacks must never leak exceptions into SDL.
                            import traceback
                            traceback.print_exc()
                return 1

            dll.SDL_AddEventWatch.argtypes = [callback_type, ctypes.c_void_p]
            dll.SDL_AddEventWatch.restype = None
            dll.SDL_DelEventWatch.argtypes = [callback_type, ctypes.c_void_p]
            dll.SDL_DelEventWatch.restype = None
            dll.SDL_AddEventWatch(watch, None)
            self._live_resize_dll = dll
            self._live_resize_callback = watch
        except (AttributeError, OSError):
            self._live_resize_dll = None
            self._live_resize_callback = None

    def _remove_live_resize_watch(self):
        if self._live_resize_dll is not None and self._live_resize_callback is not None:
            self._live_resize_dll.SDL_DelEventWatch(self._live_resize_callback, None)
        self._live_resize_callback = None
        self._live_resize_dll = None

    def screenshot(self, path: str | None = None):
        """Grab the current frame from any thread; returns a pygame Surface
        (RGBA, window size) and optionally saves it to `path` as PNG."""
        done = threading.Event()
        box: list = []

        def _grab():
            try:
                if self.page is not None:
                    self.page.draw()  # GL: re-draw so the back buffer is current
                box.append(self.renderer.screenshot())
            except Exception as e:  # surface the error on the caller thread
                box.append(e)
            finally:
                done.set()

        self.post(_grab)
        if not done.wait(2.0):
            raise TimeoutError("screenshot: UI thread did not respond")
        result = box[0]
        if isinstance(result, Exception):
            raise result
        if path:
            pygame.image.save(result, path)
        return result

    @property
    def size(self):
        return tuple(self._size)

    @property
    def outer_size(self):
        return tuple(self._outer_size)

    @property
    def refresh_rate(self):
        return self._refresh_rate

    def client_size_for_outer(self, width, height):
        return (max(1, int(width) - self._frame_size[0]),
                max(1, int(height) - self._frame_size[1]))

    def _measure_frame_size(self):
        """Return native non-client (border + title bar) width/height.

        Win32 reports the real metrics for the current DPI/theme, avoiding
        hard-coded 16x39 assumptions. Other platforms retain SDL semantics.
        """
        if sys.platform != "win32":
            return (0, 0)
        try:
            import ctypes
            from ctypes import wintypes

            hwnd = self._window.handle
            outer = wintypes.RECT()
            client = wintypes.RECT()
            user32 = ctypes.windll.user32
            if not user32.GetWindowRect(hwnd, ctypes.byref(outer)):
                return (0, 0)
            if not user32.GetClientRect(hwnd, ctypes.byref(client)):
                return (0, 0)
            return ((outer.right - outer.left) - (client.right - client.left),
                    (outer.bottom - outer.top) - (client.bottom - client.top))
        except (KeyError, OSError):
            return (0, 0)


def _swallow(fn, *args):
    try:
        fn(*args)
    except Exception:
        import traceback
        traceback.print_exc()


def run(main, *, backend: Render | None = None, width: int = 800,
        height: int = 600, title: str = "saturn", **_flet_ignored):
    """Open a window, run `main(page)` and block until the window closes.

    Extra flet-style run kwargs (view, assets_dir, host, port, ...) are
    accepted and ignored so flet programs port with a one-line change.
    Returns the App handle (after the window closes).
    """
    if backend is Render.VULKAN:
        raise NotImplementedError("Render.VULKAN is a placeholder; use SOFTWARE or OPENGL")
    if backend is None:  # test hook: pick renderer from the environment
        backend = Render(os.environ.get("SATURN_BACKEND", "software").lower())
    app = App(main, backend, width, height, title)
    app.start()
    app.run_until_closed()
    return app
