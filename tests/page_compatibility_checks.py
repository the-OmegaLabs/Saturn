"""Native Page behavior: events, fonts, attachment, themes and input scope."""
import asyncio
import functools
import http.server
import inspect
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.request import ProxyHandler, build_opener

sys.path.insert(0, ".")

import pygame
import saturn
from saturn import colors, text
from saturn.event import KeyboardEvent, PageResizeEvent, _invoke, fire
from saturn.page import Page
from saturn.renderer.software import SoftwareRenderer


class AppStub:
    def __init__(self, renderer=None):
        self.renderer = renderer
        self.size = (360, 200)
        self.pixel_ratio = 1.5
        self._title = "Startup title"
        self._window = SimpleNamespace(handle=0, title=self._title)
        self.pending = []
        self.dirty = threading.Event()

    def mark_dirty(self):
        self.dirty.set()

    def post(self, fn):
        self.pending.append(fn)

    def logical_point(self, x, y):
        return x / self.pixel_ratio, y / self.pixel_ratio

    def call(self, fn, *args):
        result = fn(*args)
        if inspect.isawaitable(result):
            asyncio.run(result)


class CountingControl(saturn.Control):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attach_count = 0
        self.keys = []
        self.text_inputs = []

    def _attach(self, page, parent=None):
        self.attach_count += 1
        super()._attach(page, parent)

    def _key(self, event):
        self.keys.append(event)

    def _text_input(self, value):
        self.text_inputs.append(value)


def check_events():
    from dataclasses import fields
    from flet.controls.page import KeyboardEvent as ReferenceKeyboardEvent
    from flet.controls.base_page import PageResizeEvent as ReferenceResizeEvent

    assert {"key", "shift", "ctrl", "alt", "meta"}.issubset(
        {field.name for field in fields(ReferenceKeyboardEvent)})
    assert {"width", "height"}.issubset(
        {field.name for field in fields(ReferenceResizeEvent)})
    app = AppStub()
    page = Page(app)
    assert page.page is page
    events = []
    page.on_resize = events.append
    page._notify_resize()
    assert isinstance(events[-1], PageResizeEvent)
    assert (events[-1].width, events[-1].height) == app.size
    assert events[-1].page is page
    page.on_keyboard_event = events.append
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s,
                               mod=pygame.KMOD_CTRL | pygame.KMOD_SHIFT)
    page.handle_event(event)
    keyboard = events[-1]
    assert isinstance(keyboard, KeyboardEvent)
    assert keyboard.key == "S" and keyboard.ctrl and keyboard.shift
    assert not keyboard.alt and not keyboard.meta and keyboard.page is page
    with patch("pygame.mouse.get_pos", return_value=(150, 90)), \
            patch.object(page, "_wheel") as wheel:
        page.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1))
        wheel.assert_called_once_with(-40, 100, 60)
    count = []
    async def no_args():
        count.append("async zero")
    async def with_event(event):
        count.append(("async event", event.page))
    page.on_resize = [lambda: count.append("sync zero"), no_args, with_event]
    page._notify_resize()
    assert count == ["sync zero", "async zero", ("async event", page)]
    control = CountingControl()
    control.on_click = with_event
    page.controls.append(control)
    page.update()
    fire(control, "click")
    assert count[-1] == ("async event", page)
    print("Typed Page events and sync/async callback/list dispatch: pass")


