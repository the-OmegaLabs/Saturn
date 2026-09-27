"""Native GPU procedural fragments, composition, animation, and fallback checks.

Run with ``python -m tests.shader_checks`` on a desktop with Vulkan/OpenGL.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pygame

import saturn as st
from saturn.renderer import create_renderer
from saturn.widgets.shader import Shader, ShaderEffect


ROOT = Path(__file__).resolve().parents[1]


def new_renderer(backend):
    window = pygame.Window("Shader checks", size=(360, 240), hidden=True,
                           opengl=backend is st.Renderer.OPENGL,
                           vulkan=backend is st.Renderer.VULKAN)
    return window, create_renderer(backend, window, vsync=False)


def draw(renderer, shader):
    renderer.clear("white")
    with (patch("pygame.Surface", side_effect=AssertionError("CPU effect bitmap")),
          patch("pygame.image.tobytes", side_effect=AssertionError("effect texture upload"))):
        shader._draw_all(renderer)
    return renderer.screenshot()


def native_checks(renderer, window):
    assert renderer.native_shader
    shader = Shader(ShaderEffect.GRADIENT, color="#FF0000", secondary_color="#0000FF",
                    animate=False, border_radius=16, width=200, height=120)
    shader._place(20, 20, 200, 120, renderer.scale)
    frame = draw(renderer, shader)
    left, right = frame.get_at((40, 80)), frame.get_at((200, 80))
    assert left.r > 200 and left.b < 55, left
    assert right.b > 200 and right.r < 55, right
    assert frame.get_at((20, 20))[:3] == (255, 255, 255)
    assert frame.get_at((19, 80))[:3] == (255, 255, 255)
    assert frame.get_at((220, 80)).r >= 200  # Feather at the last pixel is bounded.

    textures_before = len(getattr(renderer, "_gpu_tex_cache", getattr(renderer, "_tex_cache", {})))
    images = []
    for effect in ShaderEffect:
        shader.effect = effect
        shader.time = 0
        first = draw(renderer, shader)
        shader.time = 1.5
        second = draw(renderer, shader)
        assert pygame.image.tobytes(first, "RGBA") != pygame.image.tobytes(second, "RGBA"), effect
        images.append(first)
    textures_after = len(getattr(renderer, "_gpu_tex_cache", getattr(renderer, "_tex_cache", {})))
    assert textures_before == textures_after
    assert not getattr(renderer, "_pending_textures", ())

    # The shader participates in the same alpha, translation, and clip stacks.
    shader.effect = ShaderEffect.GRADIENT
    shader.color = shader.secondary_color = "black"
    shader.border_radius = 0
    shader.opacity = .5
    renderer.clear("white")
    renderer.clip_push(40, 40, 30, 30)
    renderer.translate_push(20, 20)
    shader._draw_all(renderer)
    renderer.translate_pop()
    renderer.clip_pop()
    frame = renderer.screenshot()
    assert all(125 <= channel <= 130 for channel in frame.get_at((55, 55))[:3])
    assert frame.get_at((75, 55))[:3] == (255, 255, 255)
    assert frame.get_at((35, 55))[:3] == (255, 255, 255)

    # Color alpha is interpolated before normal compositing; transparent blue
    # must not create a blue fringe around a half-transparent red gradient.
    shader.opacity = 1
    shader.color = (255, 0, 0, 255)
    shader.secondary_color = (0, 0, 255, 0)
    frame = draw(renderer, shader)
    center = frame.get_at((120, 80))
    assert center.r >= 250 and 120 <= center.g <= 135 and 120 <= center.b <= 135, center

    # Later controls retain painter order, and hiding a shader clears its old pixels.
    renderer.clear("white")
    shader._draw_all(renderer)
    renderer.fill_rect(100, 50, 40, 40, (0, 255, 0, 255))
    assert renderer.screenshot().get_at((120, 70))[:3] == (0, 255, 0)
    shader.visible = False
    assert draw(renderer, shader).get_at((120, 80))[:3] == (255, 255, 255)
    shader.visible = True

    window.size = (400, 280)
    renderer.on_resize(400, 280, pixel_size=(400, 280), pixel_ratio=1)
    assert draw(renderer, shader).get_size() == (400, 280)

    output = ROOT / ".build-probe" / f"shaders-{type(renderer).__name__}.png"
    output.parent.mkdir(exist_ok=True)
    collage = pygame.Surface((400, 240))
    for index, image in enumerate(images):
        collage.blit(image, ((index % 2) * 200, (index // 2) * 120),
                     (20, 20, 200, 120))
    pygame.image.save(collage, output)
    print(type(renderer).__name__, "procedural fragments, alpha/clip/resize: PASS")


def animation_checks():
    shader = Shader("plasma")
    shader.page = SimpleNamespace(_app=SimpleNamespace(renderer=SimpleNamespace(native_shader=True)))
    assert shader._tick_animations(shader._started + 1)
    assert shader._elapsed == 1
    shader.animate = False
    assert not shader._tick_animations(shader._started + 2)
    assert shader._elapsed == 1
    shader.animate = True
    shader.parent = SimpleNamespace(visible=False, parent=None)
    assert not shader._tick_animations(shader._started + 3)
    shader.parent = None
    shader.page._app.renderer.native_shader = False
    assert not shader._tick_animations(shader._started + 4)

    for kwargs in ({"effect": "missing"}, {"uniforms": {"typo": 2}},
                   {"uniforms": {"intensity": 2}}, {"uniforms": {"frequency": 0}},
                   {"uniforms": {"center": (2, 0)}}, {"speed": float("inf")},
                   {"time": float("nan")}, {"border_radius": -1}):
        try:
            Shader(**kwargs)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(kwargs)


def main():
    pygame.init()
    try:
        animation_checks()
        for backend in (st.Renderer.OPENGL, st.Renderer.VULKAN, st.Renderer.SOFTWARE):
            window, renderer = new_renderer(backend)
            try:
                if renderer.native_shader:
                    native_checks(renderer, window)
                else:
                    shader = Shader("plasma", fallback_color="#123456", animate=True)
                    shader._place(10, 10, 100, 100, renderer.scale)
                    renderer.clear("white")
                    shader._draw_all(renderer)
                    assert renderer.screenshot().get_at((50, 50))[:3] == (18, 52, 86)
                    print("SoftwareRenderer static fallback: PASS")
            finally:
                renderer.close()
                window.destroy()
        print("SHADER CHECKS PASS")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
