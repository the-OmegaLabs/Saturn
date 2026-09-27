"""Native ownership, renderer isolation, routing and child-window lifecycle."""
import ctypes
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
import saturn as st
from saturn.app import App


def check(backend):
    app = App(lambda page: None, backend)
    app.start()
    def pump(predicate=lambda: True):
        deadline = time.perf_counter()+5
        while True:
            app._pump_once()
            if predicate():
                return
            assert time.perf_counter() < deadline, "Native window operation timed out"
            time.sleep(.01)
    try:
        page = app.page
        page.bgcolor = "#193047"
        page.renderer.vsync = False
        seen, ready = [], []
        page.on_route_change = lambda e: seen.append(("parent", e.route))
        child = page.open_subpage(lambda p: ready.append(p.window.hwnd), title="Native settings")
        child.window.width, child.window.height = 340, 250
        child.renderer.vsync = False
        child.bgcolor = "#6B2941"
        field = st.TextField("child")
        child.add(field)
        child.on_route_change = lambda e: seen.append(("child", e.route))
        pump(lambda: child.ready and bool(ready))
        assert ready[0] and child.window.hwnd != page.window.hwnd
        assert child.window.visible, "New native child was left hidden"
        assert child.parent_page is page and page.subpages == (child,)
        assert child.renderer.context is not page.renderer.context
        assert field.page is child and field.parent is child
        main_field = st.TextField("parent")
        page.add(main_field)
        pump()
        page.focus(main_field)
        child.focus(field)
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, window=child._app._window, text="X"))
        pump()
        assert field.value != "child" and main_field.value == "parent", "Input leaked between windows"
        if sys.platform == "win32":
            user = ctypes.windll.user32
            user.GetWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            user.GetWindow.restype = ctypes.c_void_p
            assert user.GetWindow(child.window.hwnd, 4) == page.window.hwnd
        for target, rgb in ((app, (25, 48, 71)), (child._app, (107, 41, 65)))*2:
            target._activate()
            target.page.draw()
            shot = target.renderer.screenshot()
            assert shot.get_at((2, 2))[:3] == rgb, (backend, shot.get_at((2, 2)), rgb)
        page.route = ""
        child.go("/settings")
        pump(lambda: len(seen) == 4)
        assert page.route == child.route == "/settings"
        assert sorted(seen) == sorted([("parent", ""), ("child", ""),
                                      ("parent", "/settings"), ("child", "/settings")])
        child.attach("right", offset=(12, 0), follow_parent=True)
        pump()
        px, py = app._window.position
        assert child._app._window.position[0] == px + round(page.window.width*app.pixel_ratio)+12
        app._window.position = (px+25, py+15)
        pump()
        assert child._app._window.position[0] == px+25+round(page.window.width*app.pixel_ratio)+12
        child.hide()
        pump()
        assert not child.window.visible
        original_draw = child.draw
        draws = []
        child.draw = lambda: draws.append(1)
        child._app.mark_dirty()
        pump()
        child.draw = original_draw
        assert not draws, "Hidden child still consumed a render frame"
        child.show()
        pump()
        grandchild = child.open_subpage(title="Nested")
        grandchild.renderer.vsync = False
        pump(lambda: grandchild.ready)
        child.close()
        pump(lambda: child.closed and child._app._disposed)
        assert grandchild.closed and grandchild._app._disposed
        assert not app._closed.is_set() and page.subpages == ()
        modal = page.open_subpage(title="Modal", modal=True)
        modal.renderer.vsync = False
        pump(lambda: modal.ready)
        if sys.platform == "win32":
            assert not user.IsWindowEnabled(ctypes.c_void_p(page.window.hwnd))
        page.focus(main_field)
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, window=app._window, text="Y"))
        pump()
        assert main_field.value == "parent", "Modal owner still accepted text input"
        modal.destroy()
        pump()
        if sys.platform == "win32":
            assert user.IsWindowEnabled(ctypes.c_void_p(page.window.hwnd))
        closing = page.open_subpage()
        pump(lambda: closing.ready)
        app.close()
        app._dispose()
        assert closing.closed and closing._app._disposed
        print(f"{backend.value}: native windows, owner, colors, routes, attachment, modal and close OK")
    finally:
        app.close()
        app._dispose()
        pygame.display.quit()
        app._executor.shutdown(wait=True)
        app._loop.call_soon_threadsafe(app._loop.stop)


if __name__ == "__main__":
    check(st.Renderer(sys.argv[1] if len(sys.argv)>1 else "software"))
