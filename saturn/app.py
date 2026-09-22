"""Window, event loop and threading model.

Thread rules:
- The thread that calls run() owns the window: it pumps SDL events, re-layouts
  and redraws when dirty, then presents (~60 fps).
- main(page) and every event handler run off the UI thread (sync -> daemon
  thread, async -> the app's asyncio loop), so blocking handlers never freeze
  the window. Control state changes from those threads are only safe between
  update() calls; update() just raises the dirty flag.
"""
from __future__ import annotations

import asyncio
import enum
import inspect
import os
import queue
import threading

import pygame

from .renderer import create_renderer
from .renderer.base import Renderer


class Render(enum.Enum):
    """Rendering backend."""
    SOFTWARE = "software"
    OPENGL = "opengl"
    VULKAN = "vulkan"  # placeholder, see TODO


class App:
    def __init__(self, main, backend: Render, width: int, height: int, title: str):
        self._main = main
        self._backend = backend
        self._size = [int(width), int(height)]
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

    # -- lifecycle ------------------------------------------------------
    def start(self):
        pygame.init()
        if self._backend is Render.OPENGL:
            pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
        flags = pygame.RESIZABLE
        if self._backend is Render.OPENGL:
            flags |= pygame.DOUBLEBUF | pygame.OPENGL
        self._sdl_flags = flags
        pygame.display.set_mode(tuple(self._size), flags)
        pygame.display.set_caption(self._title)
        self._window = pygame.Window.from_display_module()
        self.renderer = create_renderer(self._backend)
        from .page import Page  # deferred: page imports app bits
        self.page = Page(self)
        autoclose = os.environ.get("SATURN_AUTOCLOSE")  # test hook
        if autoclose:
            threading.Timer(float(autoclose), self.close).start()
        threading.Thread(target=self.call, args=(self._main, self.page),
                         daemon=True, name="saturn-main").start()
        self._dirty.set()

    def close(self):
        self._closed.set()

    def run_until_closed(self):
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
                    self._size[0], self._size[1] = e.x, e.y
                    if self.renderer is not None:
                        self.renderer.on_resize(*self._size)
                    self._dirty.set()
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.page.pointer_down(*e.pos)
                elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                    self.page.pointer_up(*e.pos)
                elif e.type == pygame.MOUSEMOTION:
                    self.page.pointer_move(*e.pos)
                elif e.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT,
                                pygame.MOUSEWHEEL):
                    self.page.handle_event(e)
                else:
                    self.page.handle_event(e)
            if self._dirty.is_set():
                self._dirty.clear()
                self.page.draw()
                self.renderer.flip()
            clock.tick(60)
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


def _swallow(fn, *args):
    try:
        fn(*args)
    except Exception:
        import traceback
        traceback.print_exc()


def run(main, *, backend: Render = Render.SOFTWARE, width: int = 800,
        height: int = 600, title: str = "saturn", **_flet_ignored):
    """Open a window, run `main(page)` and block until the window closes.

    Extra flet-style run kwargs (view, assets_dir, host, port, ...) are
    accepted and ignored so flet programs port with a one-line change.
    Returns the App handle (after the window closes).
    """
    if backend is Render.VULKAN:
        raise NotImplementedError("Render.VULKAN is a placeholder; use SOFTWARE or OPENGL")
    app = App(main, backend, width, height, title)
    app.start()
    app.run_until_closed()
    return app
