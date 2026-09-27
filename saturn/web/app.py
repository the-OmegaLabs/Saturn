"""Optional FastAPI host, one-process session registry and browser protocol."""
import asyncio
import contextlib
import inspect
import json
import math
import secrets
import threading
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse

from ..event import normalize_handlers
from .context import current_view, current_session
from .events import WebEvent
from .resources import Resources
from .session import Session, View, PageHandle, invoke


class WebRuntime:
    def __init__(self, main, *, session_ttl=300, authorize=None, max_sessions=1024,
                 max_pending_events=256, max_message_bytes=65536, allowed_origins=None):
        if not callable(main):
            raise TypeError("main must be callable")
        if not math.isfinite(session_ttl) or session_ttl < 0:
            raise ValueError("session_ttl must be finite and nonnegative")
        if any(isinstance(v,bool) or not isinstance(v,int) or v < 1
               for v in (max_sessions,max_pending_events,max_message_bytes)):
            raise ValueError("Web limits must be positive integers")
        if allowed_origins is not None and (isinstance(allowed_origins,str)
                or any(not isinstance(v,str) for v in allowed_origins)):
            raise TypeError("allowed_origins must be a collection of strings")
        self.main, self.session_ttl, self.authorize = main, session_ttl, authorize
        self.max_sessions, self.max_pending_events = max_sessions, max_pending_events
        self.max_message_bytes, self.allowed_origins = max_message_bytes, allowed_origins
        self.sessions, self.tokens = {}, {}
        self.token_expiry = {}
        self.registry_lock = threading.RLock()
        self.resources = Resources()
        self.loop = None
        self.closing = False

    def schedule(self, fn):
        if self.loop is None or self.closing:
            return
        self.loop.call_soon_threadsafe(fn)

    def all_sessions(self):
        with self.registry_lock:
            return list(self.sessions.values())

    def permitted(self, identifier, view):
        if self.authorize is not None:
            result = self.authorize(view.request, identifier)
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise TypeError("authorize must be a synchronous membership check")
            if not result:
                raise PermissionError("Session access denied")

    def select(self, identifier, view, *, check=True, replace=None):
        if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 128:
            raise ValueError("Session ID must be a nonempty string of at most 128 characters")
        if check:
            self.permitted(identifier, view)
        with self.registry_lock:
            session = self.sessions.get(identifier)
            if session is None or session.closed:
                count = len(self.sessions) - int(replace is not None and not replace.locked
                    and self.sessions.get(replace.id) is replace)
                if count >= self.max_sessions:
                    raise RuntimeError("Web session limit reached")
                session = self.sessions[identifier] = Session(self, identifier, view.client_id)
            return session

    def discard_empty(self, session):
        with self.registry_lock:
            if not session.locked and not session.views:
                if self.sessions.get(session.id) is session:
                    del self.sessions[session.id]
                self.schedule(lambda: asyncio.create_task(session.dispose()))

    def deliver(self, view, message):
        # Coalesce unsent frames into a snapshot while preserving input replies.
        pending = []
        while not view.outbox.empty():
            pending.append(view.outbox.get_nowait())
        if message.get('type') in ('patch', 'snapshot'):
            replaced = any(m.get('type') in ('patch', 'snapshot') for m in pending)
            pending = [m for m in pending if m.get('type') not in ('patch', 'snapshot')]
            if replaced:
                message = dict(type='snapshot', scene=view.scene, revision=view.revision,
                               state_revision=view.session.revision, base_revision=0)
        pending.append(message)
        if len(pending) > view.outbox.maxsize:
            pending = [dict(type='error', error='Client is not keeping up; reconnect required', reconnect=True)]
        for item in pending:
            view.outbox.put_nowait(item)

    def report(self, error, view=None):
        if view is not None:
            self.deliver(view, dict(type="error", error=error))
        else:
            import logging
            logging.getLogger('saturn.web').error(error)

    @staticmethod
    def viewport(message, view):
        for field in ('width', 'height'):
            value = message.get(field, getattr(view, field))
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid viewport {field}")
            setattr(view, field, max(16, min(8192, int(value))))
        density = message.get('density', view.density)
        if not isinstance(density, (int, float)) or not math.isfinite(density):
            raise ValueError("Invalid display density")
        view.density = max(1, min(4, density))

    async def connect(self, request, hello):
        if self.closing:
            raise RuntimeError("Web runtime is closed")
        self.loop = asyncio.get_running_loop()
        view = View(request)
        self.viewport(hello, view)
        resumed = self.tokens.get(hello.get('resume'))
        if resumed and not resumed[0].closed:
            session, client_id = resumed
            self.permitted(session.id, view)
            view.client_id = client_id
            if client_id in session.views:
                raise PermissionError("This view is already connected")
            view.session = session
            view.token = hello['resume']
            if expiry := self.token_expiry.pop(view.token, None):
                expiry.cancel()
        else:
            # Selection needs a temporary Page, not another registry slot.
            # Existing-session joins must still work at max_sessions.
            session = Session(self, str(uuid4()), view.client_id)
            view.session = session
            handle = PageHandle(session, view)
            token = current_view.set(view)
            scope = current_session.set(session)
            try:
                await invoke(self.main, handle)
                session = view.session
                self.permitted(session.id, view)
                with self.registry_lock:
                    if session.id not in self.sessions:
                        if len(self.sessions) >= self.max_sessions:
                            raise RuntimeError("Web session limit reached")
                        self.sessions[session.id] = session
                if session.owner == view.client_id and not session.ready.done():
                    session.ready.set_result(None)
            except BaseException as error:
                session = view.session
                if session.owner == view.client_id:
                    if not session.ready.done():
                        session.ready.set_exception(error)
                    with self.registry_lock:
                        self.sessions.pop(session.id, None)
                    await session.dispose()
                raise
            finally:
                current_view.reset(token)
                current_session.reset(scope)
            view.token = secrets.token_urlsafe(32)
        await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(session.ready)), timeout=30)
        if session.closed:
            raise RuntimeError("Session closed during connection")
        self.tokens[view.token] = (session, view.client_id)
        if session.expiry:
            session.expiry.cancel()
            session.expiry = None
        session.views[view.client_id] = view
        session.start()
        self.deliver(view, dict(type="welcome", protocol=1, session=session.id,
                    client_id=view.client_id, resume=view.token))
        event = WebEvent('connect', session.page, session=session.id,
                         client_id=view.client_id, connection_count=len(session.views))
        session.enqueue(normalize_handlers(session.on_connect), event, view)
        try:
            await self.refresh(view)
        except Exception:
            await self.disconnect(view)
            self.tokens.pop(view.token, None)
            raise
        return view

    async def refresh(self, view):
        from .scene import build_scene, scene_patch
        session = view.session
        async with session.lock:
            message = scene_patch(view, build_scene(session, view), session)
            if message:
                self.deliver(view, message)

    async def disconnect(self, view):
        session = view.session
        session.views.pop(view.client_id, None)
        event = WebEvent('disconnect', session.page, session=session.id,
                         client_id=view.client_id, connection_count=len(session.views))
        session.enqueue(normalize_handlers(session.on_disconnect), event, view)
        def expire_token():
            self.tokens.pop(view.token, None)
            self.token_expiry.pop(view.token, None)
        self.token_expiry[view.token] = self.loop.call_later(self.session_ttl, expire_token)
        if not session.views:
            def expire():
                if not session.views:
                    with self.registry_lock:
                        self.sessions.pop(session.id, None)
                    self.tokens = {k:v for k,v in self.tokens.items() if v[0] is not session}
                    asyncio.create_task(session.dispose())
            session.expiry = self.loop.call_later(self.session_ttl, expire)

    async def receive(self, view, message):
        if not isinstance(message, dict):
            raise ValueError("Web messages must be JSON objects")
        kind = message.get('type')
        if kind in ('resize', 'resync'):
            previous = (view.width, view.height)
            self.viewport(message, view)
            view.needs_snapshot = kind == 'resync'
            await self.refresh(view)
            if kind == 'resize' and previous != (view.width, view.height):
                event = WebEvent('resize', view.session.page, session=view.session.id,
                    client_id=view.client_id, width=view.width, height=view.height)
                await self.execute(view, normalize_handlers(view.session.page.on_resize), event)
            return
        if kind == 'scroll':
            node = view.scene.get('nodes', {}).get(message.get('control'))
            if node is None or node['kind'] != 'scroll':
                raise ValueError("Unknown scroll target")
            if node.get('disabled'):
                raise ValueError("Scroll target is disabled")
            offset = message.get('offset', 0)
            if not isinstance(offset, (int, float)) or not math.isfinite(offset):
                raise ValueError("Invalid scroll offset")
            extent = node['bounds'][2 if node['horizontal'] else 3]
            view.scroll[node['control']] = max(0, min(max(0,node['content_size']-extent), offset))
            await self.refresh(view)
            return
        if kind == 'route':
            route = message.get('route')
            if not isinstance(route, str) or len(route) > 2048:
                raise ValueError("Invalid route")
            await self.execute(view, [lambda: view.session.page.go(route)], None)
            return
        if kind != 'event':
            raise ValueError("Unknown Web message type")
        identifier = message.get('id')
        if not isinstance(identifier, str) or len(identifier) > 128:
            raise ValueError("Event requires a bounded string ID")
        if identifier in view.seen_events:
            self.deliver(view, view.seen_events[identifier])
            return
        session = view.session
        control_id = message.get('control')
        control = session.controls.get(control_id)
        node = view.scene.get('nodes', {}).get(control_id)
        if control is None or node is None:
            raise ValueError("Control does not belong to this view")
        name = message.get('name')
        from ..widgets import TextField, Checkbox, Switch, Container, IconButton, Slider, Dropdown
        from ..widgets.dialogs import DialogControl
        from ..widgets.buttons import FilledButton
        supported = {'dismiss'} if isinstance(control,DialogControl) else (
            {'click'} if isinstance(control, (FilledButton.__mro__[1], Container, IconButton)) else (
            {'change', 'focus', 'blur', 'submit'} if isinstance(control, TextField) else
            {'change','change_start','change_end'} if isinstance(control,Slider) else
            {'select'} if isinstance(control,Dropdown) else
            {'change'} if isinstance(control, (Checkbox, Switch)) else set()))
        if name not in supported:
            raise ValueError("Event is not supported by this control")
        event = WebEvent(name, control, data=message.get('value'),
                         session=session.id, client_id=view.client_id, message_id=identifier)
        ack = dict(type='ack', id=identifier, control=control_id, version=message.get('version', 0))
        async def apply():
            if node.get('disabled'):
                raise ValueError("Control is disabled in this view")
            from ..widgets import AlertDialog
            barriers=[o for o in session.page.overlay if isinstance(o,AlertDialog)]
            if barriers:
                ancestors=[]
                ancestor=control
                while ancestor is not None:
                    ancestors.append(ancestor)
                    ancestor=ancestor.parent
                if barriers[-1] not in ancestors:
                    raise ValueError("Control is behind an open dialog")
            parent = control
            while parent is not None:
                if not parent.visible or parent.disabled or parent.page is not session.page:
                    raise ValueError("Control is disabled, hidden or detached")
                parent = parent.parent
            if name == 'dismiss':
                if control.modal:
                    raise ValueError("Modal dialog cannot be dismissed by its barrier")
                session.page.pop_dialog(control)
                return
            elif isinstance(control,Slider):
                value=message.get('value')
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                    raise ValueError("Slider value must be finite")
                value=max(control.min,min(control.max,value))
                if control.divisions and control.max>control.min:
                    step=(control.max-control.min)/control.divisions
                    value=control.min+round((value-control.min)/step)*step
                if control.round:
                    value=round(value,control.round)
                event.data=value
                if name=='change':
                    control.value=value
                    session.page.update()
            elif name == 'select':
                option=next((o for o in control.options if o.key==message.get('value') and o.visible and not o.disabled),None)
                if option is None:
                    raise ValueError("Unknown or disabled Dropdown option")
                control.value=option.key
                control.text=option.text or str(option.key)
                event.data=option.key
                session.page.update()
            elif name == 'change':
                if isinstance(control, TextField):
                    if control.read_only:
                        raise ValueError("TextField is read-only")
                    version, base = message.get('version'), message.get('input_revision')
                    if isinstance(version, bool) or not isinstance(version, int) or version <= view.input_versions.get(control_id, 0):
                        raise ValueError("Outdated edit version")
                    current = session.input_revisions.get(control_id, 0)
                    if base != current and session.input_owners.get(control_id) != view.client_id:
                        ack.update(conflict=True, value=control.value, input_revision=current)
                        return
                    value = message.get('value')
                    if not isinstance(value, str) or len(value.encode()) > self.max_message_bytes:
                        raise ValueError("Invalid text value")
                    from ..widgets.inputs import _filtered
                    value = _filtered(value, control.input_filter)
                    if control.max_length is not None and control.max_length >= 0:
                        value = value[:control.max_length]
                    control.value = value
                    session.input_revisions[control_id] = current+1
                    session.input_owners[control_id] = view.client_id
                    view.input_versions[control_id] = version
                else:
                    if not isinstance(message.get('value'), bool):
                        raise ValueError("Toggle value must be boolean")
                    control.value = message['value']
                event.data = control.value
                session.page.update()
            for callback in normalize_handlers(getattr(control, f'on_{name}', None)):
                from ..event import _invoke
                try:
                    await invoke(_invoke, callback, event)
                except Exception as error:
                    self.report(str(error), view)
            if isinstance(control, TextField):
                ack.update(value=control.value, input_revision=session.input_revisions.get(control_id, 0))
        await self.execute(view, [apply], event)
        view.seen_events[identifier] = ack
        if len(view.seen_events) > 256:
            view.seen_events.pop(next(iter(view.seen_events)))
        self.deliver(view, ack)

    async def execute(self, view, callbacks, event):
        done = asyncio.get_running_loop().create_future()
        view.session.enqueue(callbacks, event, view, done)
        await done

    @contextlib.asynccontextmanager
    async def lifespan(self):
        self.loop = asyncio.get_running_loop()
        self.closing = False
        try:
            yield self
        finally:
            await self.close()

    async def close(self):
        self.closing = True
        await asyncio.gather(*(s.dispose() for s in self.all_sessions()))
        self.sessions.clear()
        self.tokens.clear()
        for expiry in self.token_expiry.values():
            expiry.cancel()
        self.token_expiry.clear()
        self.resources.files.clear()


