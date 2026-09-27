"""Logical Page ownership and per-view execution context, without SDL windows."""
import asyncio
import inspect
import threading
from concurrent.futures import Future
from dataclasses import dataclass, field
from types import SimpleNamespace
from uuid import uuid4

from ..event import _invoke, normalize_handlers
from ..page import Page
from ..types import ThemeMode
from .context import NativeWindowUnavailable, current_session, current_view
from .events import WebEvents


async def invoke(fn, *args):
    if inspect.iscoroutinefunction(fn):
        return await fn(*args)
    result = await asyncio.to_thread(fn, *args)
    return await result if inspect.isawaitable(result) else result


@dataclass
class View:
    request: object
    width: int = 1024
    height: int = 768
    density: float = 1
    client_id: str = field(default_factory=lambda: str(uuid4()))
    session: object = None
    outbox: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=16))
    scene: dict = field(default_factory=dict)
    revision: int = 0
    scene_revision: int = 0
    scroll: dict = field(default_factory=dict)
    input_versions: dict = field(default_factory=dict)
    seen_events: dict = field(default_factory=dict)
    token: str = ""
    needs_snapshot: bool = True


class WebSettings:
    def __init__(self, owner, handle=None):
        self.owner, self.handle = owner, handle
        self._events = WebEvents(self) if handle is None else None

    @property
    def _session(self):
        return self.owner._target._app.session if self.handle else self.owner._app.session

    @property
    def session(self):
        return self._session.id

    @session.setter
    def session(self, identifier):
        if self.handle is None:
            raise RuntimeError("Select page.web.session inside main before adding controls")
        old = self._session
        if identifier == old.id:
            return
        if old.locked or old.ready.done():
            raise RuntimeError("Session membership is fixed after initialization")
        target = old.runtime.select(identifier, self.handle.view, replace=old)
        self.owner._target = target.page
        self.handle.view.session = target
        current_session.set(target)
        old.runtime.discard_empty(old)

    @property
    def is_new_session(self):
        view = current_view.get()
        return bool(view and self._session.owner == view.client_id and not self._session.ready.done())

    @property
    def client_id(self):
        view = current_view.get()
        return view.client_id if view else None

    @property
    def query(self):
        view = current_view.get()
        return dict(view.request.query_params) if view else {}

    @property
    def connection_count(self):
        return len(self._session.views)

    @property
    def events(self):
        return self._session.page._web._events

    @property
    def on_connect(self):
        return self._session.on_connect

    @on_connect.setter
    def on_connect(self, value):
        normalize_handlers(value)
        self._session.on_connect = value

    @property
    def on_disconnect(self):
        return self._session.on_disconnect

    @on_disconnect.setter
    def on_disconnect(self, value):
        normalize_handlers(value)
        self._session.on_disconnect = value


class PageHandle(Page):
    """Entry-point Page facade; binding changes before initialization only."""
    def __init__(self, session, view):
        object.__setattr__(self, "_target", session.page)
        object.__setattr__(self, "view", view)
        object.__setattr__(self, "_settings", WebSettings(self, self))

    def __getattribute__(self, name):
        if name in ("_target", "view", "_settings", "__dict__", "__class__"):
            return object.__getattribute__(self, name)
        if name == "web":
            return object.__getattribute__(self, "_settings")
        return getattr(object.__getattribute__(self, "_target"), name)

    def __setattr__(self, name, value):
        if name == "_target":
            object.__setattr__(self, name, value)
        else:
            setattr(self._target, name, value)


class SessionApp:
    def __init__(self, session):
        self.session = session
        self._root = self
        self._active_theme = None
        self._closed = threading.Event()
        self.renderer = SimpleNamespace(name="canvas", scale=1, gpu_name=None, gpu_index=None, gpus=())
        self._anti_aliasing, self._vsync = True, True

    @property
    def pixel_ratio(self):
        view = current_view.get()
        return view.density if view else 1

    def mark_dirty(self):
        if self.session.closed or not hasattr(self.session, 'page'):
            return
        self.session.locked = True
        self.session.runtime.schedule(self.session.dirty)

    def call(self, fn, *args):
        view = current_view.get()
        self.session.runtime.schedule(lambda: self.session.enqueue([lambda: fn(*args)], None, view))

    def post(self, fn):
        if hasattr(self.session, 'page'):
            self.call(fn)

    def configure_renderer(self, **options):
        raise NotImplementedError("Browser rendering options are managed by the browser")


