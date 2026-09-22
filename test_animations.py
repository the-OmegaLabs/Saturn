"""Implicit-animation and renderer-effect self-check."""
import sys
import threading

sys.path.insert(0, ".")

import pygame

import saturn as ft
from saturn.animation import animation_spec, ease
from saturn.control import Control
from saturn.renderer.software import SCALE, SoftwareRenderer
from saturn.widgets.buttons import FilledButton
from saturn.widgets.basic import ProgressBar, ProgressRing
from saturn.widgets.containers import Container, Stack
from saturn.widgets.inputs import Checkbox, Switch


class _App:
    def __init__(self):
        self.events = []

    def call(self, fn, *args):
        fn(*args)

    def mark_dirty(self):
        pass


class _Page:
    def __init__(self):
        self._app = _App()

    def update(self):
        pass


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


def check_animation_values_and_curves():
    assert animation_spec(True) == (1.0, ft.AnimationCurve.LINEAR)
    assert animation_spec(250) == (0.25, ft.AnimationCurve.LINEAR)
    duration, curve = animation_spec(
        ft.Animation(ft.Duration(milliseconds=300), ft.AnimationCurve.EASE_IN_OUT))
    assert duration == 0.3 and curve is ft.AnimationCurve.EASE_IN_OUT
    for curve in ft.AnimationCurve:
        assert ease(curve, 0) == 0
        assert ease(curve, 1) == 1
    assert approx(ease(ft.AnimationCurve.EASE_IN_QUAD, 0.5), 0.25)
    assert approx(ease(ft.AnimationCurve.EASE_OUT_QUAD, 0.5), 0.75)


def check_opacity_and_interruption():
    events = []
    c = Control(opacity=1, animate_opacity=1000,
                on_animation_end=lambda e: events.append(e.data))
    c._attach(_Page())
    c.opacity = 0
    c._prepare_animations(10.0)
    assert c.opacity == 1
    assert c._tick_animations(10.5)
    assert approx(c.opacity, 0.5)

    # A new target begins at the currently presented value, not the stale end.
    c.opacity = 1
    c._prepare_animations(10.5)
    c._tick_animations(11.0)
    assert approx(c.opacity, 0.75)
    assert not c._tick_animations(11.5)
    assert c.opacity == 1
    assert events == ["opacity"]


def check_size_position_and_container_color():
    c = Container(width=100, height=40, left=0, bgcolor="#000000",
                  animate_size=1000, animate_position=1000,
                  animate=ft.Animation(1000, ft.AnimationCurve.LINEAR))
    c._attach(_Page())
    c._width = 200
    c.left = 80
    c.bgcolor = "#ffffff"
    c._prepare_animations(20.0)
    c._tick_animations(20.5)
    assert approx(c.width, 150)
    assert approx(c.left, 40)
    assert c.bgcolor == (128, 128, 128, 255), c.bgcolor
    c._place(0, 0, c.width, c.height, 1)
    assert approx(c._rect[2], 150)

    # Stack lays out and hit-tests at the presented (intermediate) position.
    stack = Stack(c, width=400, height=100)
    stack._place(0, 0, 400, 100, 1)
    assert approx(c._rect[0], 40)
    assert c._contains(45, 10)
    assert not c._contains(10, 10)


def check_renderer_opacity_and_translation():
    pygame.init()
    pygame.display.set_mode((40, 30))
    r = SoftwareRenderer()
    r.clear((255, 255, 255, 255))
    r.opacity_push(0.5)
    r.translate_push(10, 0)
    r.fill_rect(0, 0, 10, 10, (255, 0, 0, 255))
    r.translate_pop()
    r.opacity_pop()
    untouched = r._buf.get_at((2 * SCALE, 2 * SCALE))
    blended = r._buf.get_at((12 * SCALE, 2 * SCALE))
    assert untouched == pygame.Color(255, 255, 255, 255), untouched
    assert blended.a == 255 and blended.r == 255
    assert 126 <= blended.g <= 128 and 126 <= blended.b <= 128, blended
    pygame.display.quit()


def check_material_state_transitions():
    page = _Page()
    button = FilledButton("go")
    button._attach(page)
    button._set_hover(True)
    button._animations["_state_hover_alpha"].started = 0.0
    button._tick_animations(0.0075)
    assert 0 < button._state_hover_alpha < 0.08
    button._pressed = True
    button._pressed_hook(0, 0)
    assert button._animations["_state_press_alpha"].end_value == 0.12
    assert button._animations["_state_ripple_progress"].duration == 0.45

    for control, midpoint, endpoint in (
            (Checkbox(value=False), 0.175, 0.36),
            (Switch(value=False), 0.075, 0.31)):
        control._attach(page)
        control._toggle()
        control._animations["_value_progress"].started = 0.0
        control._tick_animations(midpoint)
        assert 0 < control._value_progress < 1
        control._tick_animations(endpoint)
        assert control._value_progress == 1

    ink = Container(width=100, height=40, ink=True)
    ink._attach(page)
    ink._pressed = True
    ink._pressed_hook(10, 10)
    assert ink._animations["_state_press_alpha"].end_value == 0.12
    ink._pressed = False
    ink._released_hook(10, 10)
    assert ink._state_release_deadline is not None, "quick taps need a visible pulse"
    deadline = ink._state_release_deadline
    ink._tick_animations(deadline)
    assert ink._state_release_deadline is None
    assert ink._animations["_state_press_alpha"].end_value == 0.0


def check_material_progress_transitions():
    page = _Page()
    bar = ProgressBar(0.1)
    bar._attach(page)
    bar.value = 0.9
    bar._prepare_animations(0.0)
    assert bar._animations["_display_value"].duration == 0.25
    bar._tick_animations(0.125)
    assert 0.1 < bar._display_value < 0.9

    ring = ProgressRing(0.1)
    ring._attach(page)
    ring.value = 0.9
    ring._prepare_animations(0.0)
    assert ring._animations["_display_value"].duration == 0.5
    ring._tick_animations(0.25)
    assert 0.1 < ring._display_value < 0.9

    busy = ProgressBar(None)
    busy._attach(page)
    busy._phase_started = 0.0
    assert busy._tick_animations(1.0)
    assert busy._phase == 0.5


def check_worker_ui_thread_safety():
    c = Control(opacity=1, animate_opacity=10)
    c._attach(_Page())
    errors = []

    def update_worker():
        try:
            for i in range(1000):
                c.opacity = i % 2
                c._prepare_animations(i / 1000)
        except Exception as exc:  # pragma: no cover - assertion captures races
            errors.append(exc)

    thread = threading.Thread(target=update_worker)
    thread.start()
    try:
        for i in range(1000):
            c._tick_animations(i / 1000)
    except Exception as exc:
        errors.append(exc)
    thread.join()
    assert not errors, errors


if __name__ == "__main__":
    check_animation_values_and_curves()
    check_opacity_and_interruption()
    check_size_position_and_container_color()
    check_renderer_opacity_and_translation()
    check_material_state_transitions()
    check_material_progress_transitions()
    check_worker_ui_thread_safety()
    print("ALL ANIMATION TESTS PASS")
