"""Real GPU checks for edge coverage and dynamic bitmap replacement.

python -m tests.dynamic_renderer_checks
python -m tests.dynamic_renderer_checks --stress
"""
import argparse
import math
import statistics
import time
from pathlib import Path
from unittest.mock import patch

import pygame

import saturn as st
from saturn.painting import draw_shadow
from saturn.renderer import create_renderer


ROOT = Path(__file__).resolve().parents[1]


def make_renderer(backend):
    window = pygame.Window('Dynamic renderer checks', size=(640, 360), hidden=True,
                           opengl=backend is st.Renderer.OPENGL,
                           vulkan=backend is st.Renderer.VULKAN)
    return window, create_renderer(backend, window, vsync=False)


def edge_count(frame):
    return sum(1 for y in range(frame.get_height()) for x in range(frame.get_width())
               if 195 < frame.get_at((x, y)).r < 255 and
                  38 < frame.get_at((x, y)).g < 255)


def check_edges(renderer):
    renderer.clear('white')
    renderer.line(8.2, 11.4, 87.6, 52.8, (195, 38, 82, 255), width=1.25)
    frame = renderer.screenshot()
    lines = edge_count(frame)
    assert lines >= 30, lines
    # A diagonal must not fill its entire axis-aligned bounding rectangle.
    assert frame.get_at((12, 48))[:3] == (255, 255, 255)
    renderer.clear('white')
    renderer.arc(48, 32, 23, .2, 5.5, (195, 38, 82, 255), width=1.5)
    arcs = edge_count(renderer.screenshot())
    assert arcs >= 30, arcs
    print(type(renderer).__name__, 'samples', getattr(renderer, '_gpu_samples', None),
          'covered line pixels', lines, 'covered arc pixels', arcs)


def controls():
    items = [st.LoadingIndicator(color='#C32652'),
             st.LinearWavyProgressIndicator(.5, color='#C32652'),
             st.CircularWavyProgressIndicator(.5, color='#C32652')]
    for control, rect in zip(items, ((8, 8, 48, 48), (80, 25, 220, 18),
                                     (330, 8, 64, 64))):
        control._place(*rect, 1)
    return items


def check_dynamic_geometry(renderer):
    items = controls()
    before = len(getattr(renderer, '_gpu_tex_cache', getattr(renderer, '_tex_cache', {})))
    frames = []
    for elapsed in (0, .3):
        renderer.clear('white')
        with patch('pygame.Surface', side_effect=AssertionError('dynamic CPU bitmap')):
            for control in items:
                control._elapsed = elapsed
                control._draw(renderer, *control._rect[:2])
        frame = renderer.screenshot()
        frames.append(pygame.image.tobytes(frame, 'RGBA'))
    assert frames[0] != frames[1]
    after = len(getattr(renderer, '_gpu_tex_cache', getattr(renderer, '_tex_cache', {})))
    assert before == after, (before, after)
    assert not getattr(renderer, '_pending_textures', ())


def check_tint_and_shadows(renderer):
    image = st.Image(str(ROOT / '.static' / 'saturn-logo-transparent.png'),
                     width=52, height=40, color='#FFFFFF')
    image._place(10, 10, 52, 40, renderer.scale)
    renderer.clear('white')
    image._draw(renderer, 10, 10)
    draw_shadow(renderer, (80, 30, 120, 48), 16, 6)
    renderer.flip()
    prepared = image._prepared_surface
    for tint in ('#C32652', '#2468AC', '#663366'):
        image.color = tint
        renderer.clear('white')
        with (patch('pygame.image.tobytes', side_effect=AssertionError('rehashed pixels')),
              patch('saturn.painting._shadow', side_effect=AssertionError('CPU shadow'))):
            image._draw(renderer, 10, 10)
            draw_shadow(renderer, (80, 30, 120, 48), 16, 6)
        assert image._prepared_surface is prepared
        renderer.flip()
    icon = st.Icon(st.Icons.FAVORITE, color='#C32652')
    icon._place(240, 20, 24, 24, renderer.scale)
    renderer.clear('white')
    icon._draw(renderer, 240, 20)
    renderer.flip()
    with patch('pygame.image.tobytes', side_effect=AssertionError('tinted glyph upload')):
        icon.color = '#2468AC'
        icon._draw(renderer, 240, 20)
    renderer.flip()
    # A source texture is reused while its tint and opacity are GPU parameters.
    white = pygame.Surface((8, 8), pygame.SRCALPHA)
    white.fill('white')
    renderer.clear('white')
    renderer.blit_tinted_scaled(white, 10, 10, 20, 20, (195, 38, 82, 255))
    assert all(abs(renderer.screenshot().get_at((20, 20))[i] - (195, 38, 82)[i]) <= 2
               for i in range(3))
    # Animated bitmap enlargement keeps original source pixels on the GPU.
    image._surface = white
    image._load = lambda: white
    image._loaded_key = 'small-upscale'
    image._is_svg = False
    for size in (20, 30):
        image._place(10, 10, size, size, renderer.scale)
        image._draw(renderer, 10, 10)
        assert image._prepared_surface is white


