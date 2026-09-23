"""Theme tint keeps the transparent logo silhouette intact."""
from pathlib import Path
import saturn as ft
from saturn import colors


class Capture:
    scale = 1

    def blit(self, surface, _x, _y):
        self.surface = surface


def check():
    image = ft.Image(str(Path(__file__).resolve().parents[1] / 'saturn-logo-a2.svg'),
                     width=55, height=33, color=ft.Colors.PRIMARY)
    image._place(0, 0, 55, 33, 1)
    capture = Capture()
    seen = []
    try:
        for dark in (False, True):
            colors.theme_dark = dark
            image._draw(capture, 0, 0)
            assert capture.surface.get_at((0, 0)).a == 0
            pixel = capture.surface.get_at((25, 15))
            expected = ft.parse_color(ft.Colors.PRIMARY)
            assert pixel.a > 250
            assert all(abs(pixel[i] - expected[i]) <= 3 for i in range(3))
            seen.append(pixel[:3])
        assert seen[0] != seen[1]
    finally:
        colors.theme_dark = False


if __name__ == '__main__':
    check()
    print('THEME LOGO TINT PASS')
