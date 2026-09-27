"""Desktop parameter behavior checked against installed Flet constructors."""
import inspect
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, ".")

import flet
import pygame
import saturn as st
from saturn.page import Page
from saturn.renderer.software import SoftwareRenderer


class App:
    def __init__(self, renderer):
        self.renderer = renderer
        self.size = (520, 480)
        self.pixel_ratio = 1.0
        self._title = "Inputs"
        self._window = SimpleNamespace(handle=0, title="Inputs")
        self.pending = []

    def mark_dirty(self):
        pass

    def post(self, fn):
        self.pending.append(fn)

    def call(self, fn, *args):
        return fn(*args)

    def set_text_input_rect(self, rect):
        self.ime_rect = rect


def key(control, code, mod=0):
    control._key(pygame.event.Event(pygame.KEYDOWN, key=code, mod=mod))


def draw(control, renderer, rect=(20, 20, 360, 80)):
    renderer.clear((0, 0, 0, 255))
    control._place(*rect, renderer.scale)
    control._draw_all(renderer)
    return renderer._buf.copy()


def check_field(page, renderer):
    changes, selections = [], []
    field = st.TextField("12", input_filter=st.InputFilter(regex_string="[0-9]"),
                         on_change=lambda e: changes.append(e.control.value),
                         on_selection_change=lambda e: selections.append(e))
    field._attach(page)
    field._text_input("a3b4")
    assert field.value == "1234" and changes[-1] == "1234"
    field.selection = st.TextSelection(1, 3)
    field._text_input("x8")
    assert field.value == "184" and field.selection.is_collapsed
    assert selections[-2].selection.start == 1 and selections[-2].text == "23"
    assert selections[-2].page is page
    field.read_only = True
    field._text_input("5")
    key(field, pygame.K_BACKSPACE)
    assert field.value == "184"
    field.enable_interactive_selection = False
    key(field, pygame.K_a, pygame.KMOD_CTRL)
    assert field.selection.is_collapsed
    with patch("saturn.widgets.inputs._clipboard_copy") as copy:
        field.selection = st.TextSelection(0, 2)
        key(field, pygame.K_c, pygame.KMOD_CTRL)
        copy.assert_called_once_with("18")

    capital = st.TextField(capitalization=st.TextCapitalization.WORDS)
    capital._text_input("hello world")
    assert capital.value == "Hello World"
    capital.capitalization = st.TextCapitalization.CHARACTERS
    capital._text_input(" xyz")
    assert capital.value.endswith(" XYZ")

    field = st.TextField("ABC", prefix="$", suffix="USD", helper="Helpful",
                         counter="3 / 10", content_padding=st.Padding.all(12),
                         filled=True, fill_color="#123456", cursor_color="#ff0000",
                         cursor_width=5, cursor_height=28, cursor_radius=2,
                         text_style=st.TextStyle(size=18, weight=st.FontWeight.BOLD),
                         selection_color="#00ff00")
    field._attach(page)
    field._focused = field._cursor_visible = True
    image = draw(field, renderer)
    assert image.get_at((round(30 * renderer.scale), round(30 * renderer.scale)))[:3] == (18, 52, 86)
    assert field._field_height() == 58
    left, width = field._text_viewport()
    assert left > 32 and width < 336
    reds = [(x, y) for x in range(40, 340) for y in range(25, 72)
            if image.get_at((x * 2, y * 2))[:3] == (255, 0, 0)]
    assert reds and max(x for x, _ in reds) - min(x for x, _ in reds) >= 3
    field.error = "Invalid"
    draw(field, renderer)
    assert field._support_height() == 22

    multi = st.TextField("first\nsecond\nthird", multiline=True, min_lines=2, max_lines=4,
                         content_padding=8, ignore_up_down_keys=False)
    multi._attach(page)
    multi._place(20, 100, 260, 120, renderer.scale)
    multi._focused = True
    multi._caret = 8
    key(multi, pygame.K_DOWN)
    assert multi._caret == 15
    key(multi, pygame.K_UP)
    assert multi._caret == 8
    lines = multi._display_lines(multi.value, 244, renderer.scale)
    assert [line for _, line in lines] == ["first", "second", "third"]
    draw(multi, renderer, (20, 100, 260, 120))
    assert multi._index_at(29, 110) == 0
    assert multi._index_at(29, 110 + st.text.line_height(16, scale=renderer.scale)) == 6
    multi._update_ime_rect()
    assert page._app.ime_rect.y >= 110

    for options in ({"autofill_hints": ["email"]}, {"keyboard_type": st.KeyboardType.NUMBER},
                    {"autocorrect": False}):
        try:
            st.TextField(**options)
        except NotImplementedError:
            pass
        else:
            raise AssertionError(options)
    borderless = st.TextField(border=st.NoInputBorder(), show_cursor=False)
    no_pixels = draw(borderless, renderer, (20, 20, 200, 56))
    underline = st.TextField(border=st.UnderlineInputBorder(side=st.BorderSide(3, "#ffffff")), show_cursor=False)
    under_pixels = draw(underline, renderer, (20, 20, 200, 56))
    assert no_pixels.get_at((60, 148))[:3] == (0, 0, 0)
    assert under_pixels.get_at((60, 148))[:3] == (255, 255, 255)
    assert under_pixels.get_at((60, 42))[:3] == (0, 0, 0)
    checkbox_none = st.Checkbox(value=None, tristate=True)
    checkbox_none._prepare_animations(0)
    assert checkbox_none._value_progress == 1
    try:
        st.Text("Unsupported", style=st.TextStyle(letter_spacing=2))
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Unsupported text shaping must not be accepted silently")
    field._stop_cursor_blink()
    multi._stop_cursor_blink()
    print("FIELD FILTER, SELECTION, CARET STYLE, AFFIXES, SUPPORT TEXT, MULTILINE PASS")


