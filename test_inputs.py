"""Inputs self-check (milestone 8): TextField editing, toggles, radio, slider,
dropdown menu. Headless + assert-based.
"""
import sys
import time

sys.path.insert(0, ".")

import pygame

import saturn as ft
from saturn.widgets.containers import Row
from saturn.widgets.inputs import (Checkbox, Dropdown, DropdownOption, Radio,
                                   RadioGroup, Slider, Switch, TextField)


class Rec:
    def __init__(self):
        self.items = []
        self.ev = __import__("threading").Event()

    def __call__(self, e=None):
        self.items.append(e.data if hasattr(e, "data") else e)
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


class FakeKey:
    def __init__(self, key):
        self.key = key


class FakeText:
    def __init__(self, text):
        self.text = text


def check_textfield():
    app, page = make_page()
    changed, submitted = Rec(), Rec()
    tf = TextField("abc", on_change=changed, on_submit=submitted)
    page.add(tf)
    page.draw()
    page.pointer_down(*center(tf))          # focuses + sets caret
    assert page._focused is tf
    page._focused._text_input("d")          # abc -> abcd? caret set by click x
    assert tf.value.startswith("abc"), tf.value
    tf._caret = len(tf.value)
    tf._text_input("X")
    assert tf.value.endswith("X")
    assert changed.wait(), "on_change never fired"
    page._focused._key(FakeKey(__import__("pygame").K_BACKSPACE))
    assert not tf.value.endswith("X")
    tf._key(FakeKey(__import__("pygame").K_RETURN))
    assert submitted.wait()
    page.focus(None)
    assert not tf._focused

    outline = ft.OutlineInputBorder(
        border_radius=12,
        side=ft.BorderSide(color=ft.Colors.RED_900),
    )
    modern = TextField(border=outline)
    page.add(modern)
    page.draw()
    assert modern.border is outline
    assert modern.border.border_radius == 12
    assert modern.border.side.color == ft.Colors.RED_900
    print("textfield ok")


def check_password_and_hint():
    app, page = make_page()
    tf = TextField("secret", password=True, can_reveal_password=True,
                   hint_text="enter pwd")
    page.add(tf)
    page.draw()
    assert tf._visible_text() == "••••••"
    x, y, w, h = tf._rect
    page.pointer_down(x + w - 12, y + h / 2)
    page.pointer_up(x + w - 12, y + h / 2)
    assert tf._visible_text() == "secret"
    page.pointer_down(x + w - 12, y + h / 2)
    page.pointer_up(x + w - 12, y + h / 2)
    assert tf._visible_text() == "••••••"
    print("password ok")


def check_textfield_animations():
    app, page = make_page()
    tf = TextField(label="Name", hint_text="Enter a name")
    page.add(tf)
    page.draw()
    assert tf._label_progress == 0.0
    assert tf._focus_progress == 0.0

    page.focus(tf)
    started = tf._animations["_focus_progress"].started
    assert tf._cursor_visible
    assert tf._tick_animations(started + 0.075)
    assert 0.0 < tf._focus_progress < 1.0
    assert 0.0 < tf._label_progress < 1.0
    tf._tick_animations(started + 0.16)
    assert tf._focus_progress == 1.0
    assert tf._label_progress == 1.0

    # Intermediate label frames must reuse fixed rasters instead of creating
    # a new font surface/GL texture for every interpolated size.
    tf._focus_progress = tf._label_progress = 0.8
    tf._draw(app.renderer, 0, 0)
    cached_lines = len(tf._line_cache)
    for progress in (0.1, 0.25, 0.5, 0.75, 0.9):
        tf._focus_progress = tf._label_progress = progress
        tf._draw(app.renderer, 0, 0)
        assert len(tf._line_cache) == cached_lines
    tf._focus_progress = tf._label_progress = 1.0

    tf._set_hover(True)
    hover_started = tf._animations["_hover_progress"].started
    tf._tick_animations(hover_started + 0.075)
    assert 0.0 < tf._hover_progress < 1.0
    tf._tick_animations(hover_started + 0.16)
    assert tf._hover_progress == 1.0

    page.focus(None)
    blur_started = tf._animations["_label_progress"].started
    tf._tick_animations(blur_started + 0.16)
    assert tf._focus_progress == 0.0
    assert tf._label_progress == 0.0
    assert not tf._cursor_visible
    print("textfield animations ok")