def check_application_async_dispatch():
    from saturn.app import App
    app = object.__new__(App)
    app._executor = ThreadPoolExecutor(max_workers=3)
    app._loop = asyncio.new_event_loop()
    worker = threading.Thread(target=app._loop.run_forever)
    worker.start()
    done = [threading.Event() for _ in range(3)]
    received = []
    payload = object()
    async def zero_args():
        await asyncio.sleep(0)
        received.append("zero")
        done[0].set()
    async def one_arg(event):
        await asyncio.sleep(0)
        received.append(event)
        done[1].set()
    def returns_coroutine(event):
        async def inner():
            await asyncio.sleep(0)
            received.append(("returned", event))
            done[2].set()
        return inner()
    try:
        app.call(_invoke, zero_args, payload)
        app.call(_invoke, one_arg, payload)
        app.call(_invoke, returns_coroutine, payload)
        assert all(event.wait(3) for event in done)
        assert "zero" in received and payload in received
        assert ("returned", payload) in received
    finally:
        app._executor.shutdown(wait=True)
        app._loop.call_soon_threadsafe(app._loop.stop)
        worker.join(3)
        app._loop.close()
    print("Actual App.call awaits async handlers and returned coroutines: pass")


def check_attachment_and_disabled():
    app = AppStub()
    page = Page(app)
    child = CountingControl()
    column = saturn.Column(child)
    overlay = CountingControl()
    page.controls = [column]
    page.overlay.append(overlay)
    service = saturn.FilePicker()
    page.services.append(service)
    page.update()
    assert child.page is page and child.parent is column
    assert overlay.page is page and service.page is page
    page.update()
    assert child.attach_count == overlay.attach_count == 1
    page.focus(child)
    page.controls.clear()
    page.overlay.clear()
    page.services.clear()
    page.update()
    assert child.page is column.page is overlay.page is service.page is None
    assert page._focused is None
    page.controls.append(child)
    page.overlay.append(overlay)
    page.update()
    child._rect = overlay._rect = (0, 0, 100, 100)
    child._focusable = overlay._focusable = True
    page.focus(child)
    page.disabled = True
    page.update()
    assert page._focused is None
    page.pointer_down(20, 20)
    page.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0))
    page.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="a"))
    assert page._pressed is None and not child.keys and not child.text_inputs
    assert page._hit_test(20, 20) is None
    page.disabled = False
    page.update()
    page.focus(child)
    page.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="a"))
    assert child.text_inputs == ["a"]
    child.disabled = True
    page.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="b"))
    assert child.text_inputs == ["a"]
    assert page.title == "Startup title"
    page.window.title = "Window title"
    assert page.title == "Window title"
    assert page.media.device_pixel_ratio == 1.5
    print("List mutation, service ownership, detach and disabled input: pass")


def check_themes():
    page = Page(AppStub())
    page.theme = saturn.Theme(font_family="Light family")
    page.dark_theme = saturn.Theme(font_family="Dark family")
    page.theme_mode = saturn.ThemeMode.LIGHT
    assert text.default_family == "Light family" and not colors.theme_dark
    page.theme_mode = saturn.ThemeMode.DARK
    assert text.default_family == "Dark family" and colors.theme_dark
    page.dark_theme.font_family = "Mutated dark family"
    page.update()
    assert text.default_family == "Mutated dark family"
    page.dark_theme = None
    assert text.default_family == "Light family"
    changed = []
    page.on_platform_brightness_change = changed.append
    page._platform_brightness = "light"
    page.theme_mode = saturn.ThemeMode.SYSTEM
    with patch.object(colors, "system_prefers_dark", return_value=True):
        assert page._refresh_platform_brightness()
        assert not page._refresh_platform_brightness()
    assert colors.theme_dark and changed[-1].brightness == "dark"
    assert changed[-1].page is page
    page.theme = None
    print("Effective light/dark/system themes and brightness events: pass")