def check_text(page, renderer):
    events = []
    text = st.Text("Long text that must overflow", style=st.TextStyle(size=18, color="#ffffff"),
                   overflow=st.TextOverflow.ELLIPSIS, no_wrap=True, selectable=True,
                   on_selection_change=lambda e: events.append(e),
                   bgcolor="#112233", on_tap=lambda e: events.append(e.name))
    text._attach(page)
    draw(text, renderer, (20, 20, 100, 40))
    assert text._ellipsized(text.value, 100, renderer.scale).endswith("…")
    text._pointer_down(25, 25, clicks=3)
    assert text.selection.start == 0 and text.selection.end == len(text.value)
    assert events[-1].text == text.value and events[-1].page is page
    key(text, pygame.K_HOME)
    key(text, pygame.K_RIGHT, pygame.KMOD_SHIFT)
    assert text.selection.start == 0 and text.selection.end == 1
    with patch("saturn.widgets.inputs._clipboard_copy") as copy:
        key(text, pygame.K_c, pygame.KMOD_CTRL)
        copy.assert_called_once_with("L")
    plain = st.Text("Ordinary label")
    assert not plain._handles_tap
    plain.selectable = True
    assert plain._focusable
    fallback = st.Text("Hello 中文", font_family="Consolas", font_family_fallback=["Arial"])
    draw(fallback, renderer, (20, 60, 250, 60))
    assert fallback._family() == ("Consolas", "Arial")
    print("TEXT STYLE, ELLIPSIS, REAL SELECTION, CALLBACKS, FALLBACK FONT PASS")


def check_toggles(page, renderer):
    checkbox = st.Checkbox("Three", tristate=True, value=False,
                           label_style=st.TextStyle(size=19), fill_color="#ff0000",
                           check_color="#ffffff", border_side=st.BorderSide(3, "#00ff00"))
    checkbox._attach(page)
    checkbox._toggle(); assert checkbox.value is True
    checkbox._toggle(); assert checkbox.value is None
    checkbox._toggle(); assert checkbox.value is False
    key(checkbox, pygame.K_SPACE); assert checkbox.value is True
    draw(checkbox, renderer, (20, 20, 220, 40))
    custom_label = st.Container(st.Text("Custom label"), bgcolor="#334455", padding=2)
    draw(st.Checkbox(custom_label), renderer, (20, 70, 250, 40))
    switch = st.Switch("Switch", value=True, active_track_color="#ff0000",
                       thumb_color="#00ff00", thumb_icon=st.Icons.CHECK,
                       inactive_track_color="#0000ff", track_outline_width=3)
    draw(switch, renderer, (20, 120, 240, 40))
    key(switch, pygame.K_SPACE)
    assert switch.value is False
    group = st.RadioGroup(st.Row(st.Radio("a", label="A", toggleable=True),
                                st.Radio("b", label="B", label_position=st.LabelPosition.LEFT)), value="a")
    group._attach(page)
    a, b = group.content.controls
    a._pick(); assert group.value is None
    key(a, pygame.K_RIGHT); assert group.value == "b"
    draw(group, renderer, (20, 180, 260, 40))
    print("CHECKBOX TRISTATE, SWITCH STYLES, RADIO TOGGLE AND KEYBOARD PASS")


