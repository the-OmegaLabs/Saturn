"""Renderer pixel-compositing self-check."""
import sys

sys.path.insert(0, ".")

import pygame

from saturn.renderer.software import SCALE, SoftwareRenderer


def check_translucent_stroke_composites():
    pygame.init()
    pygame.display.set_mode((100, 100))
    renderer = SoftwareRenderer()
    renderer.clear((20, 30, 40, 255))
    renderer.stroke_rect(10, 10, 50, 30, (255, 255, 255, 128), width=2)
    pixel = renderer._buf.get_at((10 * SCALE, 10 * SCALE))
    assert pixel.a == 255, pixel
    assert 135 <= pixel.r <= 140, pixel
    assert 140 <= pixel.g <= 145, pixel
    assert 145 <= pixel.b <= 150, pixel
    pygame.display.quit()


if __name__ == "__main__":
    check_translucent_stroke_composites()
    print("ALL RENDERER TESTS PASS")
