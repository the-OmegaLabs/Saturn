"""Check Saturn's common Flet-style controls against the installed Flet.

Run with a Flet 1.x installation: python -m tests.flet_api_checks
This checks real constructors and stored properties, then exercises selected
Saturn edit/layout paths. It does not claim rendered parity with Flutter.
"""
from __future__ import annotations

import inspect
from importlib.metadata import version
from unittest.mock import patch

import flet
import pygame
import saturn


CASES = {
    "Text": ({"value": "hello", "size": 16}, ("value", "size")),
    "Button": ({"content": "OK", "bgcolor": "#123456"},
               ("content", "bgcolor")),
    "TextField": ({"value": "abc", "label": "Name", "multiline": False},
                  ("value", "label", "multiline")),
    "ListView": ({"controls": [], "spacing": 4, "item_extent": 40},
                 ("spacing", "item_extent")),
    "Row": ({"controls": [], "spacing": 3}, ("spacing",)),
    "Column": ({"controls": [], "spacing": 3}, ("spacing",)),
    "Container": ({"padding": 8, "bgcolor": "#123456"},
                  ("padding", "bgcolor")),
    "Checkbox": ({"label": "A", "value": True}, ("label", "value")),
    "Switch": ({"label": "A", "value": True}, ("label", "value")),
    "Slider": ({"value": .5, "min": 0, "max": 1},
               ("value", "min", "max")),
    "Dropdown": ({"options": []}, ("options",)),
    "Radio": ({"value": "a", "label": "A"}, ("value", "label")),
    "ProgressBar": ({"value": .5, "bar_height": 4},
                    ("value", "bar_height")),
    "FloatingActionButton": ({"icon": flet.Icons.ADD,
                              "bgcolor": "#123456"}, ("bgcolor",)),
    "Card": ({"elevation": 2}, ("elevation",)),
    "Divider": ({"height": 20, "thickness": 2},
                ("height", "thickness")),
    "FilledButton": ({"content": "Filled"}, ("content",)),
    "FilledTonalButton": ({"content": "Tonal"}, ("content",)),
    "OutlinedButton": ({"content": "Outlined"}, ("content",)),
    "TextButton": ({"content": "Text"}, ("content",)),
    "Icon": ({"icon": flet.Icons.ADD, "size": 20}, ("size",)),
    "IconButton": ({"icon": flet.Icons.ADD, "selected": True},
                   ("selected",)),
    "Image": ({"src": None}, ("src",)),
    "ProgressRing": ({"value": .4, "stroke_width": 3},
                     ("value", "stroke_width")),
    "Stack": ({"controls": []}, ("controls",)),
    "Tooltip": ({"message": "Hello"}, ("message",)),
    "AlertDialog": ({"modal": True}, ("modal",)),
    "GestureDetector": ({"on_tap": None}, ("on_tap",)),
    "DropdownOption": ({"key": "a", "text": "A"},
                       ("key", "text")),
}


def _explicit_parameters(cls):
    """Include Saturn's shared Control arguments, excluding catch-all kwargs."""
    names = set()
    for base in cls.__mro__:
        if base is object:
            break
        for name, parameter in inspect.signature(base.__init__).parameters.items():
            if parameter.kind not in (parameter.VAR_POSITIONAL,
                                      parameter.VAR_KEYWORD):
                names.add(name)
        if base is saturn.Control:
            break
    return names - {"self"}