class WebPage(Page):
    _native_window = False

    def __init__(self, session):
        super().__init__(SessionApp(session))
        self.window = NativeWindowUnavailable()
        self._web = WebSettings(self)
        self._title = "Saturn Web"
        self._platform_brightness = "light"

    @property
    def web(self):
        return self._web

    @property
    def width(self):
        view = current_view.get()
        return view.width if view else 1024

    @property
    def height(self):
        view = current_view.get()
        return view.height if view else 768

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = str(value)
        self._app.mark_dirty()

    def _apply_theme(self):
        dark = self._theme_mode is ThemeMode.DARK
        effective = self._dark_theme if dark and self._dark_theme else self._theme
        self._theme_key = (dark, getattr(effective, "font_family", None),
                          getattr(effective, "color_scheme_seed", None),
                          getattr(effective, "expressive", False))

    def _sync_native_title_bar(self):
        pass

    def _sync_fonts(self):
        from pathlib import Path
        for source in self._fonts.values():
            if str(source).startswith(("http://", "https://")):
                raise NotImplementedError("Web font aliases currently require local files")
            if not Path(source).is_file() and not (Path("assets")/source).is_file():
                raise FileNotFoundError(source)

    def update(self):
        if not hasattr(self, "_attached_roots"):
            return
        self._apply_theme()
        self._sync_fonts()
        self._reconcile_roots()
        if self.services:
            raise NotImplementedError("Desktop services are not supported by the Web runtime")
        self._layout_dirty = True
        self._app.mark_dirty()

    def open_subpage(self, *args, **kwargs):
        raise NotImplementedError("Native Subpages require a desktop runtime")

    def run_task(self, *args, **kwargs):
        raise NotImplementedError("Web background tasks must be owned by the ASGI application's lifespan")

    def go(self, route):
        super().go(route)
        self._app.mark_dirty()

    def focus(self, control):
        view = current_view.get()
        if view is None:
            raise RuntimeError("Web focus requires an originating browser view")
        if control is not None and control.page is not self:
            raise ValueError("Focus target must belong to this Page")
        view.focus_id = self._app.session.control_id(control) if control else None
        self._app.mark_dirty()


class Session:
    def __init__(self, runtime, identifier, owner):
        self.runtime, self.id, self.owner = runtime, identifier, owner
        self.ready = Future()
        self.locked = self.closed = False
        self.views = {}
        self.controls, self.ids = {}, {}
        self.revision = self.sequence = 0
        self.input_revisions, self.input_owners = {}, {}
        self.on_connect = self.on_disconnect = None
        self.queue = asyncio.Queue(maxsize=runtime.max_pending_events)
        self.lock = asyncio.Lock()
        self.worker = self.flush = self.expiry = None
        self.page = WebPage(self)

    def control_id(self, control):
        if control not in self.ids:
            identifier = str(uuid4())
            self.ids[control] = identifier
        identifier = self.ids[control]
        self.controls[identifier] = control
        return identifier

    def start(self):
        if self.worker is None:
            self.worker = asyncio.create_task(self.consume())

    def enqueue(self, callbacks, event, view=None, done=None):
        if self.closed:
            if done is not None and not done.done():
                done.set_exception(RuntimeError("Session closed"))
            return
        try:
            self.queue.put_nowait((callbacks, event, view, done))
        except asyncio.QueueFull:
            if done is not None:
                done.set_exception(RuntimeError("Session event queue is full"))
            else:
                self.runtime.report("Session event queue is full", view)
        self.start()

    async def consume(self):
        try:
            await asyncio.wrap_future(self.ready)
            while True:
                callbacks, event, view, done = await self.queue.get()
                async with self.lock:
                    origin = current_view.set(view)
                    token = current_session.set(self)
                    try:
                        for callback in callbacks:
                            try:
                                await invoke(_invoke, callback, event)
                            except Exception as error:
                                if done is not None and not done.done():
                                    done.set_exception(error)
                                else:
                                    self.runtime.report(str(error), view)
                        if done is not None and not done.done():
                            done.set_result(None)
                    finally:
                        current_view.reset(origin)
                        current_session.reset(token)
                        self.queue.task_done()
        except asyncio.CancelledError:
            pass

    def dirty(self):
        if not self.closed and (self.flush is None or self.flush.done()):
            self.flush = asyncio.create_task(self.publish())

    async def publish(self):
        from .scene import build_scene, scene_patch
        await asyncio.wrap_future(self.ready)
        await asyncio.sleep(0)
        async with self.lock:
            if self.closed:
                return
            self.revision += 1
            for view in list(self.views.values()):
                try:
                    scene = build_scene(self, view)
                    message = scene_patch(view, scene, self)
                    if message:
                        self.runtime.deliver(view, message)
                except Exception as error:
                    self.runtime.report(str(error), view)

    async def dispose(self):
        self.closed = True
        self.page._app._closed.set()
        if self.expiry:
            self.expiry.cancel()
        tasks = [t for t in (self.worker, self.flush) if t and t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if not self.ready.done():
            self.ready.cancel()
        while not self.queue.empty():
            _, _, _, done = self.queue.get_nowait()
            if done and not done.done():
                done.set_exception(RuntimeError("Session closed"))
            self.queue.task_done()
        self.page.web.events.clear()
        self.page.controls.clear()
        self.controls.clear()
        self.ids.clear()
