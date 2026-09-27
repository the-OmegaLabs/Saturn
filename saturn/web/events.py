"""Ordered, JSON-safe named messages scoped to logical Pages."""
import json
import threading
from dataclasses import dataclass
from uuid import uuid4
from ..event import ControlEvent
from .context import current_view


@dataclass
class WebEvent(ControlEvent):
    session: str = ""
    client_id: str | None = None
    message_id: str | None = None
    sequence: int = 0
    connection_count: int = 0
    width: int = 0
    height: int = 0


class WebEvents:
    def __init__(self, settings):
        self.settings = settings
        self.handlers = {}
        self.lock = threading.RLock()

    @staticmethod
    def _key(name, scope):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("sub_name must be a nonempty string")
        if scope not in ("session", "app"):
            raise ValueError("scope must be session or app")
        return scope, name

    def subscribe(self, sub_name, handler, *, scope="session"):
        key = self._key(sub_name, scope)
        if not callable(handler):
            raise TypeError("handler must be callable")
        session = self.settings._session
        if session.closed:
            raise RuntimeError("Session is closed")
        with self.lock:
            handlers = self.handlers.setdefault(key, [])
            if handler not in handlers:
                handlers.append(handler)
        session.locked = True

    def unsubscribe(self, sub_name, *, handler=None, scope="session"):
        key = self._key(sub_name, scope)
        with self.lock:
            if handler is None:
                self.handlers.pop(key, None)
            else:
                callbacks = self.handlers.get(key, [])
                if handler in callbacks:
                    callbacks.remove(handler)
                if not callbacks:
                    self.handlers.pop(key, None)

    def send(self, sub_name, data, *, scope="session"):
        key = self._key(sub_name, scope)
        def validate(value):
            if isinstance(value, dict):
                if any(not isinstance(k, str) for k in value):
                    raise TypeError("message dictionary keys must be strings")
                for child in value.values():
                    validate(child)
            elif isinstance(value, list):
                for child in value:
                    validate(child)
            elif value is not None and not isinstance(value, (str, int, float, bool)):
                raise TypeError("message data must be JSON-safe")
        try:
            validate(data)
            encoded = json.dumps(data, allow_nan=False, ensure_ascii=False)
        except RecursionError:
            raise ValueError("message data is cyclic or too deeply nested") from None
        session = self.settings._session
        if session.closed:
            raise RuntimeError("Session is closed")
        if len(encoded.encode()) > session.runtime.max_message_bytes:
            raise ValueError("message payload exceeds max_message_bytes")
        message_id = str(uuid4())
        view = current_view.get()
        origin = view.client_id if view else None
        def publish():
            targets = [session] if scope == "session" else session.runtime.all_sessions()
            if scope == "app" and session not in targets:
                targets.append(session)
            for target in targets:
                if target.closed:
                    continue
                with target.page.web.events.lock:
                    callbacks = list(target.page.web.events.handlers.get(key, []))
                target.sequence += 1
                event = WebEvent(sub_name, target.page, data=json.loads(encoded),
                    session=target.id, client_id=origin, message_id=message_id,
                    sequence=target.sequence)
                target.enqueue(callbacks, event, view if view and view.session is target else None)
        session.runtime.schedule(publish)
        return message_id

    def clear(self):
        with self.lock:
            self.handlers.clear()
