"""Window/Page size semantics self-check."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

import pygame

from saturn.app import App, Render, _system_refresh_rate
from saturn.page import Page, Window
from saturn.types import ThemeMode


def check_outer_to_client_conversion():
    app = App(lambda page: None, Render.SOFTWARE, 800, 600, "test")
    app._frame_size = (16, 39)
    assert app.outer_size == (800, 600)
    assert app.client_size_for_outer(350, 480) == (334, 441)


def check_live_resize_frame():
    class Renderer:
        def __init__(self):
            self.resizes = []
            self.flips = 0

        def on_resize(self, width, height):
            self.resizes.append((width, height))

        def flip(self):
            self.flips += 1

    class Page:
        def __init__(self):
            self.draws = 0
            self.on_resize = [object()]
            self.dispatches = 0

        def draw(self):
            self.draws += 1

        def _dispatch(self, handlers):
            assert handlers is self.on_resize
            self.dispatches += 1

    app = App(lambda page: None, Render.SOFTWARE, 800, 600, "test")
    app._frame_size = (16, 39)
    app.renderer = Renderer()
    app.page = Page()
    app._resize_frame(500, 320, present=True, dispatch=True)
    assert app.size == (500, 320)
    assert app.outer_size == (516, 359)
    assert app.renderer.resizes == [(500, 320)]
    assert app.page.draws == 1 and app.renderer.flips == 1
    assert app.page.dispatches == 1
    app._resize_frame(500, 320, present=False, dispatch=True)
    assert app.page.dispatches == 1, "same SDL resize must not dispatch twice"


def check_refresh_rate_detection():
    current = pygame.display.get_current_refresh_rate
    desktops = pygame.display.get_desktop_refresh_rates
    try:
        pygame.display.get_current_refresh_rate = lambda: 165
        pygame.display.get_desktop_refresh_rates = lambda: [144]
        assert _system_refresh_rate() == 165
        pygame.display.get_current_refresh_rate = lambda: 0
        assert _system_refresh_rate() == 144
        pygame.display.get_desktop_refresh_rates = lambda: [0]
        assert _system_refresh_rate() == 60
    finally:
        pygame.display.get_current_refresh_rate = current
        pygame.display.get_desktop_refresh_rates = desktops


def check_default_window_icon_contract():
    app = App(lambda page: None, Render.SOFTWARE, 800, 600, "test")
    window = Window(app)
    assert window.icon is None
    app._window_icon = "custom.ico"
    assert window.icon == "custom.ico"


def check_title_bar_tracks_page_theme():
    app = App(lambda page: None, Render.SOFTWARE, 800, 600, "test")
    app._window = SimpleNamespace(handle=42)
    app.post = lambda callback: callback()
    with patch("saturn.page._set_windows_dark_title_bar") as set_dark:
        page = Page(app)
        set_dark.reset_mock()
        page.theme_mode = ThemeMode.DARK
        set_dark.assert_called_once_with(42, True)
        set_dark.reset_mock()
        page.theme_mode = ThemeMode.LIGHT
        set_dark.assert_called_once_with(42, False)


def check_windows_dark_title_bar_dwm_contract():
    set_attribute = MagicMock(side_effect=[-1, 0])
    set_window_pos = MagicMock()
    libraries = SimpleNamespace(
        dwmapi=SimpleNamespace(DwmSetWindowAttribute=set_attribute),
        user32=SimpleNamespace(SetWindowPos=set_window_pos),
    )
    with patch("saturn.page.sys.platform", "win32"), \
            patch("saturn.page.ctypes.windll", libraries):
        from saturn.page import _set_windows_dark_title_bar
        assert _set_windows_dark_title_bar(42, True)
    assert set_attribute.call_count == 2, "must fall back from DWM 20 to 19"
    set_window_pos.assert_called_once()


def check_native_ime_ui_enabled_before_pygame_init():
    app = App(lambda page: None, Render.SOFTWARE, 800, 600, "test")
    calls = []
    previous = os.environ.pop("SDL_IME_SHOW_UI", None)
    try:
        with patch("pygame.init", side_effect=lambda: calls.append(
                os.environ.get("SDL_IME_SHOW_UI"))), \
                patch("pygame.Window", side_effect=RuntimeError("stop")):
            try:
                app.start()
            except RuntimeError as error:
                assert str(error) == "stop"
        assert calls == ["1"]
    finally:
        if previous is None:
            os.environ.pop("SDL_IME_SHOW_UI", None)
        else:
            os.environ["SDL_IME_SHOW_UI"] = previous


def check_ime_input_rect_forwarded_to_sdl():
    app = App(lambda page: None, Render.SOFTWARE, 800, 600, "test")
    rect = pygame.Rect(64, 80, 1, 48)
    with patch("pygame.key.set_text_input_rect") as sdl_position:
        app.set_text_input_rect(rect)
    sdl_position.assert_called_once_with(rect)


if __name__ == "__main__":
    check_outer_to_client_conversion()
    check_live_resize_frame()
    check_refresh_rate_detection()
    check_default_window_icon_contract()
    check_title_bar_tracks_page_theme()
    check_windows_dark_title_bar_dwm_contract()
    check_native_ime_ui_enabled_before_pygame_init()
    check_ime_input_rect_forwarded_to_sdl()
    print("ALL WINDOW TESTS PASS")
