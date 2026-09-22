"""Scrolling self-check (milestone 10): ListView offset/clipping/wheel,
GestureDetector tap events. Headless + assert-based.
"""
import sys
import threading

sys.path.insert(0, ".")

import saturn as ft
from saturn.widgets.buttons import FilledButton
from saturn.widgets.scrolling import GestureDetector, ListView
from saturn.widgets.text import Text


class Rec:
    def __init__(self):
        self.items = []
        self.ev = threading.Event()

    def __call__(self, e=None):
        self.items.append(getattr(e, "data", 1) if not hasattr(e, "kind") else e)
        self.ev.set()

    def wait(self, timeout=2.0):
        return self.ev.wait(timeout)


def make_page(*controls, height=300):
    from saturn.app import App
    app = App(lambda p: None, ft.Render.SOFTWARE, 400, height, "t")
    app.start()
    page = app.page
    for c in controls:
        page.add(c)
    page.draw()
    return app, page


def check_listview_scroll():
    items = [FilledButton(f"item {i}") for i in range(20)]
    lv = ListView(*items, spacing=4, height=200, width=200)
    app, page = make_page(lv)  # page.draw() lays out: lv at (10,10,200,200)
    assert lv._content_size > 200, lv._content_size  # 20 x 40px + spacing
    first = items[0]._rect
    assert first == (10.0, 10.0, 200.0, 40.0), first
    # wheel down 100px: item 0 moves up out of view (draw offset), hit maps back
    lv._wheel(100)
    page.draw()
    assert lv._offset == 100, lv._offset
    hit = lv._hit_test(100, 60)  # screen y=60 -> content y=160 -> item 3
    assert hit is not None and hit is not items[0], hit
    assert hit.content == "item 3", hit.content
    lv.scroll_to(0)
    assert lv._offset == 0
    print("listview ok")


def check_listview_wheel_routing():
    lv = ListView(*[Text(f"row {i}") for i in range(30)], height=100, width=200)
    app, page = make_page(lv)
    lv._place(10, 10, 200, 100, 1.0)
    page.draw()
    off0 = lv._offset
    page._wheel(-40, 100, 50)  # up at top -> stays 0
    assert lv._offset == 0
    page._wheel(40, 100, 50)
    assert lv._offset == 40, lv._offset
    print("wheel routing ok")


def check_gesture_detector():
    app, page = make_page()
    taps, downs = Rec(), Rec()
    gd = GestureDetector(Text("tap me"), on_tap=taps, on_tap_down=downs)
    page.add(gd)
    page.draw()
    x, y = gd._rect[0] + gd._rect[2] / 2, gd._rect[1] + gd._rect[3] / 2
    page.pointer_down(x, y)
    page.pointer_up(x, y)
    assert taps.wait() and downs.wait()
    tap = taps.items[0]
    assert tap.kind == "tap"
    down = downs.items[0]
    assert down.kind == "down" and down.local_position[0] > 0
    print("gesture detector ok")


if __name__ == "__main__":
    check_listview_scroll()
    check_listview_wheel_routing()
    check_gesture_detector()
    print("ALL SCROLLING TESTS PASS")
