"""Second migration batch: AnimatedSwitcher, NavigationRail, PopupMenuButton,
InputBorder / NumbersOnlyInputFilter, Event annotations, foreign-control guard."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saturn as st
from saturn.app import App, Renderer
from saturn.widgets.inputs import _filtered


def pump(app, predicate=lambda: True, timeout=5.0):
    deadline = time.perf_counter() + timeout
    while True:
        app._pump_once()
        if predicate():
            return
        assert time.perf_counter() < deadline, "window operation timed out"
        time.sleep(0.01)


def check_event_annotations():
    assert st.Event[st.Container] is st.ControlEvent
    assert st.HoverEvent[st.Container] is st.ControlEvent
    print("Event/HoverEvent annotations OK")


def check_input_border_and_filter():
    for border in (st.InputBorder.NONE, st.InputBorder.OUTLINE,
                   st.InputBorder.UNDERLINE, st.InputBorder.FILLED):
        field = st.TextField("1", border=border)
        assert field.border is border
    assert _filtered("12a", st.NumbersOnlyInputFilter()) == "12"
    assert _filtered("1.5", st.NumbersOnlyInputFilter()) == "15"
    assert _filtered("007", st.NumbersOnlyInputFilter()) == "007"
    # border=NONE must actually suppress the border stroke in the draw path
    def main(page):
        page.add(st.Container(st.TextField("0.8", border=st.InputBorder.NONE,
                                           input_filter=st.NumbersOnlyInputFilter()),
                              width=120, height=48))
    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app)
    finally:
        app.close()
        app.run_until_closed()
    print("InputBorder / NumbersOnlyInputFilter OK")


def check_animated_switcher():
    def main(page):
        a = st.Text("A")
        b = st.Text("B")
        switcher = st.AnimatedSwitcher(duration=60, reverse_duration=60,
                                       content=a, key="sw")
        page.add(st.Container(switcher, width=100, height=40,
                              alignment=st.Alignment.CENTER))
        page._a, page._b, page._sw = a, b, switcher

    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        page = app.page
        pump(app)
        switcher, a, b = page._sw, page._a, page._b
        assert switcher.controls == [a], switcher.controls
        assert a.page is page and a.parent is switcher

        # swap A -> B: A keeps animating below B, both stay attached
        switcher.content = b
        assert switcher.controls == [a, b], switcher.controls
        assert a.page is page and b.page is page
        # rapid swap back to A while A is still fading out must not duplicate
        pump(app)  # settle one frame
        switcher.content = a
        assert switcher.controls == [b, a], switcher.controls
        assert switcher.controls.count(a) == 1
        pump(app, lambda: switcher.controls == [a])
        assert b.page is None and b.parent is None, (b.page, b.parent)
        assert a.page is page

        # ROTATION and SCALE transitions must draw without errors
        for transition in (st.AnimatedSwitcherTransition.ROTATION,
                           st.AnimatedSwitcherTransition.SCALE):
            switcher.transition = transition
            switcher.content = b
            pump(app)
            switcher.content = a
            pump(app, lambda: switcher.controls == [a])
        print("AnimatedSwitcher swap/fade/cleanup OK")
    finally:
        app.close()
        app.run_until_closed()


def check_navigation_rail():
    events = []

    def main(page):
        rail = st.NavigationRail(
            destinations=[st.NavigationRailDestination(icon=st.Icons.HOME, label="主页"),
                          st.NavigationRailDestination(icon=st.Icons.EDIT, label="话术"),
                          st.NavigationRailDestination(icon=st.Icons.SETTINGS, label="设置")],
            expand=True, on_change=lambda e: events.append(e.data))
        page.add(st.Row(st.Column(rail, width=72), st.Container(st.Text("body"), expand=True),
                        expand=True, spacing=0))
        page._rail = rail

    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        page = app.page
        pump(app)
        rail = page._rail
        assert rail.selected_index is None
        assert len(rail._children()) == 3
        # click the second destination
        item = rail._children()[1]
        x, y = item._rect[0] + item._rect[2] / 2, item._rect[1] + item._rect[3] / 2
        page.pointer_down(x, y)
        page.pointer_up(x, y)
        pump(app)
        assert events == [1], events
        assert rail.selected_index == 1
        # clicking the same destination again must not fire on_change
        page.pointer_down(x, y)
        page.pointer_up(x, y)
        pump(app)
        assert events == [1], events
        # the app's route_to indexes e.data
        routes = ["/home", "/script", "/settings"]
        assert routes[events[0]] == "/script"
        print("NavigationRail select/on_change OK")
    finally:
        app.close()
        app.run_until_closed()


def check_popup_menu():
    picked = []

    def main(page):
        item = st.PopupMenuItem(content=st.Text("高"), height=40,
                                on_click=lambda e: picked.append("high"))
        button = st.PopupMenuButton(
            content=st.Container(st.Text("思考"), width=122, height=34,
                                 alignment=st.Alignment.CENTER),
            padding=0, tooltip="思考深度",
            items=[st.PopupMenuItem(content=st.Text("默认"), height=40),
                   item])
        page.add(button)
        page._button, page._item = button, item

    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        page = app.page
        pump(app)
        button, item = page._button, page._item
        bx, by = button._rect[0] + 10, button._rect[1] + button._rect[3] / 2

        page.pointer_down(bx, by)
        page.pointer_up(bx, by)
        pump(app, lambda: button.open and button._menu_surface is not None)
        surface = button._menu_surface
        assert surface in page.overlay
        assert len(surface.items) == 2
        # rows must be laid out inside the surface
        assert surface.items[0]._rect[3] == 40

        # click the second row ("高")
        row = surface.items[1]
        rx, ry = row._rect[0] + row._rect[2] / 2, row._rect[1] + row._rect[3] / 2
        page.pointer_down(rx, ry)
        page.pointer_up(rx, ry)
        pump(app, lambda: not button.open)
        assert picked == ["high"], picked
        pump(app, lambda: surface not in page.overlay and button._menu_surface is None,
             timeout=2.0)

        # barrier click closes the menu and must not reach the page below
        page.pointer_down(bx, by)
        page.pointer_up(bx, by)
        pump(app, lambda: button.open)
        surface2 = button._menu_surface
        far_x, far_y = page.width - 5, page.height - 5
        page.pointer_down(far_x, far_y)
        page.pointer_up(far_x, far_y)
        pump(app, lambda: not button.open)
        pump(app, lambda: surface2 not in page.overlay, timeout=2.0)
        assert picked == ["high"]
        print("PopupMenuButton open/pick/barrier OK")
    finally:
        app.close()
        app.run_until_closed()


def check_foreign_control_guard():
    class FakeFletColumn:
        """Stands in for a control created by `import flet` (not saturn)."""

    def flet_module_column():
        cls = type("Column", (), {})
        cls.__module__ = "flet.controls.containers"
        return cls()

    def main(page):
        page._ready = True

    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        page = app.page
        pump(app, lambda: getattr(page, "_ready", False))
        fake = FakeFletColumn()
        try:
            page.add(fake)
        except TypeError as error:
            assert "not a Saturn control" in str(error), error
        else:
            raise AssertionError("foreign control must raise a clear TypeError")
        try:
            page.add(flet_module_column())
        except TypeError as error:
            assert "import saturn" in str(error), error
        else:
            raise AssertionError("flet-module control must name the import fix")
        # add() must reject BEFORE mutating: the tree stays clean and the
        # event pump keeps working instead of crashing on the next frame.
        assert fake not in page.controls
        pump(app)
    finally:
        app.close()
        app.run_until_closed()
    print("foreign-control guard OK")


if __name__ == "__main__":
    check_event_annotations()
    check_input_border_and_filter()
    check_animated_switcher()
    check_navigation_rail()
    check_popup_menu()
    check_foreign_control_guard()
    print("ALL MIGRATION-2 CHECKS PASS")
