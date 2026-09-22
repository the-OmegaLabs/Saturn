"""Event model: ControlEvent + handler dispatch (flet semantics).

Handlers may take zero args or one event arg, sync or async — dispatch runs
them off the UI thread via App.call.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ControlEvent:
    name: str
    control: "Control"  # noqa: F821
    data: Any = None

    @property
    def page(self):
        return self.control.page


@dataclass
class TapEvent:
    kind: str
    local_position: tuple
    global_position: tuple

    @property
    def page(self):
        return None  # wired by fire() wrapper when possible


def handlers_of(control, name: str) -> list:
    hs = getattr(control, f"on_{name}", None)
    if hs is None:
        return []
    return [hs] if callable(hs) else list(hs)


def fire(control, name: str, data: Any = None) -> None:
    """Dispatch an event to the control's on_<name> handlers."""
    hs = handlers_of(control, name)
    if not hs:
        return
    if control.page is None:
        return
    ev = ControlEvent(name=name, control=control, data=data)
    for h in hs:
        control.page._app.call(_invoke, h, ev)


def _invoke(h, ev):
    try:
        n = len(inspect.signature(h).parameters)
    except (TypeError, ValueError):
        n = 1
    h(ev) if n else h()
