"""Real-window GL/Vulkan parity for SVG, text, clipping, DPI and resizing.

Run with python -m tests.vulkan_supersampling_checks.
"""
from pathlib import Path

import pygame

import saturn as st
from saturn.renderer import create_renderer


ROOT = Path(__file__).resolve().parents[1]


def draw_scene(renderer):
    renderer.clear('white')
    for i, fraction in enumerate((0, .25, .5, .75)):
        image = st.Image(str(ROOT / '.static/saturn-logo.svg'), width=40, height=40)
        image._place(0, 0, 40, 40, renderer.scale)
        image._draw(renderer, 10 + 60 * i + fraction, 10)
    font = pygame.font.Font(None, round(16 * renderer.scale))
    renderer.blit_cached(font.render('SVG text 0123', True, 'black'), 10.25, 58.5)
    renderer.line(10.2, 82.4, 110.7, 112.8, 'black', width=1.25)
    renderer.arc(170, 100, 23, .2, 5.5, 'black', width=1.5)
    renderer.fill_rect(10.25, 130.5, 50, 25, 'black', radius=6)
    renderer.clip_push(75.5, 130.5, 35, 23)
    renderer.fill_rect(65, 120, 70, 50, (180, 45, 80, 128), radius=9)
    renderer.clip_pop()
    return renderer.screenshot()


def check():
    pygame.init()
    results = {}
    try:
        for backend in (st.Renderer.OPENGL, st.Renderer.VULKAN):
            window = pygame.Window(size=(256, 160), hidden=True, resizable=True,
                                   opengl=backend is st.Renderer.OPENGL,
                                   vulkan=backend is st.Renderer.VULKAN)
            renderer = None
            try:
                renderer = create_renderer(backend, window, vsync=False)
                for ratio, enabled in ((1, True), (1, False), (1.5, True),
                                       (2, True), (1, True)):
                    pixels = (round(256 * ratio), round(160 * ratio))
                    window.size = pixels
                    pygame.event.pump()
                    renderer.configure(anti_aliasing=enabled, vsync=False)
                    renderer.on_resize(256, 160, pixel_size=pixels, pixel_ratio=ratio)
                    ssaa = 2 if enabled and ratio < 1.5 else 1
                    assert renderer.scale == ssaa * ratio
                    if backend is st.Renderer.VULKAN:
                        assert renderer._render_extent == tuple(v * ssaa for v in pixels)
                        assert len(renderer._gpu_present_semaphores) == len(renderer._swapchain_images)
                    frame = draw_scene(renderer)
                    assert frame.get_size() == pixels
                    key = ratio, enabled
                    raw = pygame.image.tobytes(frame, 'RGB')
                    if backend is st.Renderer.OPENGL:
                        results[key] = raw
                    else:
                        delta = [abs(a - b) for a, b in zip(raw, results[key])]
                        mean = sum(delta) / len(delta)
                        assert mean < .1 and max(delta) <= 3, (key, mean, max(delta))
                        print('DPI', ratio, 'AA', enabled, 'mean RGB difference', round(mean, 4))
                # Opaque images must have the same edges in and outside an atlas.
                opaque = pygame.Surface((8, 8), pygame.SRCALPHA)
                opaque.fill('red')
                frames = []
                for method in (renderer.blit_scaled, renderer.blit_cached_scaled):
                    renderer.clear('white')
                    method(opaque, 10.25, 10.25, 40, 40)
                    frames.append(pygame.image.tobytes(renderer.screenshot(), 'RGB'))
                assert frames[0] == frames[1], backend
                # Crossing the DPI threshold must rebuild the target even when
                # the physical window size stays fixed.
                renderer.on_resize(128, 80, pixel_size=(256, 160), pixel_ratio=2)
                if backend is st.Renderer.VULKAN:
                    assert renderer._render_extent == (256, 160)
                renderer.clear('white')
                renderer.fill_rect(10, 10, 20, 20, (255, 0, 0, 255))
                shot = renderer.screenshot()
                assert shot.get_at((30, 30))[:3] == (255, 0, 0)
                assert shot.get_at((65, 30))[:3] == (255, 255, 255)
                renderer.on_resize(256, 160, pixel_size=(256, 160), pixel_ratio=1)
                if backend is st.Renderer.VULKAN:
                    assert renderer._render_extent == (512, 320)
                # Consecutive frames replace old content without trails.
                for i in range(12):
                    renderer.clear('white')
                    renderer.fill_rect(10 + i * 4, 10, 10, 10, 'black')
                    renderer.flip()
                assert renderer.screenshot().get_at((12, 12))[:3] == (255, 255, 255)
            finally:
                if renderer is not None:
                    renderer.close()
                window.destroy()
    finally:
        pygame.quit()


if __name__ == '__main__':
    check()
    print('VULKAN SUPERSAMPLING CHECKS PASS')
