"""Window, event loop and threading model.

Thread rules:
- The thread that calls run() owns the window: it pumps SDL events, re-layouts
  and redraws when dirty, with optional display refresh pacing.
- main(page) and every event handler run off the UI thread (sync -> a bounded
  worker pool, async -> the app's asyncio loop), so blocking handlers do not
  stop window event processing. Complete related control mutations before
  calling update(); it reconciles ownership and requests layout/redrawing.
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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pygame

from .renderer import create_renderer
from .renderer.base import Renderer as _RendererBase
from .window import WindowEventType


class Renderer(enum.Enum):
    """Rendering backend."""
    SOFTWARE = "software"

    OPENGL = "opengl"

    VULKAN = "vulkan"


Render = Renderer

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


def _system_pixel_ratio() -> float:
    """Return the primary Windows display density in logical-pixel units."""
    if sys.platform != "win32":
        return 1.0
    try:
        dpi = int(ctypes.windll.user32.GetDpiForSystem())
        return max(1.0, dpi / 96.0) if dpi > 0 else 1.0
    except (AttributeError, OSError, TypeError, ValueError):
        return 1.0


def _window_pixel_ratio(hwnd: int) -> float:
    """Return the live per-monitor density for a native window."""
    if sys.platform != "win32" or not hwnd:
        return 1.0
    try:
        dpi = int(ctypes.windll.user32.GetDpiForWindow(hwnd))
        return max(1.0, dpi / 96.0) if dpi > 0 else 1.0
    except (AttributeError, OSError, TypeError, ValueError):
        return _system_pixel_ratio()


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


class App:
    def __init__(self, main, backend: Renderer, title: str = "saturn", *, gpu=None, _parent_app=None):
        from .renderer.gpu import validate_gpu
        self._gpu = validate_gpu(gpu)
        if backend is Renderer.SOFTWARE and self._gpu is not None:
            raise ValueError('The software renderer does not support GPU selection')
        self._parent_app = _parent_app
        self._root = _parent_app._root if _parent_app else self
        self._children = []
        self._window = None
        self._disposed = False
        self._running = False
        if _parent_app:
            self._router = self._root._router
        else:
            from .routing import RouteState
            self._router = RouteState()
        self._active_theme = None
        self._main = main
        self._backend = backend
        self._renderer_failure = None
        # Window.width/height describe the native outer window. Page
        # width/height describe the drawable client area. SDL's Window.size
        # is client-only, so keep the two coordinate spaces separate.
        self._outer_size = [800, 600]
        self._size = list(self._outer_size)
        self._frame_size = (0, 0)
        self._title = title
        self._dirty = threading.Event()
        self._closed = threading.Event()
        self._mod_watch_stop = threading.Event()
        self._ui_q: queue.SimpleQueue = queue.SimpleQueue()
        # background loop for async handlers / main coroutines
        if _parent_app:
            self._loop = self._root._loop
            self._executor = self._root._executor
        else:
            self._loop = asyncio.new_event_loop()
            self._executor = ThreadPoolExecutor(thread_name_prefix="saturn-handler")
            threading.Thread(target=self._loop.run_forever, daemon=True,
                             name="saturn-async").start()
        self.renderer: _RendererBase | None = None
        self._anti_aliasing = _parent_app._anti_aliasing if _parent_app else True
        self._vsync = _parent_app._vsync if _parent_app else True
        self._renderer_configuration_pending = False
        self._renderer_options_lock = threading.Lock()
        self._font_event_lock = asyncio.Lock()
        self.page = None  # set in start()
        self._live_resize_dll = None
        self._live_resize_callback = None
        self._last_live_resize_frame = 0.0
        self._last_resize_dispatched_size = None
        self._refresh_rate = 60
        self._window_icon = None
        self._pixel_ratio = 1.0
        self._show_on_first_frame = _parent_app is None
        self._last_brightness_check = 0.0

    # -- lifecycle ------------------------------------------------------
    def start(self):
        self._ui_thread = threading.get_ident()
        # SDL2 suppresses native IME UI by default. Enable the operating
        # system candidate list before initializing the video subsystem.
        os.environ.setdefault("SDL_IME_SHOW_UI", "1")
        # SDL must opt into Per-Monitor V2 before video initialization. This
        # disables Windows' blurry bitmap scaling when a window moves between
        # displays with different densities.
        os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
        if self._parent_app is None:
            pygame.init()
        # pygame disables key repeat by default. SDL owns the held-key timer
        # and stops it on key release; text entry still uses TEXTINPUT events.
        pygame.key.set_repeat(400, 35)
        try:
            self._create_window_renderer()
        except Exception as error:
            if self._backend is Renderer.SOFTWARE:
                raise
            self._renderer_failure = dict(backend=self._backend.value,
                                          gpu=self._gpu, error=str(error))
            print("Saturn can't use your current GPU, fallback to software renderer.")
            print(f"  reason: {error}")
            position = self._window.position if self._window is not None else None
            if self.renderer is not None:
                try:
                    self.renderer.close()
                except Exception as cleanup_error:
                    self._renderer_failure['error'] += f"; cleanup failed: {cleanup_error}"
                self.renderer = None
            if self._window is not None:
                self._window.destroy()
                self._window = None
            self._backend, self._gpu = Renderer.SOFTWARE, None
            self._create_window_renderer()
            if position is not None:
                self._window.position = position
        from .page import Page  # deferred: page imports app bits
        if self.page is None:
            self.page = Page(self)
        from . import text as _text
        _text._font_event_apps.add(self._root)
        if self._parent_app is None:
            from . import _modwatch
            _modwatch.start(self.page, self._mod_watch_stop)
        autoclose = os.environ.get("SATURN_AUTOCLOSE")  # test hook
        if autoclose and self._parent_app is None:
            threading.Timer(float(autoclose), self.close).start()
        shot = os.environ.get("SATURN_SHOT")  # test hook: save a frame
        if shot and self._parent_app is None:
            threading.Timer(2.0, lambda: _swallow(self.screenshot, shot)).start()
        threading.Thread(target=self.call, args=(self._invoke_main, self.page),
                         daemon=True, name="saturn-main").start()
        self._dirty.set()
        if self._root._running:
            self._install_live_resize_watch()

    def _create_window_renderer(self):
        if self._backend is Renderer.OPENGL:
            pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
        self._pixel_ratio = _system_pixel_ratio()
        self._window = pygame.Window(
            title=self._title, size=self.physical_size_for_logical(*self._outer_size),
            resizable=True, opengl=self._backend is Renderer.OPENGL,
            vulkan=self._backend is Renderer.VULKAN, allow_high_dpi=True,
            hidden=False)
        self._pixel_ratio = _window_pixel_ratio(self._window.handle)
        self._refresh_rate = _system_refresh_rate()
        self._apply_default_window_icon()
        self._frame_size = self._measure_frame_size()
        client = self.client_size_for_outer(*self._outer_size)
        pixel_client = self.physical_size_for_logical(*client)
        if tuple(self._window.size) != pixel_client:
            self._window.size = pixel_client
        self._size[:] = client
        self.renderer = create_renderer(
            self._backend, self._window, logical_size=client,
            pixel_ratio=self._pixel_ratio, anti_aliasing=self._anti_aliasing,
            vsync=self._vsync, gpu=self._gpu)
        self.renderer.on_resize(*client, pixel_size=pixel_client,
                                pixel_ratio=self._pixel_ratio)

    def _notify_render_ready(self):
        from .event import RenderFailedEvent, RenderReadyEvent
        page = self.page
        events = []
        if self._renderer_failure is not None:
            events.append((page.on_render_failed, RenderFailedEvent(
                "render_failed", page, **self._renderer_failure)))
        events.append((page.on_render_ready, RenderReadyEvent(
            "render_ready", page, backend=self.renderer.name,
            gpu_name=self.renderer.gpu_name, gpu_index=self.renderer.gpu_index,
            fallback=self._renderer_failure is not None)))
        self.call(self._dispatch_ordered_events, events)

    async def _dispatch_ordered_events(self, events):
        from .event import _invoke, normalize_handlers
        for handlers, event in events:
            for handler in normalize_handlers(handlers):
                if self._closed.is_set() or event.page._app._closed.is_set():
                    return
                try:
                    result = await asyncio.get_running_loop().run_in_executor(
                        self._executor, _invoke, handler, event)
                    if inspect.isawaitable(result):
                        await result
                except Exception:
                    import traceback
                    traceback.print_exc()

    def _notify_font_optimize(self, **payload):
        from .event import FontOptimizeEvent
        events = []
        for app in tuple(self._apps()):
            if app._closed.is_set() or app.page is None:
                continue
            if payload['status'] != 'started':
                app.page._font_ready()
            events.append((app.page.on_font_optimize,
                           FontOptimizeEvent("font_optimize", app.page, **payload)))
        async def notify():
            async with self._font_event_lock:
                await self._dispatch_ordered_events(events)
        self.call(notify)

    def _invoke_main(self, page):
        result = self._main(page)
        def placed():
            if hasattr(page, "_sync_attachment") and not self._closed.is_set():
                self.post(lambda: page._sync_attachment(force=True))
            if not self._closed.is_set():
                self._notify_render_ready()
            # Safety for mains that draw nothing: never keep the window hidden.
            def show_pending():
                if getattr(self, "_show_on_first_frame", False):
                    self._show_on_first_frame = False
                    if page.window._values.get("visible", True):
                        self._window.show()
                        page.window._emit(WindowEventType.SHOW)
            self.post(show_pending)
        if inspect.isawaitable(result):
            async def finish():
                try:
                    return await result
                finally:
                    placed()
            return finish()
        placed()
        return result

    def close(self):
        self._closed.set()
        for child in tuple(self._children):
            child.close()

    def _apps(self):
        yield self
        for child in tuple(self._children):
            yield from child._apps()

    def _mark_all_dirty(self):
        for app in self._apps():
            app.mark_dirty()

    def _activate(self):
        if self.renderer is not None:
            self.renderer.activate()
        # Colors and font defaults are currently shared by the widget library.
        # Restore the owning Page's settings before each window is rendered.
        if self.page is not None and self.page._theme_key is not None:
            from . import colors, text
            text.register_fonts(self.page._fonts, on_ready=self._root._mark_all_dirty)
            key = self.page._theme_key
            if self._root._active_theme != key:
                # Use page's theme manager instead of global state
                self.page._theme_manager.to_legacy_globals()
                colors.apply_seed(key[2], expressive=key[3])
                text.set_default_family(key[1])
                self._root._active_theme = key

    def _drain_commands(self):
        if self._window is None or self._closed.is_set():
            return
        self._activate()
        while True:
            try:
                command = self._ui_q.get_nowait()
            except queue.Empty:
                break
            command()
            self._activate()

    def _handle_event(self, e):
        self._activate()
        if e.type == pygame.WINDOWCLOSE:
            self.page.window._request_close()
        elif e.type == pygame.WINDOWRESIZED:
            self._resize_frame(e.x, e.y, present=False, dispatch=True)
        elif e.type == pygame.WINDOWDISPLAYCHANGED:
            self._refresh_pixel_ratio()
            self._resize_frame(*self._window.size, present=False, dispatch=True)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.page.pointer_down(*self.logical_point(*e.pos))
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.page.pointer_up(*self.logical_point(*e.pos))
        elif e.type == pygame.MOUSEMOTION:
            self.page.pointer_move(*self.logical_point(*e.pos))
        else:
            self.page.handle_event(e)
        self.page.window._handle_event(e)

    def _pump_once(self):
        for app in tuple(self._apps()):
            app._drain_commands()
        apps = {app._window.id: app for app in self._apps()
                if app._window is not None and not app._closed.is_set()}
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.page.window._request_close()
                continue
            window = getattr(event, "window", None)
            window_id = getattr(window, "id", window)
            target = apps.get(window_id)
            if target is None and window is None:
                target = next((app for app in apps.values() if app._window.focused), self)
            if target is None or target._closed.is_set():
                continue
            if any(getattr(child.page, "modal", False) and not child._closed.is_set()
                   for child in target._children) and event.type in (
                    pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION,
                    pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT, pygame.TEXTEDITING,
                    pygame.MOUSEWHEEL):
                continue
            target._handle_event(event)
        now = time.perf_counter()
        for app in tuple(self._apps()):
            if app._closed.is_set() or app._window is None or app.renderer is None:
                continue
            app._activate()
            if hasattr(app.page, "_sync_attachment"):
                app.page._sync_attachment()
            if now - app._last_brightness_check >= 1.0:
                app._last_brightness_check = now
                app.page._refresh_platform_brightness()
            if not app.page.window._values.get("visible", True):
                # Explicitly hidden windows keep their tree but consume no
                # animation frames. Showing them requests a fresh frame.
                app._dirty.clear()
                continue
            if app._dirty.is_set():
                app._dirty.clear()
                app.page.draw()
                app.renderer.flip()
                if getattr(app, "_show_on_first_frame", False):
                    app._show_on_first_frame = False
                    if app.page.window._values.get("visible", True):
                        app._window.show()
                        app.page.window._emit(WindowEventType.SHOW)
        for app in reversed(tuple(self._apps())):
            if app._closed.is_set() and app is not self:
                app._dispose()

    def _dispose(self):
        if self._disposed:
            return
        for child in tuple(self._children):
            child.close()
            child._dispose()
        self._remove_live_resize_watch()
        self._activate()
        if self.page is not None:
            self.page._cancel_input()
            self.page.window._dispose()
            self._router.unregister(self.page)
        if self.renderer is not None:
            self.renderer.close()
        if self._window is not None:
            self._window.destroy()
            self._window = None
        self._disposed = True
        parent = self._parent_app
        if parent is not None:
            if self in parent._children:
                parent._children.remove(self)
            if (sys.platform == "win32" and parent._window is not None
                    and getattr(self.page, "modal", False)
                    and not any(getattr(c.page, "modal", False) and not c._closed.is_set()
                                for c in parent._children)):
                ctypes.windll.user32.EnableWindow(ctypes.c_void_p(parent._window.handle), True)
            if not parent._closed.is_set():
                parent._activate()

    def run_until_closed(self):
        # Bind the SDL watcher to the actual event-loop lifetime. Some unit
        # tests use start() only and create several displays in one process;
        # leaving a watcher attached across those displays is unsafe.
        self._install_live_resize_watch()
        self._running = True
        clock = pygame.time.Clock()
        while not self._closed.is_set():
            self._pump_once()
            if self._vsync:
                clock.tick(self._refresh_rate)
            elif not self._dirty.is_set():
                # Poll input while idle without spinning a CPU core. Active
                # animations remain uncapped when synchronization is off.
                self._dirty.wait(0.004)
        self._running = False
        if self._root is self:
            self._mod_watch_stop.set()
        self._dispose()
        pygame.display.quit()
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._loop.call_soon_threadsafe(self._loop.stop)

    # -- cross-thread helpers -------------------------------------------
    def configure_renderer(self, *, anti_aliasing=None, vsync=None):
        """Coalesce rendering option changes before the next UI frame."""
        with self._renderer_options_lock:
            changed = False
            if anti_aliasing is not None and anti_aliasing != self._anti_aliasing:
                self._anti_aliasing = anti_aliasing
                changed = True
            if vsync is not None and vsync != self._vsync:
                self._vsync = vsync
                changed = True
            if not changed or self._renderer_configuration_pending:
                return
            self._renderer_configuration_pending = True

        def apply():
            with self._renderer_options_lock:
                options = (self._anti_aliasing, self._vsync)
                self._renderer_configuration_pending = False
            if self.renderer is not None:
                self.renderer.configure(anti_aliasing=options[0], vsync=options[1])
            if self.page is not None:
                self.page._layout_dirty = True
            self.mark_dirty()

        self.post(apply)
        self.mark_dirty()

    def call(self, fn, *args, **kwargs):
        """Run a callable off the UI thread and await returned awaitables."""
        if inspect.iscoroutinefunction(fn):
            future = asyncio.run_coroutine_threadsafe(fn(*args, **kwargs), self._loop)
            future.add_done_callback(_report_async_error)
            return future
        else:
            def invoke():
                result = fn(*args, **kwargs)
                if inspect.isawaitable(result):
                    async def await_result():
                        return await result
                    future = asyncio.run_coroutine_threadsafe(await_result(), self._loop)
                    future.add_done_callback(_report_async_error)
                    return future
                return result
            return self._executor.submit(_swallow, invoke)

    def mark_dirty(self):
        self._dirty.set()

    def post(self, fn):
        """Run a callable on the UI thread (required for SDL display calls)."""
        self._ui_q.put(fn)

    def set_text_input_rect(self, rect: pygame.Rect):
        """Position SDL text input using a caret-relative exclusion area."""
        ratio = self._pixel_ratio
        pygame.key.set_text_input_rect(pygame.Rect(
            round(rect.x * ratio), round(rect.y * ratio),
            max(1, round(rect.width * ratio)),
            max(1, round(rect.height * ratio)),
        ))

    def _apply_default_window_icon(self):
        return _set_windows_default_icon(self._window.handle)

    def _resize_frame(self, width: int, height: int, *, present: bool,
                      dispatch: bool = False):
        """Apply a client-area resize, optionally drawing immediately.

        ``present=True`` is used by the SDL event watch while Win32 owns the
        modal move/size loop and Saturn's normal event loop cannot advance.
        """
        self._activate()
        pixel_width = max(1, int(width))
        pixel_height = max(1, int(height))
        self._refresh_pixel_ratio()
        width = max(1, round(pixel_width / self._pixel_ratio))
        height = max(1, round(pixel_height / self._pixel_ratio))
        rects = self._window_rects()
        if rects is not None:
            # One consistent snapshot: the tracked frame, client and outer
            # sizes all come from the same instant. A cached frame here can
            # be stale (a style change re-splits client/outer without an SDL
            # resize) and would inflate the tracked sizes every event.
            outer, client = rects
            ratio = self._pixel_ratio or 1.0
            client_w = client.right - client.left
            client_h = client.bottom - client.top
            if client_w > 0 and client_h > 0:  # minimized windows report none
                width = max(1, round(client_w / ratio))
                height = max(1, round(client_h / ratio))
                self._frame_size = (
                    round(((outer.right - outer.left) - client_w) / ratio),
                    round(((outer.bottom - outer.top) - client_h) / ratio))
                self._outer_size[0] = max(1, round((outer.right - outer.left) / ratio))
                self._outer_size[1] = max(1, round((outer.bottom - outer.top) / ratio))
        self._size[:] = [width, height]
        if self.renderer is not None:
            self.renderer.on_resize(
                width, height, pixel_size=(pixel_width, pixel_height),
                pixel_ratio=self._pixel_ratio)
        size = (width, height)
        if (dispatch and self.page is not None
                and size != self._last_resize_dispatched_size):
            self._last_resize_dispatched_size = size
            self.page._notify_resize()
            self.page.window._emit(WindowEventType.RESIZED)
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
                if threading.get_ident() != self._ui_thread or self._closed.is_set():
                    return 1
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
        if self._closed.is_set():
            raise RuntimeError("Cannot capture a closed window")
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

    @property
    def pixel_ratio(self):
        return self._pixel_ratio

    def physical_size_for_logical(self, width, height):
        ratio = self._pixel_ratio
        return (max(1, round(float(width) * ratio)),
                max(1, round(float(height) * ratio)))

    def logical_point(self, x, y):
        ratio = self._pixel_ratio
        return (float(x) / ratio, float(y) / ratio)

    def _refresh_pixel_ratio(self):
        if self._window is None:
            return False
        ratio = _window_pixel_ratio(self._window.handle)
        if abs(ratio - self._pixel_ratio) < 0.001:
            return False
        self._pixel_ratio = ratio
        self._frame_size = self._measure_frame_size()
        if self.page is not None:
            self.page.window._apply_limits()
        return True

    def client_size_for_outer(self, width, height):
        return (max(1, int(width) - self._frame_size[0]),
                max(1, int(height) - self._frame_size[1]))

    def _measure_frame_size(self):
        """Return native non-client (border + title bar) width/height.

        Win32 reports the real metrics for the current DPI/theme, avoiding
        hard-coded 16x39 assumptions. Other platforms retain SDL semantics.
        """
        rects = self._window_rects()
        if rects is None:
            return (0, 0)
        outer, client = rects
        frame_w = ((outer.right - outer.left)
                   - (client.right - client.left))
        frame_h = ((outer.bottom - outer.top)
                   - (client.bottom - client.top))
        return (round(frame_w / self._pixel_ratio),
                round(frame_h / self._pixel_ratio))

    def _actual_outer_size(self):
        """The window's real outer size in logical pixels.

        Style changes (hiding the title bar) alter the client/outer split
        without an SDL resize, leaving the tracked `_outer_size` stale.
        """
        rects = self._window_rects()
        if rects is None:
            return tuple(self._outer_size)
        outer, _ = rects
        ratio = self._pixel_ratio or 1.0
        return (max(1, round((outer.right - outer.left) / ratio)),
                max(1, round((outer.bottom - outer.top) / ratio)))

    def _window_rects(self):
        """Outer and client rects in physical pixels, or None off-Windows."""
        if sys.platform != "win32" or self._window is None:
            return None
        try:
            import ctypes
            from ctypes import wintypes

            hwnd = self._window.handle
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
        except (KeyError, OSError):
            return None


def _swallow(fn, *args):
    try:
        return fn(*args)
    except Exception:
        import traceback
        traceback.print_exc()


def _report_async_error(future):
    if future.cancelled():
        return
    try:
        future.result()
    except Exception:
        import traceback
        traceback.print_exc()


def run(main, *, backend: Renderer | None = None, title: str = "saturn", gpu: str | int | None = None):
    """Open a window, run `main(page)` and block until the window closes.

    Set window dimensions through `page.window.width` and
    `page.window.height` in the entry point. Only the listed desktop
    startup options are supported; unknown keyword arguments raise TypeError.
    Returns the App handle (after the window closes).
    The active backend name is available as `page.renderer.name` in main.
    Pass gpu as an exact/unique GPU name or index; None keeps default selection.
    """
    if backend is None:  # explicit selection and test hook via environment
        backend = Renderer(os.environ.get("SATURN_BACKEND", "opengl").lower())

    app = App(main, backend, title=title, gpu=gpu)
    try:
        app.start()
    except Exception:
        app.close()
        app.run_until_closed()
        raise
    app.run_until_closed()
    return app


def run_thread(main, *, backend: Renderer | None = None, title: str = "saturn",
               gpu: str | int | None = None):
    """Like `run`, but the window runs on a daemon thread and this returns
    the App handle immediately. Window creation and the event loop share
    that thread (SDL affinity); UI mutations from the caller's thread must
    go through `page.run_task` / `page._app.post`. The app dies with the
    process (daemon thread)."""
    if backend is None:
        backend = Renderer(os.environ.get("SATURN_BACKEND", "opengl").lower())

    app = App(main, backend, title=title, gpu=gpu)

    def serve():
        try:
            app.start()
        except Exception:
            import traceback
            traceback.print_exc()
            app.close()
            app.run_until_closed()
            return
        app.run_until_closed()

    threading.Thread(target=serve, daemon=True, name="saturn-window").start()
    return app
