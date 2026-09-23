"""The classic Saturn badge renders consistently in both themes."""
from pathlib import Path
import saturn as ft
from saturn import colors


class Capture:
    scale = 1

    def blit(self, surface, _x, _y):
        self.surface = surface


def check():
    image = ft.Image(str(Path(__file__).resolve().parents[1] / 'saturn-logo.svg'),
                     width=36, height=36, fit=ft.BoxFit.CONTAIN)
    image._place(0, 0, 36, 36, 1)
    capture = Capture()
    seen = []
    try:
        for dark in (False, True):
            colors.theme_dark = dark
            image._draw(capture, 0, 0)
            assert capture.surface.get_at((0, 0)).a < 32
            assert capture.surface.get_at((18, 18)).a > 250
            assert capture.surface.get_at((18, 18))[:3] == (0, 0, 0)
            assert any(sum(capture.surface.get_at((x, y))[:3]) > 600
                       for x in range(36) for y in range(36))
            seen.append(capture.surface.get_at((18, 18)))
        assert seen[0] == seen[1]
    finally:
        colors.theme_dark = False


if __name__ == '__main__':
    check()
    print('CLASSIC LOGO PASS')
