"""Native Windows behavior, handle, limits, style changes, and close events."""
import sys
import queue
import ctypes
from ctypes import wintypes
from types import SimpleNamespace
import dataclasses
import asyncio

sys.path.insert(0, ".")
import pygame
import flet
import saturn


def drain(app):
    for _ in range(1000):
        try:
            app._ui_q.get_nowait()()
        except queue.Empty:
            return
    raise AssertionError("UI queue did not settle")


def check():
    app = saturn.App(lambda page: None, saturn.Renderer.SOFTWARE)
    app.start()
    window = app.page.window
    received = []
    # Invoke handlers immediately in this focused test; App scheduling is
    # independently covered by page_checks with real async workers.
    app.call = lambda fn, *args: fn(*args)
    window.on_event = lambda event: received.append(event)
    try:
        drain(app)
        fields = {f.name for f in dataclasses.fields(flet.Window)
                  if not f.name.startswith("_")}
        for cls in flet.Window.__mro__:
            fields.update(name for name, value in vars(cls).items()
                          if not name.startswith("_") and isinstance(value, property))
        assert all(hasattr(window, name) for name in fields), fields
        user = window._native.user32
        user.IsWindow.argtypes = [wintypes.HWND]
        assert window.hwnd == app._window.handle and user.IsWindow(window.hwnd)
        assert window.page is app.page and window.parent is app.page
        window.width, window.height = 400, 300
        drain(app)
        assert app.outer_size == (400, 300), app.outer_size
        assert app.size == app.client_size_for_outer(400, 300)
        assert saturn.WindowEventType.RESIZED in [event.type for event in received]
        window.title = "Native test"
        drain(app)
        assert app.page.title == window.title == app._window.title == "Native test"
        window.min_width, window.min_height = 220, 180
        window.max_width, window.max_height = 600, 500
        drain(app)
        window.width, window.height = 100, 900
        drain(app)
        assert app.outer_size == (220, 500), app.outer_size
        for name, value in (("opacity", 1.5), ("min_width", 900),
                            ("alignment", "center"), ("brightness", "invalid")):
            try:
                setattr(window, name, value)
            except (ValueError, TypeError):
                pass
            else:
                raise AssertionError((name, "invalid value accepted"))
        window.opacity = .8
        window.resizable = False
        window.minimizable = False
        window.maximizable = False
        window.always_on_top = True
        drain(app)
        style = window._native.get_style(window.hwnd, -16)
        assert not style & (0x20000 | 0x10000 | 0x40000), hex(style)
        assert app._window.always_on_top
        assert window._native.get_style(window.hwnd, -20) & 0x80000
        window.opacity = 1
        window.always_on_top = False
        window.resizable = True
        window.minimizable = window.maximizable = True
        window.frameless = True
        drain(app)
        assert app._window.borderless
        assert not window._native.get_style(window.hwnd, -16) & 0xC00000
        assert app._window.minimum_size == app.physical_size_for_logical(
            *app.client_size_for_outer(window.min_width, window.min_height))
        window.frameless = False
        window.title_bar_hidden = True
        window.title_bar_buttons_hidden = True
        window.skip_task_bar = True
        window.ignore_mouse_events = True
        window.shadow = False
        window.brightness = "dark"
        drain(app)
        assert window._native.get_style(window.hwnd, -20) & 0x80
        assert window._native.get_style(window.hwnd, -20) & 0x20
        window.title_bar_hidden = window.title_bar_buttons_hidden = False
        window.skip_task_bar = window.ignore_mouse_events = False
        window.shadow = True
        window.left, window.top = 120, 100
        drain(app)
        assert app._window.position == (120, 100)
        window.aspect_ratio = 2
        drain(app)
        assert abs(window.width / window.height - 2) < .02
        try:
            window.min_height = 400
        except ValueError:
            pass
        else:
            raise AssertionError("incompatible aspect bounds accepted")
        assert window.min_height == 180
        window.aspect_ratio = None
        window.max_width = window.max_height = None
        drain(app)
        window.progress_bar = .5
        window.badge_label = "2"
        drain(app)
        assert window._native.taskbar and window._native.badge_icon
        window.progress_bar = window.badge_label = None
        drain(app)
        assert window._native.badge_icon is None
        window.visible = False
        drain(app)
        assert not window.visible
        window.bgcolor = "#345678"
        drain(app)
        app.page.draw()
        assert app.renderer._buf.get_at((1, 1))[:3] == (52, 86, 120)
        window.bgcolor = "#00345678"
        drain(app)
        assert window._native.get_style(window.hwnd, -20) & 0x80000
        window.bgcolor = None
        drain(app)
        window.full_screen = True
        drain(app)
        assert window.full_screen
        window.full_screen = False
        drain(app)
        assert not window.full_screen
        window.maximized = True
        drain(app)
        assert window.maximized
        window.maximized = False
        drain(app)
        assert not window.maximized
        window.minimized = True
        drain(app)
        assert window.minimized
        window.minimized = False
        drain(app)
        assert not window.minimized
        asyncio.run(window.center())
        drain(app)
        left, top, width, height = window._work_area()
        actual = app._window.position
        expected = (left + (width - round(window.width * app.pixel_ratio)) // 2,
                    top + (height - round(window.height * app.pixel_ratio)) // 2)
        assert max(abs(actual[i] - expected[i]) for i in range(2)) <= 1
        ready = asyncio.run_coroutine_threadsafe(window.wait_until_ready_to_show(), app._loop)
        import time
        limit = time.monotonic() + 2
        while not ready.done() and time.monotonic() < limit:
            drain(app)
            time.sleep(.005)
        ready.result(timeout=.1)
        window.visible = True
        drain(app)
        assert window.visible
        window.prevent_close = True
        window.close()
        drain(app)
        assert not app._closed.is_set()
        assert received[-1].type is saturn.WindowEventType.CLOSE
        assert received[-1].page is app.page
        window.prevent_close = False
        window.close()
        drain(app)
        assert app._closed.is_set()
        print("NATIVE WINDOW CHECKS PASS", len(fields), "shared property names")
    finally:
        window._dispose()
        app.renderer.close()
        app._window.destroy()
        app._loop.call_soon_threadsafe(app._loop.stop)
        app._executor.shutdown(wait=True, cancel_futures=True)
        pygame.quit()


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("Native checks require Windows")
    check()