def check_cjk_ime():
    app, page = make_page()
    changed = Rec()
    tf = TextField("前", on_change=changed)
    page.add(tf)
    page.draw()
    page.pointer_down(*center(tf))
    tf._caret = len(tf.value)

    page.handle_event(pygame.event.Event(
        pygame.TEXTEDITING, text="中文", start=1, length=1))
    assert tf.value == "前", "preedit text must not mutate the committed value"
    assert tf._composition == "中文"
    assert tf._composition_start == 1 and tf._composition_length == 1
    assert changed.items == [], "preedit must not fire on_change"
    assert tf._last_ime_rect is not None
    assert tf._last_ime_rect.y > round(tf._rect[1])
    assert tf._last_ime_rect.bottom == round(tf._rect[1] + tf._rect[3] - 4)

    page.handle_event(pygame.event.Event(pygame.KEYDOWN,
                                         key=pygame.K_BACKSPACE))
    assert tf.value == "前", "IME must own editing keys during composition"

    page.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="中文"))
    assert tf.value == "前中文"
    assert tf._composition == ""
    assert changed.wait() and changed.items == ["前中文"]

    page.handle_event(pygame.event.Event(
        pygame.TEXTEDITING, text="输入", start=2, length=0))
    page.focus(None)
    assert tf._composition == "", "blur must cancel unfinished preedit text"
    print("CJK IME ok")


def check_checkbox_switch():
    app, page = make_page()
    cb, sw = Rec(), Rec()
    c = Checkbox("cbox", on_change=cb)
    s = Switch(on_change=sw)
    page.add(c, s)
    page.draw()
    page.pointer_down(*center(c))
    page.pointer_up(*center(c))
    assert c.value is True and cb.wait() and cb.items[-1] == "true"
    page.pointer_down(*center(s))
    page.pointer_up(*center(s))
    assert s.value is True and sw.wait()
    print("checkbox/switch ok")


def check_radio_group():
    app, page = make_page()
    grp = Rec()
    g = RadioGroup(value="a", on_change=grp,
                   content=Row(Radio("a", label="A"), Radio("b", label="B"),
                               spacing=8))
    page.add(g)
    page.draw()
    rb = g.content.controls[1]
    page.pointer_down(*center(rb))
    page.pointer_up(*center(rb))
    assert g.value == "b" and grp.wait() and grp.items[-1] == "b"
    print("radio ok")


def check_slider():
    app, page = make_page()
    changed, ended = Rec(), Rec()
    s = Slider(min=0, max=100, divisions=10, on_change=changed, on_change_end=ended)
    page.add(s)
    page.draw()
    x0 = s._rect[0]
    page.pointer_down(x0, s._rect[1] + 20)
    assert s._animations["_thumb_press_progress"].duration == 0.1
    page.pointer_move(x0 + s._rect[2] * 0.5, 0)
    page.pointer_up(x0 + s._rect[2] * 0.5, 0)
    assert s._animations["_thumb_press_progress"].duration == 0.1
    assert s._animations["_thumb_press_progress"].end_value == 0.0
    assert s.value == 50, s.value
    assert changed.wait() and ended.wait()
    print("slider ok")


def check_dropdown():
    app, page = make_page()
    picked = Rec()
    dd = Dropdown(value="a",
                  options=[DropdownOption("a", text="Alpha"),
                           DropdownOption("b", text="Beta")],
                  on_select=picked)
    page.add(dd)
    page.draw()
    page.pointer_down(*center(dd))
    page.pointer_up(*center(dd))
    assert dd.open and len(page.overlay) == 1
    assert dd._animations["_menu_progress"].duration == 0.3
    opened = dd._animations["_menu_progress"].started
    dd._tick_animations(opened + 0.31)
    item_b = dd._menu[1]
    page.pointer_down(*center(item_b))
    page.pointer_up(*center(item_b))
    assert picked.wait() and picked.items[-1] == "b" and dd.value == "b"
    assert not dd.open and dd._menu_closing
    assert dd._animations["_menu_progress"].duration == 0.15
    dd._tick_animations(dd._menu_close_deadline + 0.01)
    assert page.overlay == []
    print("dropdown ok")


if __name__ == "__main__":
    check_textfield()
    check_password_and_hint()
    check_textfield_animations()
    check_cjk_ime()
    check_checkbox_switch()
    check_radio_group()
    check_slider()
    check_dropdown()
    print("ALL INPUT TESTS PASS")