def create_app(main, **options):
    runtime = WebRuntime(main, **options)
    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with runtime.lifespan():
            yield
    app = FastAPI(lifespan=lifespan)
    app.state.saturn = runtime
    static = Path(__file__).with_name('static')
    @app.get('/', include_in_schema=False)
    async def index():
        return FileResponse(static/'index.html')
    @app.get('/static/{filename}', include_in_schema=False)
    async def asset(filename: str):
        if filename not in ('client.js', 'renderer.js', 'style.css'):
            raise HTTPException(404)
        return FileResponse(static/filename)
    @app.get('/resources/{identifier}', include_in_schema=False)
    async def resource(identifier: str):
        return runtime.resources.response(identifier)
    @app.websocket('/ws')
    async def websocket(socket: WebSocket):
        origin = socket.headers.get('origin')
        from urllib.parse import urlparse
        if origin and (origin not in runtime.allowed_origins if runtime.allowed_origins is not None
                       else urlparse(origin).netloc != socket.headers.get('host')):
            await socket.close(code=1008)
            return
        await socket.accept()
        view = sender = None
        try:
            raw = await asyncio.wait_for(socket.receive_text(), timeout=10)
            if len(raw.encode()) > runtime.max_message_bytes:
                raise ValueError("Hello message is too large")
            hello = json.loads(raw)
            if not isinstance(hello, dict) or hello.get('type') != 'hello' or hello.get('protocol') != 1:
                raise ValueError("Unsupported Web protocol")
            view = await runtime.connect(socket, hello)
            async def send():
                while True:
                    await socket.send_json(await view.outbox.get())
            sender = asyncio.create_task(send())
            while True:
                raw = await socket.receive_text()
                try:
                    if len(raw.encode()) > runtime.max_message_bytes:
                        raise ValueError("Web message is too large")
                    await runtime.receive(view, json.loads(raw))
                except (ValueError, TypeError, RuntimeError) as error:
                    runtime.report(str(error), view)
        except WebSocketDisconnect:
            pass
        except Exception as error:
            with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                await socket.send_json(dict(type='error', error=str(error)))
                await socket.close(code=1008)
        finally:
            if sender:
                sender.cancel()
                await asyncio.gather(sender, return_exceptions=True)
            if view:
                await runtime.disconnect(view)
    return app
