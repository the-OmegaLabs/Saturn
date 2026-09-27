"""Execution-local origin, with no mutable client identity on shared Pages."""
from contextvars import ContextVar

current_view = ContextVar("saturn_web_view", default=None)
current_session = ContextVar("saturn_web_session", default=None)


class WebWindow:
    """Ignore native-window mutations so one entry point can run on the Web."""
    def __init__(self, page):
        object.__setattr__(self, '_page', page)
        object.__setattr__(self, '_values', {})

    def __getattr__(self, name):
        from ..window import Window
        if name in ('page', 'parent'):
            return self._page
        if name in ('hwnd', 'native_handle'):
            return 0
        if name in ('width', 'height', 'title'):
            return getattr(self._page, name)
        defaults = dict(left=0, top=0, focused=False, visible=True,
                        full_screen=False, maximized=False, minimized=False,
                        icon=None, on_event=None, data=None, key=None)
        if name in defaults:
            return defaults[name]
        member = getattr(Window, name, None)
        if isinstance(member, property) and member.__doc__ and member.__doc__.startswith('Native window'):
            return member.fget(self)
        if callable(member) and not name.startswith('_'):
            return lambda *args, **kwargs: None
        raise AttributeError(name)

    def __setattr__(self, name, value):
        from ..window import Window
        if name in ('on_event', 'data', 'key') or isinstance(getattr(Window, name, None), property):
            return
        raise AttributeError(name)