def check_slider_dropdown(page, renderer):
    slider = st.Slider(value=.2, divisions=5, padding=20,
                       secondary_track_value=.8, secondary_active_color="#ff0000",
                       interaction=st.SliderInteraction.SLIDE_THUMB)
    slider._place(20, 20, 300, 48, renderer.scale)
    slider._drag_start(315, 30)
    assert slider.value == .2
    slider._drag_end()
    key(slider, pygame.K_RIGHT); assert abs(slider.value - .4) < 1e-6
    key(slider, pygame.K_END); assert slider.value == 1
    draw(slider, renderer, (20, 20, 300, 48))
    selected, changed = [], []
    options = [st.DropdownOption(str(i), text=f"Item {i}", leading_icon=st.Icons.SETTINGS,
                                 content=st.Text(f"Item {i}"), disabled=i == 1) for i in range(12)]
    dropdown = st.Dropdown(options=options, editable=True, enable_filter=True,
                           menu_width=300, menu_height=96, helper_text="Choose",
                           on_select=lambda e: selected.append(e.data),
                           on_text_change=lambda e: changed.append(e.data))
    page.controls = [dropdown]
    page.update()
    dropdown._place(20, 100, 260, 80, renderer.scale)
    dropdown._toggle_menu()
    assert dropdown._menu_surface._rect[2:] == (300, 96)
    dropdown._menu_surface._wheel(120)
    assert dropdown._menu_surface._scroll_offset == 120
    dropdown._text_input("11")
    assert changed == ["11"]
    assert [option.key for option in dropdown._filtered_options] == ["11"]
    key(dropdown, pygame.K_RETURN)
    assert dropdown.value == "11" and selected == ["11"]
    dropdown._pick_option(options[1])
    assert dropdown.value == "11"
    draw(dropdown, renderer, (20, 100, 260, 80))
    dropdown._field._stop_cursor_blink()
    searchable = st.Dropdown(options=[st.DropdownOption("a", text="Alpha"), st.DropdownOption("b", text="Beta")])
    searchable._text_input("b")
    assert searchable.value == "b"
    print("SLIDER INTERACTION/SECONDARY TRACK, EDITABLE FILTER/SEARCH/SCROLLING DROPDOWN PASS")


def check_transformed_ime(page, renderer):
    field = st.TextField("ab", offset=(.1, 0), cursor_height=24)
    listing = st.ListView(field, height=100)
    listing._attach(page)
    listing._place(0, 0, 300, 100, renderer.scale)
    field._place(20, 100, 200, 56, renderer.scale)
    listing._offset = 40
    field._focused = field._cursor_visible = True
    field._draw_all(renderer, 0, -40)
    field._update_ime_rect()
    # The ancestor scroll must be applied once; the field offset adds 20 pixels.
    assert page._app.ime_rect.y == 76, page._app.ime_rect
    family, size, _ = field._style()
    expected_x = round(20 + 16 + 20 + field._line_width("ab", size, scale=renderer.scale, family=family) - 6)
    assert page._app.ime_rect.x == expected_x
    sx, sy = field._screen_point(36, 116)
    lx, ly = field._event_point(sx, sy)
    assert abs(lx - 36) < .001 and abs(ly - 116) < .001
    field._stop_cursor_blink()
    print("TRANSFORMED/SCROLLED INPUT POINTER AND IME COORDINATES PASS")


def check_transformed_dropdown(page, renderer):
    dropdown = st.Dropdown(value="a", options=[st.DropdownOption("a", text="Alpha"),
                                             st.DropdownOption("b", text="Beta")],
                           rotate=.2, scale=1.3, menu_height=96)
    listing = st.ListView(dropdown, height=240)
    page.controls = [listing]
    page.update()
    listing._place(0, 0, 420, 240, renderer.scale)
    dropdown._place(110, 140, 160, 56, renderer.scale)
    listing._offset = 40
    dropdown._toggle_menu()
    dropdown._animate_internal("_menu_progress", 1, 0)
    dropdown._animate_internal("_menu_timeline", 1, 0)
    dropdown._position_menu()
    surface = dropdown._menu_surface
    assert surface.parent is None
    corners = [dropdown._screen_point(x, y) for x, y in
               ((110, 140), (270, 140), (110, 196), (270, 196))]
    left = min(x for x, y in corners)
    right = max(x for x, y in corners)
    bottom = max(y for x, y in corners)
    assert abs(surface._rect[0] - left) < .001
    assert abs(surface._rect[1] - bottom - 4) < .001
    assert abs(surface._rect[2] - (right - left)) < .001
    renderer.clear((0, 0, 0, 255))
    surface._draw_all(renderer)
    x, y, width, height = surface._rect
    pixel = renderer._buf.get_at((round((x + 8) * renderer.scale), round((y + 12) * renderer.scale)))
    assert pixel[:3] != (0, 0, 0), pixel
    # The second row lives in window coordinates, not in the rotated/scrolled field tree.
    px, py = x + 20, y + 72
    row = surface.items[1]
    assert surface._hit_test(px, py) is row
    ex, ey = row._event_point(px, py)
    assert abs(ex - px) < .001 and abs(ey - py) < .001
    page.pointer_down(px, py)
    page.pointer_up(px, py)
    assert dropdown.value == "b"
    dropdown._finish_menu_close()
    dropdown._toggle_menu()
    dropdown._animate_internal("_menu_progress", 1, 0)
    dropdown._animate_internal("_menu_timeline", 1, 0)
    before = dropdown._menu_surface._rect
    dropdown.scale = 1.6
    dropdown._draw(renderer, 110, 100)
    after = dropdown._menu_surface._rect
    assert after[2] > before[2]
    dropdown.disabled = True
    assert dropdown._menu_surface._hit_test(after[0] + 20, after[1] + 20) is None
    dropdown._finish_menu_close()
    print("TRANSFORMED/SCROLLED DROPDOWN WINDOW POPUP PIXELS AND POINTER PASS")


