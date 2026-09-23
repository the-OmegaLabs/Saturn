"""Run with `uv run python -m tests.expressive_checks`."""
from types import SimpleNamespace
import pygame
import saturn as ft
from saturn.renderer.software import SoftwareRenderer
from saturn.widgets._material import draw_state_layer
from saturn.painting import _shadow
from saturn.widgets.expressive_progress import _shapes, _morph_points
import math


def renderer(w=400, h=200):
    return SoftwareRenderer(SimpleNamespace(get_surface=lambda: pygame.Surface((w, h))))


def check_regressions():
    r = renderer()
    r.clear((0, 0, 0, 0))
    state = SimpleNamespace(_state_hover_alpha=0, _state_press_alpha=.12,
                            _state_press_origin=(50, 20), _state_ripple_progress=1)
    draw_state_layer(state, r, (0, 0, 100, 40), '#FFFFFF', (20, 4, 4, 20))
    assert r._buf.get_at((2, 2)).a == 0
    assert r._buf.get_at((192, 4)).a > 0
    for progress in (0, .01, .5, 1):
        r.clear('#123456')
        field = ft.TextField('Value', label='Label')
        field._place(0, 0, 240, 56, r.scale)
        field._label_progress = progress
        field._focus_progress = progress
        field._focused = True
        field._draw(r, 0, 0)
        assert r._buf.get_at((28, 1))[:3] == (18, 52, 86)
    shadow, pad = _shadow(600, 80, (40, 40, 40, 40), 6, 2)
    assert shadow.get_at((0, 0)).a == 0
    alphas = [shadow.get_at((pad + 300, pad + 80 + n)).a for n in range(20)]
    assert len(set(alphas)) > 8, alphas


def check_progress():
    data = _shapes()
    assert len(data['sequence']) == 7
    for curves in data['sequence']:
        for progress in (0, .25, .5, .75, 1):
            pts = _morph_points(curves, progress)
            assert len(pts) > 20
            assert all(math.isfinite(v) for point in pts for v in point)
    r = renderer()
    for control in (ft.LoadingIndicator(), ft.LoadingIndicator(.5),
                    ft.WavyProgressIndicator(.5), ft.CircularWavyProgressIndicator(.5)):
        w, h = control._intrinsic(None, None, r.scale)
        control._place(0, 0, w, h, r.scale)
        r.clear((0, 0, 0, 0))
        control._draw(r, 0, 0)
        first = pygame.image.tobytes(r._buf, 'RGBA')
        control._elapsed = .3
        r.clear((0, 0, 0, 0))
        control._draw(r, 0, 0)
        if control.value is None or isinstance(control, ft.WavyProgressIndicator):
            assert first != pygame.image.tobytes(r._buf, 'RGBA')


if __name__ == '__main__':
    check_regressions()
    check_progress()
    print('EXPRESSIVE REGRESSION CHECKS PASS')
