"""One observable application route shared by its native windows."""
import threading
import weakref
from .event import RouteChangeEvent


class RouteState:
    def __init__(self):
        self.route = "/"
        self._pages = weakref.WeakSet()
        self._lock = threading.RLock()

    def register(self, page):
        with self._lock:
            self._pages.add(page)

    def unregister(self, page):
        with self._lock:
            self._pages.discard(page)

    def go(self, route):
        if not isinstance(route, str):
            raise TypeError("route must be a string")
        with self._lock:
            if route == self.route:
                return
            self.route = route
            for page in tuple(self._pages):
                closed = getattr(page._app, "_closed", None)
                if closed is None or not closed.is_set():
                    page._dispatch(page.on_route_change, RouteChangeEvent(
                        "route_change", page, data=route, route=route))
