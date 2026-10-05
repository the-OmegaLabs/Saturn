"""ControlEvent values and handler dispatch.

Handlers may take zero args or one event arg, sync or async — dispatch runs
them off the UI thread via App.call.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any


@dataclass
class ControlEvent:
    name: str
    control: "Control"  # noqa: F821
    data: Any = None

    @property
    def page(self):
        return self.control.page

    @classmethod
    def __class_getitem__(cls, item):
        # Handler annotations like `def on_hover(e: HoverEvent[Container])`
        # evaluate at definition time; the payload type carries no runtime
        # information, so subscripting is a no-op.
        return cls


@dataclass
class PageResizeEvent(ControlEvent):
    width: float = 0
    height: float = 0


@dataclass
class KeyboardEvent(ControlEvent):
    key: str = ""
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    meta: bool = False


@dataclass
class PlatformBrightnessChangeEvent(ControlEvent):
    brightness: str = "light"


@dataclass
class TextSelectionChangeEvent(ControlEvent):
    selection: object = None
    text: str = ""


@dataclass
class LayoutSizeChangeEvent(ControlEvent):
    width: float = 0
    height: float = 0


@dataclass
class RouteChangeEvent(ControlEvent):
    route: str = "/"


@dataclass
class RenderFailedEvent(ControlEvent):
    backend: str = ""
    gpu: str | int | None = None
    error: str = ""
    message: str = "Saturn can't use your current GPU, fallback to software renderer."
    fallback: str = "software"


@dataclass
class RenderReadyEvent(ControlEvent):
    backend: str = ""
    gpu_name: str | None = None
    gpu_index: int | None = None
    fallback: bool = False


@dataclass
class FontOptimizeEvent(ControlEvent):
    font: str = ""
    weight: int | None = None
    status: str = "started"
    success: bool | None = None
    error: str | None = None
    operation: str = "instance"
    cached: bool = False


@dataclass
class TapEvent:
    kind: str
    local_position: tuple
    global_position: tuple

    @property
    def page(self):
        return None  # wired by fire() wrapper when possible


def normalize_handlers(hs) -> list:
    """Accept a single callback and the existing callback-list syntax."""
    if hs is None:
        return []
    result = [hs] if callable(hs) else list(hs)
    if not all(callable(handler) for handler in result):
        raise TypeError("event handlers must be callable")
    return result


def handlers_of(control, name: str) -> list:
    return normalize_handlers(getattr(control, f"on_{name}", None))


def fire(control, name: str, data: Any = None) -> None:
    """Dispatch an event to the control's on_<name> handlers."""
    if control.page is None:
        return
    if name == "click" and getattr(control, "url", None):
        import webbrowser
        value = control.url
        control.page._app.call(webbrowser.open, str(getattr(value, "url", value)))
    ev = ControlEvent(name=name, control=control, data=data)
    dispatch_event(control, name, ev)


def dispatch_event(control, name: str, ev) -> None:
    """Dispatch a typed payload with the ordinary handler conventions."""
    if control.page is None:
        return
    hs = handlers_of(control, name)
    for h in hs:
        control.page._app.call(_invoke, h, ev)


def _invoke(h, ev):
    try:
        n = len(inspect.signature(h).parameters)
    except (TypeError, ValueError):
        n = 1
    # App.call also awaits returned awaitables, including wrapped async
    # callbacks and ordinary callbacks which return a coroutine.
    return h(ev) if n else h()