def main():
    shared = sorted(
        name for name in saturn.__all__
        if inspect.isclass(getattr(saturn, name, None)) and
        inspect.isclass(getattr(flet, name, None)))
    assert len(shared) >= 60, len(shared)
    for name, (kwargs, properties) in CASES.items():
        original = getattr(flet, name)(**kwargs)
        local_kwargs = dict(kwargs)
        if name in ("FloatingActionButton", "Icon", "IconButton"):
            local_kwargs["icon"] = saturn.Icons.ADD
        local = getattr(saturn, name)(**local_kwargs)
        for prop in properties:
            left, right = getattr(original, prop), getattr(local, prop)
            if name == "Container" and prop == "padding":
                assert (right.left, right.top, right.right, right.bottom) == (
                    left, left, left, left)
                continue
            assert left == right, (name, prop, left, right)
    # These are live control behaviors that a constructor-only audit missed.
    flet_text = flet.Text("a\nb", no_wrap=True)
    text = saturn.Text("a\nb", no_wrap=True)
    assert flet_text.no_wrap and text.no_wrap
    width, height = text._intrinsic(20, 100, 1)
    text._place(0, 0, width, height, 1)
    assert text._lines == ["a", "b"] and height > text._line_h

    class TextRecorder:
        scale = 1

        def __init__(self):
            self.blits = 0
            self.clips = 0

        def clip_push(self, *_args):
            self.clips += 1

        def clip_pop(self):
            self.clips -= 1

        def blit_cached(self, *_args):
            self.blits += 1

    recorder = TextRecorder()
    text._draw(recorder, 0, 0)
    assert recorder.blits == 2 and recorder.clips == 0

    flet_field = flet.TextField(max_length=3, shift_enter=True,
                                show_cursor=False,
                                obscuring_character="*")
    field = saturn.TextField(max_length=3, shift_enter=True,
                             show_cursor=False,
                             obscuring_character="*", multiline=True)
    for prop in ("max_length", "shift_enter", "show_cursor",
                 "obscuring_character"):
        assert getattr(flet_field, prop) == getattr(field, prop)
    field._text_input("abcde")
    assert field.value == "abc"
    field._text_input("z")
    assert field.value == "abc"
    field._select_range(1, 3)
    field._text_input("XYZ")
    assert field.value == "aXY"
    field.password = True
    assert field._visible_text() == "***"
    with patch("saturn.widgets.inputs.fire") as emit:
        field._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN,
                                     mod=0))
        emit.assert_called_once_with(field, "submit", "aXY")
    field._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN,
                                 mod=pygame.KMOD_SHIFT))
    assert field.value == "aXY"  # capped at max_length
    field._set_focused(True)
    assert not field._cursor_visible and field._cursor_timer is None
    field._set_focused(False)
    multiline = saturn.TextField(multiline=True, shift_enter=True)
    multiline._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN,
                                     mod=pygame.KMOD_SHIFT))
    assert multiline.value == "\n"

    flet_slider = flet.Slider(min=10, max=20, divisions=4)
    slider = saturn.Slider(min=10, max=20, divisions=4)
    assert (flet_slider.min, flet_slider.max, flet_slider.divisions) == (
        slider.min, slider.max, slider.divisions)
    slider._place(0, 0, 104, 48, 1)
    assert slider._value_from_x(27.5) == 12.5

    for name in ("FilledButton", "FilledTonalButton", "ElevatedButton",
                 "OutlinedButton", "TextButton"):
        assert not getattr(saturn, name)("x").expressive
        assert getattr(saturn.Compose, name)("x").expressive

    flet_fab = flet.FloatingActionButton(
        icon=flet.Icons.ADD, mini=True, foreground_color="#ABCDEF")
    fab = saturn.FloatingActionButton(
        icon=saturn.Icons.ADD, mini=True, foreground_color="#ABCDEF")
    assert (fab.mini, fab.foreground_color) == (
        flet_fab.mini, flet_fab.foreground_color)
    assert fab._intrinsic(None, None, 1) == (40.0, 40.0)
    assert saturn.FloatingActionButton()._intrinsic(None, None, 1) == (56.0, 56.0)
    assert saturn.FloatingActionButton(content="Add").content == (
        flet.FloatingActionButton(content="Add").content)

    print(f"Flet {version('flet')}: {len(shared)} shared exported classes; "
          f"{len(CASES)} common constructors/properties and 4 Saturn "
          "behavior paths pass")
    for name in CASES:
        flet_args = set(inspect.signature(getattr(flet, name)).parameters)
        local_args = _explicit_parameters(getattr(saturn, name))
        missing = sorted(flet_args - local_args)
        print(f"{name}: {len(missing)} Flet parameters without an explicit "
              f"Saturn implementation; examples: {', '.join(missing[:6])}")


if __name__ == "__main__":
    main()
