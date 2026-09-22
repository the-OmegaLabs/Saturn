"""Scrolling self-check (milestone 10): ListView offset/clipping/wheel,
GestureDetector tap events. Headless + assert-based.
"""
import sys
import threading
import time
from unittest.mock import patch

sys.path.insert(0, ".")

import pygame

import saturn as ft
from saturn.widgets.containers import Container
from saturn.widgets.buttons import FilledButton
from saturn.widgets.scrolling import GestureDetector, ListView
from saturn.widgets.text import Text


def approx(a, b, tol=1.0):
    return abs(a - b) <= tol


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
    assert first[:2] == (10.0, 10.0) and approx(first[2], 200), first
    assert 40 <= first[3] <= 42, first  # button height tracks font metrics
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


def check_scrolled_children_paint_at_offset():
    first = Container(
        Text("first"), height=34, bgcolor=ft.Colors.SURFACE_CONTAINER,
        border_radius=6)
    second = FilledButton("second")
    lv = ListView(first, second, spacing=4, height=40, width=200)
    app, page = make_page(lv)
    original_y = first._rect[1]
    lv._wheel(20)
    with patch.object(app.renderer, "fill_rect",
                      wraps=app.renderer.fill_rect) as fill_rect:
        page.draw()
    expected_y = original_y - lv._offset
    matching = [call.args for call in fill_rect.call_args_list
                if len(call.args) >= 4
                and call.args[0] == first._rect[0]
                and call.args[2] == first._rect[2]
                and call.args[3] == first._rect[3]]
    assert matching and matching[0][1] == expected_y, matching
    print("scrolled child paint offset ok")


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
    assert app._dirty.is_set(), "wheel scroll did not request a redraw"
    print("wheel routing ok")


def check_scrollbar_drag():
    lv = ListView(
        controls=[Container(Text(f"row {i}"), height=30) for i in range(30)],
        height=120, width=200,
    )
    app, page = make_page(lv)
    page.draw()
    geometry = lv._scrollbar_geometry()
    assert geometry is not None
    track, thumb, _travel = geometry
    assert thumb[2] == 8.0, thumb
    x = thumb[0] + thumb[2] / 2
    y = thumb[1] + thumb[3] / 2
    page.pointer_down(x, y)
    assert page._pressed is lv and lv._scrollbar_dragging
    assert lv._raw("_scrollbar_thickness") == 12.0
    assert lv._raw("_scrollbar_opacity") == 0.64
    page.pointer_move(x, y + 60)
    assert lv._offset > 0
    dragged = lv._offset
    page.pointer_up(x, y + 60)
    assert not lv._scrollbar_dragging and lv._offset == dragged
    print("scrollbar drag ok")


def check_scrollbar_material_states():
    lv = ListView(
        controls=[Container(Text(f"row {i}"), height=30) for i in range(30)],
        height=120, width=200,
    )
    app, page = make_page(lv)
    page.draw()
    _track, thumb, _travel = lv._scrollbar_geometry()
    assert lv._scrollbar_opacity == 0.0

    # Material desktop behavior: an invisible 16px hit target reveals a wider
    # thumb on hover, while the track itself remains unpainted.
    page.pointer_move(thumb[0] + thumb[2] / 2,
                      thumb[1] + thumb[3] / 2)
    assert lv._scrollbar_hovered
    assert lv._raw("_scrollbar_thickness") == 12.0
    assert lv._raw("_scrollbar_opacity") == 0.64
    lv._tick_animations(time.perf_counter() + 1.0)
    assert lv._scrollbar_geometry()[1][2] == 12.0

    page.pointer_move(lv._rect[0] + 10, lv._rect[1] + 10)
    assert not lv._scrollbar_hovered and lv._scrollbar_hide_at is not None
    now = time.perf_counter() + 1.0
    lv._tick_animations(now)
    assert lv._raw("_scrollbar_opacity") == 0.0
    lv._tick_animations(now + 1.0)
    assert lv._scrollbar_opacity == 0.0
    print("scrollbar material states ok")


def check_pygame_wheel_direction_and_controls_keyword():
    lv = ListView(
        controls=[Container(Text(f"row {i}"), height=30) for i in range(20)],
        height=100, width=200,
    )
    app, page = make_page(lv)
    page.draw()
    x, y = int(lv._rect[0] + 5), int(lv._rect[1] + 5)
    page._wheel(-(-1) * 40, x, y)
    assert lv._offset == 40, lv._offset
    page._wheel(-(1) * 40, x, y)
    assert lv._offset == 0, lv._offset
    # Match the actual event conversion as well as direct wheel routing.
    with patch("pygame.mouse.get_pos", return_value=(x, y)):
        page.handle_event(pygame.event.Event(
            pygame.MOUSEWHEEL, {"y": -1, "x": 0}))
    assert lv._offset == 40, lv._offset
    print("pygame wheel direction ok")


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
    check_scrolled_children_paint_at_offset()
    check_listview_wheel_routing()
    check_scrollbar_drag()
    check_scrollbar_material_states()
    check_pygame_wheel_direction_and_controls_keyword()
    check_gesture_detector()
    print("ALL SCROLLING TESTS PASS")
