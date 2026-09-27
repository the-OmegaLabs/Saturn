"""Real renderer affine transforms preserve local shapes, textures, and clips."""
from __future__ import annotations

from unittest.mock import patch

import pygame

import saturn as st
from saturn.renderer import create_renderer
from saturn.widgets.shader import Shader


def check(renderer):
    rotate = (0, 1, -1, 0, 200, 0)
    renderer.clear("white")
    renderer.transform_push(rotate)
    renderer.fill_rect(20, 30, 80, 20, "#FF0000", radius=7)
    renderer.transform_pop()
    frame = renderer.screenshot()
    assert frame.get_at((160, 60))[:3] == (255, 0, 0)
    assert frame.get_at((30, 40))[:3] == (255, 255, 255)
    assert frame.get_at((169, 21))[:3] == (255, 255, 255)
    assert renderer._transform_stack[-1] == (1, 0, 0, 1, 0, 0)

    source = pygame.Surface((16, 16), pygame.SRCALPHA)
    source.fill("red")
    source.fill("blue", (8, 0, 8, 16))
    renderer.clear("white")
    renderer.transform_push(rotate)
    renderer.blit_cached_scaled(source, 20, 30, 80, 20)
    renderer.transform_pop()
    frame = renderer.screenshot()
    assert frame.get_at((160, 30))[:3] == (255, 0, 0)
    assert frame.get_at((160, 90))[:3] == (0, 0, 255)

    renderer.clear("white")
    renderer.transform_push((1, 0, 0, 1, 100, 30))
    renderer.transform_push((0, 1, -1, 0, 100, 0))
    renderer.fill_rect(20, 30, 80, 20, "#FF0000")
    renderer.transform_pop()
    renderer.transform_pop()
    assert renderer.screenshot().get_at((160, 90))[:3] == (255, 0, 0)
    # Pending GL batches must flush before changing matrix uniforms.
    renderer.fill_rect(20, 30, 30, 20, "#0000FF")
    assert renderer.screenshot().get_at((30, 40))[:3] == (0, 0, 255)

    renderer.clear("white")
    renderer.transform_push(rotate)
    renderer.clip_push(20, 30, 40, 20)
    renderer.opacity_push(.5)
    renderer.fill_rect(20, 30, 80, 20, "black")
    renderer.opacity_pop()
    renderer.clip_pop()
    renderer.transform_pop()
    frame = renderer.screenshot()
    assert all(125 <= channel <= 130 for channel in frame.get_at((160, 40))[:3])
    assert frame.get_at((160, 90))[:3] == (255, 255, 255)

    renderer.clear("white")
    renderer.transform_push((2, 0, 0, .5, 20, 30))
    renderer.fill_rect(20, 30, 80, 20, "#FF0000")
    renderer.transform_pop()
    frame = renderer.screenshot()
    assert frame.get_at((120, 50))[:3] == (255, 0, 0)
    assert frame.get_at((120, 60))[:3] == (255, 255, 255)

    # A control outside the original framebuffer can rotate or translate into
    # view; a viewport-sized source layer would discard its pixels too early.
    renderer.clear("white")
    renderer.transform_push((0,1,-1,0,150,-400), bounds=(430,20,80,20))
    renderer.fill_rect(430,20,80,20,"#FF0000")
    renderer.transform_pop()
    assert renderer.screenshot().get_at((120,60))[:3] == (255,0,0)
    renderer.clear("white")
    with patch("pygame.Surface", side_effect=AssertionError("pure translation layer")):
        renderer.transform_push((1,0,0,1,-400,0))
        renderer.fill_rect(430,20,80,20,"#FF0000")
        renderer.transform_pop()
    assert renderer.screenshot().get_at((60,30))[:3] == (255,0,0)

    renderer.clear("white")
    renderer.transform_push(rotate)
    renderer.transform_push((1,0,0,1,-400,0))
    renderer.fill_rect(430,30,80,20,"#FF0000")
    renderer.transform_pop()
    renderer.transform_pop()
    assert renderer.screenshot().get_at((160,60))[:3] == (255,0,0)

    if renderer.native_shader:
        renderer.clear("white")
        shader = Shader(color="#FF0000", secondary_color="#0000FF", animate=False)
        shader._place(20, 30, 80, 20, renderer.scale)
        renderer.transform_push(rotate)
        with patch("pygame.Surface", side_effect=AssertionError("GPU subtree rasterization")):
            shader._draw_all(renderer)
        renderer.transform_pop()
        frame = renderer.screenshot()
        assert frame.get_at((160, 30)).r > 200
        assert frame.get_at((160, 90)).b > 200

    # Identity must leave batches and software bitmap allocation untouched.
    with patch("pygame.Surface", side_effect=AssertionError("identity layer allocation")):
        renderer.transform_push((1, 0, 0, 1, 0, 0))
        renderer.transform_pop()
    print(type(renderer).__name__, "affine shapes, texture UVs, alpha, clip, nested matrices: PASS")


def main():
    pygame.init()
    try:
        for backend in (st.Renderer.OPENGL, st.Renderer.VULKAN, st.Renderer.SOFTWARE):
            window = pygame.Window("Transform checks", size=(360, 240), hidden=True,
                                   opengl=backend is st.Renderer.OPENGL,
                                   vulkan=backend is st.Renderer.VULKAN)
            renderer = create_renderer(backend, window, vsync=False)
            try:
                check(renderer)
            finally:
                renderer.close()
                window.destroy()
        print("TRANSFORM RENDERER CHECKS PASS")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
