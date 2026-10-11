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
import enum
import inspect
import os
import queue
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pygame

from .platform import get_platform
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
    """Compatibility wrapper for the active platform adapter."""
    return get_platform().system_pixel_ratio()


def _window_pixel_ratio(hwnd: int) -> float:
    """Compatibility wrapper for the active platform adapter."""
    return get_platform().window_pixel_ratio(hwnd)


def _set_windows_default_icon(hwnd: int) -> bool:
    """Compatibility wrapper for the active platform adapter."""
    return get_platform().set_default_window_icon(hwnd)


class App:
    def __init__(self, main, backend: Renderer, title: str = "saturn", *, gpu=None, _parent_app=None):
        from .renderer.gpu import validate_gpu
        self._gpu = validate_gpu(gpu)
        if backend is Renderer.SOFTWARE and self._gpu is not None:
            raise ValueError('The software renderer does not support GPU selection')
        self._parent_app = _parent_app
        self._root = _parent_app._root if _parent_app else self
        self.platform = _parent_app.platform if _parent_app else get_platform()
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
        self._last_resize_dispatched_size = None
        self._refresh_rate = 60
        self._window_icon = None
        self._pixel_ratio = 1.0
        self._show_on_first_frame = _parent_app is None
        self._last_brightness_check = 0.0

    # -- lifecycle ------------------------------------------------------
    def start(self):
        self._ui_thread = threading.get_ident()
        # Give the active platform a chance to configure SDL before video
        # initialization. The Windows DPI setting lives in its adapter.
        self.platform.prepare_environment()
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
        self._pixel_ratio = self.platform.system_pixel_ratio()
        self._window = pygame.Window(
            title=self._title, size=self.physical_size_for_logical(*self._outer_size),
            resizable=True, opengl=self._backend is Renderer.OPENGL,
            vulkan=self._backend is Renderer.VULKAN, allow_high_dpi=True,
            hidden=False)
        self._pixel_ratio = self.platform.window_pixel_ratio(self._window.handle)
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
                except Exception as e:
                    # Log handler exceptions but don't crash the event loop
                    import traceback
                    print(f"Error in event handler: {e}", file=sys.stderr)
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
            if (parent._window is not None and getattr(self.page, "modal", False)
                    and not any(getattr(c.page, "modal", False) and not c._closed.is_set()
                                for c in parent._children)):
                self.platform.enable_window(parent._window.handle, True)
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

    def mark_dirty(self, *, force: bool = False):
        """Request a frame, respecting the owning Page's auto-update switch.

        ``force=True`` is reserved for explicit Page/API requests.  Internal
        control, animation and input paths use the default so
        ``page.auto_update = False`` can pause them without blocking a manual
        ``page.update()``.
        """
        page = self.page
        if not force and page is not None and not getattr(page, "_auto_update", True):
            return
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
        return self.platform.set_default_window_icon(self._window)

    def _resize_frame(self, width: int, height: int, *, present: bool,
                      dispatch: bool = False):
        """Apply a client-area resize, optionally drawing immediately.

        ``present=True`` is used by a platform event watch while the native
        window system owns a modal move/size loop.
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
        """Install the active platform's live resize hook, if it has one."""
        self.platform.install_live_resize_watch(self)

    def _remove_live_resize_watch(self):
        self.platform.remove_live_resize_watch(self)

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
        ratio = self.platform.window_pixel_ratio(self._window.handle)
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
        """Return native non-client frame width/height when available."""
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
        """Outer and client rects in physical pixels, when the platform has them."""
        return self.platform.window_rects(self._window)


def _swallow(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        # Used for cleanup operations that shouldn't crash the app
        import traceback
        print(f"Cleanup error in {fn.__name__}: {e}", file=sys.stderr)
        traceback.print_exc()


def _report_async_error(future):
    if future.cancelled():
        return
    try:
        future.result()
    except Exception as e:
        # Async task errors should be reported, not silently dropped
        import traceback
        print(f"Async task error: {e}", file=sys.stderr)
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
    except KeyboardInterrupt:
        # User interrupted with Ctrl+C - clean shutdown
        app.close()
        app.run_until_closed()
    except Exception as e:
        # Unexpected errors during startup should be visible
        import traceback
        print(f"Saturn startup error: {e}", file=sys.stderr)
        traceback.print_exc()
        raise
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
        except Exception as e:
            # Daemon thread errors should be logged
            import traceback
            print(f"Saturn thread error: {e}", file=sys.stderr)
            traceback.print_exc()
            app.close()
            app.run_until_closed()
            return
        app.run_until_closed()

    threading.Thread(target=serve, daemon=True, name="saturn-window").start()
    return app
