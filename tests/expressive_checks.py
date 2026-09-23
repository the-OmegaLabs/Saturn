"""Run with `uv run python -m tests.expressive_checks`."""
from types import SimpleNamespace
from unittest.mock import patch
import pygame
import saturn as ft
from saturn.renderer.software import SoftwareRenderer
from saturn.widgets._material import draw_state_layer
from saturn.painting import _shadow, _scaled_shadow, draw_shadow
from saturn.widgets.expressive_progress import _shapes, _morph_points
import math
import time


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
        field._label_progress = 1.0  # Nonempty labels stay floated across focus changes.
        field._focus_progress = progress
        field._focused = True
        field._draw(r, 0, 0)
        assert r._buf.get_at((28, 1))[:3] == (18, 52, 86)
    shadow, pad = _shadow(600, 80, (40, 40, 40, 40), 6, 2)
    assert shadow.get_at((0, 0)).a == 0
    alphas = [shadow.get_at((pad + 300, pad + 80 + n)).a for n in range(20)]
    assert len(set(alphas)) > 8, alphas


def check_label_cutout():
    r = renderer()
    field = ft.TextField('', label='Transition label')
    field._place(0, 0, 240, 56, r.scale)
    def gap_at(progress, focused):
        field._label_progress = progress
        field._focused = focused
        r.clear('#123456')
        # Inspect the border separately from glyphs that overlap its gap.
        with patch.object(r, 'blit'), patch.object(r, 'blit_scaled'):
            field._draw(r, 0, 0)
        # Fractional cutout clips must never punch a hole in the bottom edge.
        assert all(r._buf.get_at((x,111))[:3] != (18,52,86) for x in range(16,464))
        return sum(r._buf.get_at((x, 1))[:3] == (18,52,86)
                   for x in range(24,360))
    samples = (0, .01, .1, .25, .5, .75, 1)
    opening = [gap_at(p, True) for p in samples]
    closing = [gap_at(p, False) for p in reversed(samples)]
    assert opening == list(reversed(closing))  # Geometry must not depend on focus intent.
    assert opening[0] == 0 and opening[-1] > opening[3] > opening[2]
    assert opening == sorted(opening), opening
    field._label_progress = 0.0
    field._restart_cursor_blink = lambda: None
    field._stop_cursor_blink = lambda: None
    with patch('saturn.control.time.perf_counter', return_value=10):
        field._set_focused(True)
    assert field._label_progress == 0
    field._tick_animations(10.075)
    assert 0 < field._label_progress < 1
    field._tick_animations(10.2)
    assert field._label_progress == 1
    with patch('saturn.control.time.perf_counter', return_value=11):
        field._set_focused(False)
    field._tick_animations(11.075)
    assert 0 < field._label_progress < 1
    field._tick_animations(11.2)
    assert field._label_progress == 0


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


def check_shadow_work():
    r = renderer(1100,120)
    _shadow.cache_clear()
    _scaled_shadow.cache_clear()
    with patch('pygame.transform.gaussian_blur', wraps=pygame.transform.gaussian_blur) as blur:
        for opacity in (1,.8,.4,.1):
            r.opacity_push(opacity)
            draw_shadow(r,(20,20,1000,64),32,6)
            r.opacity_pop()
        assert blur.call_count == 2  # Opacity must not invalidate the silhouette.
        for call in blur.call_args_list:
            w,h = call.args[0].get_size()
            assert w*h < 1000*64  # Animation filters never operate at display resolution.


def check_floating():
    a,b,c = [ft.IconButton(ft.Icons.ADD) for _ in range(3)]
    toolbar = ft.FloatingToolbar(b,leading=a,trailing=c)
    expanded = toolbar._intrinsic(None,None,1)
    toolbar._reveal = 0
    collapsed = toolbar._intrinsic(None,None,1)
    assert collapsed == (56,64) and collapsed[0] < expanded[0]
    toolbar._place(0,0,*collapsed,1)
    assert toolbar._hit_test(20,32) is b
    r = renderer()
    app = SimpleNamespace(size=(400,300),renderer=r,mark_dirty=lambda:None,
                          post=lambda fn:None,call=lambda fn,*args:fn(*args))
    page = ft.Page(app)
    selected = []
    item = ft.FloatingActionButtonMenuItem('Create',icon=ft.Icons.ADD,
                                         on_click=lambda event:selected.append(event.control))
    menu = ft.FloatingActionButtonMenu([item])
    page.add(menu)
    menu._place(300,230,56,56,1)
    menu.toggle()
    assert menu._overlay in page.overlay
    menu._overlay._place(0,0,400,300,1)
    ix,iy,iw,ih = item._rect
    assert page._hit_test(ix+iw/2,iy+ih/2) is item
    assert page._hit_test_hover(ix+iw/2,iy+ih/2) is item
    item._activate()
    assert not menu.expanded and selected == [item]
    menu._tick_animations(time.perf_counter()+1)
    assert not page.overlay
    menu.toggle()
    page.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
    assert not menu.expanded
    page.remove(menu)
    menu._overlay._tick_animations(time.perf_counter())
    assert not page.overlay and menu._overlay is None


if __name__ == '__main__':
    check_regressions()
    check_label_cutout()
    check_progress()
    check_shadow_work()
    check_floating()
    print('EXPRESSIVE REGRESSION CHECKS PASS')
