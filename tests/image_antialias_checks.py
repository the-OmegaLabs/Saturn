"""Image prepares SVG and bitmap pixels at the device display size."""
from pathlib import Path

import pygame
import saturn as ft


ROOT = Path(__file__).resolve().parents[1]


class GPUCapture:
    scale = 2
    native_texture_scaling = True

    def blit_cached_scaled(self, surface, x, y, width, height):
        self.last = (surface, x, y, width, height)


def check():
    pygame.init()
    capture = GPUCapture()
    svg = ROOT / '.static' / 'saturn-logo.svg'
    image = ft.Image(str(svg), width=52, height=40, fit=ft.BoxFit.CONTAIN)
    image._place(0, 0, 52, 40, capture.scale)
    image._draw(capture, 0, 0)
    prepared, x, y, width, height = capture.last
    assert prepared.get_size() == (80, 80)
    assert (x, y, width, height) == (6, 0, 40, 40)
    direct_svg = pygame.image.load_sized_svg(str(svg), (80, 80))
    assert pygame.image.tobytes(prepared, 'RGBA') == \
           pygame.image.tobytes(direct_svg, 'RGBA')
    assert any(0 < prepared.get_at((x, y)).a < 255
               for x in range(80) for y in range(80))
    image._draw(capture, 0, 0)
    assert capture.last[0] is prepared

    png = ROOT / '.static' / 'saturn-logo-transparent.png'
    image = ft.Image(str(png), width=52, height=40)
    image._place(0, 0, 52, 40, capture.scale)
    image._draw(capture, 0, 0)
    prepared = capture.last[0]
    assert image._surface.get_size() == (410, 304)
    assert prepared.get_size() == (104, 80)
    expected = pygame.transform.smoothscale(image._surface, (104, 80))
    assert pygame.image.tobytes(prepared, 'RGBA') == \
           pygame.image.tobytes(expected, 'RGBA')
    image._draw(capture, 0, 0)
    assert capture.last[0] is prepared


if __name__ == '__main__':
    check()
    print('IMAGE ANTIALIAS CHECKS PASS')