def check_dropdown_floating_label(page, renderer):
    dropdown = st.Dropdown(value="a", label="Palette", color="#00ff00",
                           label_style=st.TextStyle(color="#ff0000"),
                           options=[st.DropdownOption("a", text="Aurora")])
    page.controls = [dropdown]
    page.update()
    image = draw(dropdown, renderer, (20, 30, 260, 56))
    assert dropdown._field._label_progress == 1
    assert dropdown._field._last_value == "Aurora"
    label_y, value_y = [], []
    for x in range(32 * 2, 140 * 2):
        for y in range(16 * 2, 82 * 2):
            red, green, blue, alpha = image.get_at((x, y))
            if red > 180 and green < 30 and blue < 30:
                label_y.append(y)
            if green > 180 and red < 30 and blue < 30:
                value_y.append(y)
    assert label_y and value_y
    assert max(label_y) < min(value_y), (min(label_y), max(label_y), min(value_y), max(value_y))
    # Programmatic value changes also refresh the embedded field's label target.
    dropdown.value = None
    dropdown._sync_field()
    assert dropdown._field._last_value == ""
    assert dropdown._field._animation_targets["_label_progress"] == 0
    dropdown.value = "a"
    dropdown._sync_field()
    assert dropdown._field._last_value == "Aurora"
    assert dropdown._field._animation_targets["_label_progress"] == 1
    print("DROPDOWN INITIAL FLOATING LABEL PIXELS AND VALUE CHANGE STATE PASS")


def check_reference_parameters():
    cases = [("Text", dict(value="Hello", style=st.TextStyle(size=18), overflow=st.TextOverflow.ELLIPSIS)),
             ("TextField", dict(value="12", min_lines=1, cursor_width=3, error="Invalid", prefix="$")),
             ("Checkbox", dict(label="Check", value=None, tristate=True)),
             ("Switch", dict(label="Switch", active_track_color="#ff0000")),
             ("Radio", dict(value="one", label="One", toggleable=True)),
             ("Slider", dict(value=.5, secondary_track_value=.8)),
             ("Dropdown", dict(editable=True, enable_filter=True, menu_height=96)),
             ("DropdownOption", dict(key="a", text="Alpha", leading_icon=st.Icons.SETTINGS))]
    for name, kwargs in cases:
        reference = getattr(flet, name)
        assert set(kwargs) <= set(inspect.signature(reference).parameters)
        # Enum/value types differ between libraries; compare portable constructor values.
        portable = {k: (getattr(v, "value", v) if k not in ("style", "leading_icon") else v)
                    for k, v in kwargs.items()}
        if name == "Text":
            portable["style"] = flet.TextStyle(size=18)
            portable["overflow"] = flet.TextOverflow.ELLIPSIS
        if name == "DropdownOption":
            portable["leading_icon"] = flet.Icons.SETTINGS
        reference(**portable)
        getattr(st, name)(**kwargs)
    print("INSTALLED FLET CONSTRUCTOR PARAMETER COMPARISON PASS")


if __name__ == "__main__":
    pygame.init()
    pygame.display.set_mode((520, 480), flags=pygame.HIDDEN)
    renderer = SoftwareRenderer()
    page = Page(App(renderer))
    try:
        check_reference_parameters()
        check_field(page, renderer)
        check_text(page, renderer)
        check_toggles(page, renderer)
        check_slider_dropdown(page, renderer)
        check_transformed_ime(page, renderer)
        check_transformed_dropdown(page, renderer)
        check_dropdown_floating_label(page, renderer)
    finally:
        renderer.close()
        pygame.quit()
    print("INPUT PARAMETER CHECKS PASS")