def check_fonts_and_padding():
    window = pygame.Window("Page fonts check", size=(360, 200), hidden=True)
    renderer = SoftwareRenderer(window)
    app = AppStub(renderer)
    app.pixel_ratio = 1
    page = Page(app)
    page.theme_mode = saturn.ThemeMode.LIGHT
    widget = saturn.Text("iii WWW 012345", font_family="Custom", size=24)
    page.controls = [widget]
    page.padding = saturn.Padding.only(left=24, top=18, right=12, bottom=10)
    page.update()
    source = Path(pygame.__file__).parent / pygame.font.get_default_font()
    try:
        page.fonts["Custom"] = str(source)
        revision = text.font_revision
        page.update()
        assert text.font_revision > revision
        page.draw()
        first_width = widget._rect[2]
        assert widget._rect[:2] == (24, 18)
        first_frame = renderer.screenshot()
        assert text.registered_fonts["Custom"] == str(source)
        page.fonts["Custom"] = str(text.INTER)
        page.update()
        page.draw()
        assert widget._rect[2] != first_width
        second_frame = renderer.screenshot()
        assert pygame.image.tobytes(first_frame, "RGBA") != pygame.image.tobytes(second_frame, "RGBA")
        assert text._glyph_links.cache_info().currsize
        del page.fonts["Custom"]
        page.update()
        assert "Custom" not in text.registered_fonts
        page.padding = None
        page.draw()
        assert widget._rect[:2] == (0, 0)
        print("Font alias mutation invalidates layout and pixels; per-edge padding: pass")
    finally:
        renderer.close()
        window.destroy()


def check_http_font():
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        requests = 0

        def do_GET(self):
            type(self).requests += 1
            super().do_GET()

        def log_message(self, *_):
            pass
    Path(".build-probe").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".build-probe") as folder:
        directory = Path(folder)
        (directory / "download").write_bytes(text.INTER_BOLD.read_bytes())
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(QuietHandler, directory=folder))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        page = Page(AppStub())
        url = f"http://127.0.0.1:{server.server_port}/download?font=custom"
        ready = threading.Event()
        def font_ready():
            Page._font_ready(page)
            ready.set()
        try:
            with patch.object(text, "_font_cache_directory", return_value=directory / "cache"), \
                    patch.object(text, "urlopen", build_opener(ProxyHandler({})).open), \
                    patch.object(page, "_font_ready", side_effect=font_ready):
                page.fonts = {"Remote": url}
                assert ready.wait(5), "font-ready notification was not delivered"
                cached = text.registered_fonts.get("Remote")
                assert cached and Path(cached).is_file(), text.registered_fonts
                assert Path(cached).read_bytes()[:4] not in (b"wOF2", b"wOFF")
                assert text.line_width("Downloaded font", 20, family="Remote") > 0
                page.fonts.clear()
                page.update()
                assert "Remote" not in text.registered_fonts
                page.fonts = {"Remote": url}
                assert text.registered_fonts["Remote"] == cached
                assert QuietHandler.requests == 1
                page.fonts.clear()
                page.update()
                print("HTTP font download, validated cache, ready redraw and alias removal: pass")
        finally:
            server.shutdown()
            server.server_close()


def check_collection_and_web_formats():
    from fontTools.ttLib import TTCollection, TTFont
    Path(".build-probe").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".build-probe") as folder:
        root = Path(folder)
        font = TTFont(text.INTER)
        try:
            font.flavor = "woff"
            font.save(root / "custom.woff")
            font.flavor = None
            collection = TTCollection()
            collection.fonts = [font]
            collection.save(root / "custom.ttc")
            page = Page(AppStub())
            for path in (root / "custom.woff", root / "custom.ttc"):
                page.fonts = {"Format": str(path)}
                assert text._primary_link(str(path), 400, False)[0] == "file"
                assert text.line_width("Font format", 18, family="Format") > 0
                surface = text.render_line("Font format", 18, family="Format")
                assert surface.get_width() > 0 and surface.get_height() > 0
            page.fonts.clear()
            page.update()
        finally:
            font.close()
    print("TTC and WOFF fonts work through aliases and direct font paths: pass")


if __name__ == "__main__":
    pygame.init()
    try:
        check_events()
        check_application_async_dispatch()
        check_attachment_and_disabled()
        check_themes()
        check_fonts_and_padding()
        check_collection_and_web_formats()
        check_http_font()
    finally:
        text.register_fonts({})
        text.set_default_family(None)
        pygame.quit()
    print("PAGE COMPATIBILITY CHECKS PASS")
