"""Renderer pixel-compositing self-check."""
import sys

sys.path.insert(0, ".")

import pygame

from saturn.renderer.software import SCALE, SoftwareRenderer
from saturn.widgets.basic import Image


def check_image_load_without_display_surface():
    pygame.display.quit()
    image = Image("examples/assets/test_img.png")
    surface = image._load()
    assert surface is not None
    assert surface.get_flags() & pygame.SRCALPHA
    assert surface.get_size() == (240, 140)


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


def check_scaled_blit():
    pygame.init()
    pygame.display.set_mode((100, 100))
    renderer = SoftwareRenderer()
    renderer.clear((0, 0, 0, 255))
    source = pygame.Surface((8, 8), pygame.SRCALPHA)
    source.fill((240, 120, 30, 255))
    renderer.blit_scaled(source, 10, 12, 16, 10)
    inside = renderer._buf.get_at((20 * SCALE, 16 * SCALE))
    outside = renderer._buf.get_at((27 * SCALE, 16 * SCALE))
    assert tuple(inside) == (240, 120, 30, 255), inside
    assert tuple(outside) == (0, 0, 0, 255), outside
    pygame.display.quit()


def check_translucent_circle_composites():
    pygame.init()
    pygame.display.set_mode((100, 100))
    renderer = SoftwareRenderer()
    renderer.clear((20, 30, 40, 255))
    renderer.circle(30, 30, 10, (255, 255, 255, 128))
    pixel = renderer._buf.get_at((30 * SCALE, 30 * SCALE))
    assert pixel.a == 255, pixel
    assert 135 <= pixel.r <= 140, pixel
    assert 140 <= pixel.g <= 145, pixel
    assert 145 <= pixel.b <= 150, pixel
    pygame.display.quit()


if __name__ == "__main__":
    check_image_load_without_display_surface()
    check_translucent_stroke_composites()
    check_scaled_blit()
    check_translucent_circle_composites()
    print("ALL RENDERER TESTS PASS")
