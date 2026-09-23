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

    transparent = ft.Image(
        str(Path(__file__).resolve().parents[1] / 'saturn-logo-transparent.png'),
        width=52, height=40, color=ft.Colors.PRIMARY,
    )
    transparent._place(0, 0, 52, 40, 1)
    tinted = []
    try:
        for dark in (False, True):
            colors.theme_dark = dark
            transparent._draw(capture, 0, 0)
            surface = capture.surface
            assert surface.get_at((0, 0)).a < 32
            colored = next(surface.get_at((x, y)) for y in range(40)
                           for x in range(52) if surface.get_at((x, y)).a > 250)
            expected = ft.parse_color(ft.Colors.PRIMARY)
            assert all(abs(colored[i] - expected[i]) <= 3 for i in range(3))
            tinted.append(colored[:3])
        assert tinted[0] != tinted[1]
    finally:
        colors.theme_dark = False


if __name__ == '__main__':
    check()
    print('CLASSIC AND TRANSPARENT LOGO PASS')
