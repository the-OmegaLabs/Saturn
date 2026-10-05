"""Migration-gap controls: DialogControl export, VerticalDivider, Clipboard and WindowDragArea."""
import sys
import time
import unittest.mock as mock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
import saturn as st
from saturn.app import App, Renderer


MARKER = "saturn-gap-check-8f2c"


def pump(app, predicate=lambda: True, timeout=5.0):
    deadline = time.perf_counter() + timeout
    while True:
        app._pump_once()
        if predicate():
            return
        assert time.perf_counter() < deadline, "window operation timed out"
        time.sleep(0.01)


def check_dialog_control_export():
    from saturn.widgets.dialogs import DialogControl as real
    assert st.DialogControl is real, "st.DialogControl must be the dialogs base class"
    class custom(st.DialogControl):
        pass
    assert custom is not None
    print("DialogControl export OK")


def check_clipboard():
    async def main(page):
        clip = st.Clipboard()
        await clip.set(MARKER)
        page._clip_result = await clip.get()
    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app, lambda: getattr(app.page, "_clip_result", None) is not None)
        assert app.page._clip_result == MARKER, app.page._clip_result
        print("Clipboard set/get OK")
    finally:
        app.close()
        app.run_until_closed()


def check_vertical_divider():
    def main(page):
        page.bgcolor = "#193047"
        divider = st.VerticalDivider(21, thickness=3)
        box = st.Container(divider, width=41, height=61, bgcolor="#6B2941")
        page.add(box)
        page._box, page._divider = box, divider
    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app)
        app.page.draw()
        shot = app.page._app.renderer.screenshot()
        from saturn import colors
        bg = (107, 41, 65)
        line = colors.parse_color(colors.Colors.OUTLINE_VARIANT)[:3]
        dx, dy, dw, dh = page_divider = app.page._divider._rect
        bx, by, _, _ = app.page._box._rect
        cx, cy = round(dx + (dw - 3) / 2), dy + dh // 2
        assert shot.get_at((cx, cy))[:3] == line, ("line missing", shot.get_at((cx, cy)), page_divider)
        assert shot.get_at((bx + 2, cy))[:3] == bg, "unexpected fill left of the line"
        assert shot.get_at((cx, by + 3))[:3] == line, "line must span the container height"
        print("VerticalDivider draw OK")
    finally:
        app.close()
        app.run_until_closed()


def check_window_drag_area():
    events, calls, maximized, clicks = [], [], [], []
    def main(page):
        area = st.WindowDragArea(
            st.Row([
                st.Container(st.Text("btn"), bgcolor="#243B42", width=40, height=25,
                             on_click=lambda e: clicks.append("btn")),
                st.Text("title", expand=True),
            ], spacing=0),
            on_drag_start=lambda e=None: events.append("start"),
            on_drag_end=lambda e=None: events.append("end"))
        page.add(area)
        page._area = area
    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        page = app.page
        pump(app)
        area = page._area
        window = page.window
        window._native.start_interaction = lambda hit: calls.append(hit)
        row = area.content
        button, title = row.controls
        # press on the plain title text starts the native drag
        tx, ty = title._rect[0] + 8, title._rect[1] + 5
        page.pointer_down(tx, ty)
        pump(app, lambda: len(calls) == 1 and "end" in events)
        assert calls == [2], calls
        assert "start" in events and "end" in events, events
        page.pointer_up(tx, ty)
        pump(app)
        # a press on the interactive child clicks it instead of dragging
        bx, by = button._rect[0] + 20, button._rect[1] + 12
        page.pointer_down(bx, by)
        assert page._pressed is button, page._pressed
        page.pointer_up(bx, by)
        pump(app)
        assert clicks == ["btn"], (clicks, calls)
        assert len(calls) == 1, calls  # button press must not start a drag
        # double press toggles maximize instead of dragging
        with mock.patch.object(type(window), "maximized",
                               property(lambda self: False,
                                        lambda self, v: maximized.append(v))):
            area._last_press = None
            area._pressed_hook(tx, ty)
            area._pressed_hook(tx, ty)
        pump(app)
        assert maximized == [True], (maximized, calls)
        assert len(calls) == 2, calls  # each first-of-pair press starts a drag
        print("WindowDragArea drag/click-through/double-tap OK")
    finally:
        app.close()
        app.run_until_closed()


if __name__ == "__main__":
    check_dialog_control_export()
    check_clipboard()
    check_vertical_divider()
    check_window_drag_area()
    print("ALL WIDGET GAP CHECKS PASS")
