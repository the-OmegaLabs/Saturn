"""Execution-local origin, with no mutable client identity on shared Pages."""
from contextvars import ContextVar

current_view = ContextVar("saturn_web_view", default=None)
current_session = ContextVar("saturn_web_session", default=None)


class NativeWindowUnavailable:
    def __getattr__(self, name):
        raise NotImplementedError(f"page.window.{name} requires a desktop window; use page.web")

    def __setattr__(self, name, value):
        raise NotImplementedError(f"page.window.{name} requires a desktop window; use page.web")
