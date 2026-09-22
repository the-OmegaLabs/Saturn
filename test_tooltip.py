"""Self-check for Flet-style hover tooltips."""
import pygame

import saturn as ft


class App:
    size = (320, 200)

    def mark_dirty(self):
        pass


class Renderer:
    scale = 1

    def __init__(self):
        self.rects = []
        self.blits = []

    def overlay_rect(self, *args, **kwargs):
        self.rects.append((args, kwargs))

    def blit(self, *args, **kwargs):
        self.blits.append((args, kwargs))


def check_tooltip():
    pygame.font.init()
    page = ft.Page(App())
    control = ft.Container(width=100, height=40,
                           tooltip=ft.Tooltip("Open file"))
    control._rect = (20, 20, 100, 40)
    assert control._hit_test_hover(30, 30) is control
    page._hovered = control
    renderer = Renderer()
    page._draw_tooltip(renderer)
    assert len(renderer.rects) == len(renderer.blits) == 1
    assert renderer.rects[0][0][2] > 0

    control.tooltip = "Plain string"
    page._draw_tooltip(renderer)
    assert len(renderer.blits) == 2


if __name__ == "__main__":
    check_tooltip()
    print("ALL TOOLTIP TESTS PASS")