def check_visual_reference(renderer):
    # Compare shape silhouettes to the original bitmap path on the same GPU,
    # avoiding font rasterizer or presentation differences between backends.
    controls_to_check = controls()
    for elapsed in (0, .3, .65, 1.2, 1.95, 2.6, 3.25, 3.9):
        frames = []
        for native in (False, True):
            renderer.native_geometry = renderer.native_shadow = native
            renderer.clear('white')
            for control in controls_to_check:
                control._elapsed = elapsed
                control._draw(renderer, *control._rect[:2])
            draw_shadow(renderer, (80, 100, 180, 56), (24, 10, 10, 24), 6)
            renderer.fill_rect(80, 100, 180, 56, '#EEEEEE', radius=24)
            frames.append(renderer.screenshot())
        for name, bounds in (('loading', (4, 4, 56, 56)),
                             ('linear wave', (76, 20, 230, 30)),
                             ('circular wave', (326, 4, 72, 72)),
                             ('shadow', (50, 70, 240, 120))):
            x, y, w, h = bounds
            difference = sum(abs(frames[0].get_at((px, py))[channel] -
                                 frames[1].get_at((px, py))[channel])
                             for py in range(y, y + h) for px in range(x, x + w)
                             for channel in range(3)) / (w * h * 3)
            assert difference < 12, (name, elapsed, difference)
        if elapsed == .3:
            output = ROOT / '.build-probe' / f'dynamic-{type(renderer).__name__}.png'
            output.parent.mkdir(exist_ok=True)
            combined = pygame.Surface((420, 360))
            combined.blit(frames[0], (0, 0), (0, 0, 420, 180))
            combined.blit(frames[1], (0, 180), (0, 0, 420, 180))
            pygame.image.save(combined, output)
    renderer.native_geometry = renderer.native_shadow = True


def check_effects_and_resize(renderer, window):
    renderer.clear('white')
    renderer.clip_push(10, 10, 20, 20)
    renderer.opacity_push(.5)
    renderer.translate_push(10, 10)
    renderer.polygon(((0, 0), (20, 0), (20, 20), (0, 20)), (0, 0, 0, 255),
                     center=(10, 10))
    renderer.translate_pop()
    renderer.opacity_pop()
    renderer.clip_pop()
    frame = renderer.screenshot()
    assert all(125 <= frame.get_at((20, 20))[i] <= 130 for i in range(3))
    assert frame.get_at((32, 20))[:3] == (255, 255, 255)
    window.size = (480, 300)
    renderer.on_resize(480, 300, pixel_size=(480, 300), pixel_ratio=1)
    check_dynamic_geometry(renderer)
    assert renderer.screenshot().get_size() == (480, 300)
    window.size = (640, 360)
    renderer.on_resize(640, 360, pixel_size=(640, 360), pixel_ratio=1)


def stress(renderer):
    items = []
    for row in range(4):
        for column in range(6):
            control = st.LoadingIndicator() if column < 3 else st.LinearWavyProgressIndicator(.5)
            control._place(column * 100 + 8, row * 82 + 10,
                           48 if column < 3 else 88, 48 if column < 3 else 16,
                           renderer.scale)
            items.append(control)
    results = {}
    for native in (False, True):
        renderer.native_geometry = native
        samples = []
        for index in range(70):
            started = time.perf_counter()
            renderer.clear('white')
            for control in items:
                control._elapsed = index / 60
                control._draw(renderer, *control._rect[:2])
            renderer.flip()
            if index >= 10:
                samples.append((time.perf_counter() - started) * 1000)
        results['geometry' if native else 'bitmaps'] = {
            'p50_ms': round(statistics.median(samples), 3),
            'p95_ms': round(sorted(samples)[math.ceil(len(samples) * .95) - 1], 3)}
    print(type(renderer).__name__, '24 animated controls:', results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stress', action='store_true')
    args = parser.parse_args()
    pygame.init()
    try:
        for backend in (st.Renderer.OPENGL, st.Renderer.VULKAN):
            window, renderer = make_renderer(backend)
            try:
                check_edges(renderer)
                check_dynamic_geometry(renderer)
                check_tint_and_shadows(renderer)
                check_visual_reference(renderer)
                check_effects_and_resize(renderer, window)
                if args.stress:
                    stress(renderer)
            finally:
                renderer.close()
                window.destroy()
    finally:
        pygame.quit()
    print('DYNAMIC RENDERER CHECKS PASS')


if __name__ == '__main__':
    main()
