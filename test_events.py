"""Events self-check (milestone 7): hit testing, click/hover dispatch.

Assert-based, headless (no window); handlers run on real worker threads.
Run: .venv/Scripts/python.exe test_events.py
"""
import sys
import threading
import time

sys.path.insert(0, ".")

import saturn as ft
from saturn.widgets.buttons import IconButton, OutlinedButton
from saturn.widgets.containers import Container
from saturn.widgets.text import Text


class Rec:
    """Callable handler recording events; .ev set on first call."""
    def __init__(self):
        self.items = []
        self.ev = threading.Event()

    def __call__(self, e=None):
        self.items.append(e)
        self.ev.set()

    def wait(self, timeout=2.0):
        return self.ev.wait(timeout)


def make_page(*controls):
    from saturn.app import App
    app = App(lambda p: None, ft.Render.SOFTWARE, 800, 600, "t")
    app.start()
    page = app.page
    for c in controls:
        page.add(c)
    page.draw()
    return app, page


def center(c):
    return c._rect[0] + c._rect[2] / 2, c._rect[1] + c._rect[3] / 2


def check_click():
    app, page = make_page()
    clicks, events = Rec(), Rec()
    btn = ft.ElevatedButton("Hit me", on_click=clicks)
    btn2 = ft.TextButton("Two", on_click=events)
    page.add(btn, btn2)
    page.draw()
    page.pointer_down(*center(btn))
    page.pointer_up(*center(btn))
    assert clicks.wait(), "on_click never fired"
    page.pointer_down(*center(btn2))
    page.pointer_up(*center(btn2))
    assert events.wait(), "second button never fired"
    e = events.items[0]
    assert e.control is btn2 and e.page is page and e.name == "click"
    print("click ok")


def check_click_miss():
    app, page = make_page()
    hits = Rec()
    btn = ft.FilledButton("A", on_click=hits)
    page.add(btn)
    page.draw()
    page.pointer_down(700, 500)  # outside
    page.pointer_up(700, 500)
    page.pointer_down(*center(btn))
    page.pointer_up(btn._rect[0] + 300, btn._rect[1] + 2)  # released outside
    time.sleep(0.2)
    assert hits.items == [], "click fired on miss/release-outside"
    print("click-miss ok")


def check_hover():
    app, page = make_page()
    hov = Rec()
    btn = OutlinedButton("H", on_hover=hov)
    page.add(btn)
    page.draw()
    page.pointer_move(btn._rect[0] + 2, btn._rect[1] + 2)
    page.pointer_move(btn._rect[0] + 3, btn._rect[1] + 3)  # still inside
    page.pointer_move(700, 500)                            # exit
    assert hov.wait(), "hover never fired"
    datas = [i.data for i in hov.items]
    assert "true" in datas and "false" in datas, datas
    assert datas.count("true") == 1, datas
    print("hover ok")


def check_disabled():
    app, page = make_page()
    hits = Rec()
    btn = ft.FilledButton("D", on_click=hits)
    btn.disabled = True
    page.add(btn)
    page.draw()
    page.pointer_down(*center(btn))
    page.pointer_up(*center(btn))
    time.sleep(0.2)
    assert hits.items == [], "disabled button fired"
    print("disabled ok")


def check_nested():
    app, page = make_page()
    outer_hits, inner_hits = Rec(), Rec()
    inner = Container(Text("in"), bgcolor=ft.Colors.PRIMARY_CONTAINER,
                      padding=10, on_click=inner_hits)
    outer = Container(inner, padding=30, on_click=outer_hits)
    page.add(outer)
    page.draw()
    page.pointer_down(*center(inner))
    page.pointer_up(*center(inner))
    page.pointer_down(outer._rect[0] + 2, outer._rect[1] + 2)
    page.pointer_up(outer._rect[0] + 2, outer._rect[1] + 2)
    assert inner_hits.wait() and outer_hits.wait()
    assert len(inner_hits.items) == 1 and len(outer_hits.items) == 1
    print("nested click ok (inner wins, outer fires on its own area)")


def check_icon_button():
    app, page = make_page()
    hits = Rec()
    ib = IconButton(ft.Icons.ADD, on_click=hits)
    page.add(ib)
    page.draw()
    page.pointer_down(*center(ib))
    page.pointer_up(*center(ib))
    assert hits.wait()
    print("icon button ok")


if __name__ == "__main__":
    check_click()
    check_click_miss()
    check_hover()
    check_disabled()
    check_nested()
    check_icon_button()
    print("ALL EVENT TESTS PASS")
