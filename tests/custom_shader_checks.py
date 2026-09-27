"""User GLSL, uniforms, compilation failure recovery and composition on GPUs."""
import os
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
import saturn as st
from saturn.renderer import create_renderer
from saturn.renderer.shader_source import resolve_source

SOURCE = '''
#include "palette.glsl"
uniform vec3 tint;
uniform float gain;
uniform int mode;
uniform bool enabled;
vec4 mainImage(vec2 uv) {
    return vec4(enabled ? palette(uv) * tint * gain : vec3(float(mode)/10.0), 1.0);
}
'''


def main(backend):
    pygame.init()
    window = pygame.Window("Custom shader checks", size=(320,200), hidden=True,
                           opengl=backend is st.Renderer.OPENGL, vulkan=backend is st.Renderer.VULKAN)
    renderer = create_renderer(backend, window, vsync=False)
    try:
        empty = pygame.Surface((0, 16), pygame.SRCALPHA)
        renderer.blit_cached(empty, 0, 0)
        renderer.blit_tinted_scaled(empty, 0, 0, 0, 16, "white")
        shader = st.Shader(shader=SOURCE, includes={"palette.glsl": "vec3 palette(vec2 uv) { return vec3(uv, 1.0); }"},
            uniforms={"tint": (1,0,0), "gain": 1., "mode": 2, "enabled": True}, animate=False,
            width=200,height=120,border_radius=16)
        shader._place(20,20,200,120,renderer.scale)
        def draw():
            renderer.clear("white")
            with patch("pygame.Surface", side_effect=AssertionError("CPU effect bitmap")), patch("pygame.image.tobytes", side_effect=AssertionError("GPU upload")):
                shader._draw_all(renderer)
                renderer.fill_rect(230,20,40,40,"#00FF00")
            assert shader.error is None, shader.error
            return renderer.screenshot()
        shot = draw()
        assert 120<=shot.get_at((120,80)).r<=135 and shot.get_at((120,80)).g==0
        assert shot.get_at((20,20))[:3] == (255,255,255)
        assert shot.get_at((240,30))[:3] == (0,255,0)
        cache = renderer._custom_programs if hasattr(renderer,"_custom_programs") else renderer._custom_pipelines
        shader.uniforms["tint"] = (0,1,0)
        assert draw().get_at((120,80)).g >= 120 and len(cache)==1
        # Two instances sharing one program must retain different per-draw values.
        other = st.Shader(shader=SOURCE, includes=shader.includes,
                          uniforms={"tint": (0,0,1), "gain": 1., "mode": 2, "enabled": True}, animate=False)
        other._place(20,140,200,40,renderer.scale)
        renderer.clear("white")
        shader._draw_all(renderer)
        other._draw_all(renderer)
        shot=renderer.screenshot()
        assert shot.get_at((120,80)).g>=120 and shot.get_at((120,160)).b==255
        shader.uniforms["enabled"]=False
        assert all(49<=v<=53 for v in draw().get_at((120,80))[:3])
        shader.shader = 'vec4 mainImage(vec2 uv) { this_is_invalid; return vec4(1); }'
        renderer.clear("white")
        shader._draw_all(renderer)
        assert shader.error
        shader.shader = 'vec4 mainImage(vec2 uv) { return vec4(uv, sin(u_time)*.5+.5, 1); }'
        shader.uniforms = {}
        shader.time = 0
        first=draw()
        shader.time = 1.5
        assert pygame.image.tobytes(first,"RGB") != pygame.image.tobytes(draw(),"RGB")
        shader.shader = 'void mainImage(out vec4 color, in vec2 pixel) { color=vec4(pixel/iResolution.xy,0,1); }'
        assert 120<=draw().get_at((120,80)).g<=135
        window.size=(360,240)
        renderer.on_resize(360,240,pixel_size=(360,240),pixel_ratio=1)
        assert draw().get_size()==(360,240)
        try:
            resolve_source('#include "a"', {"a": '#include "a"'})
        except ValueError:
            pass
        else:
            raise AssertionError("Include cycles accepted")
        print(f"{backend.value}: GLSL, includes, uniforms, ordering, cache, recovery, time and resize OK")
    finally:
        renderer.close()
        window.destroy()
        pygame.quit()


if __name__ == "__main__":
    main(st.Renderer(sys.argv[1] if len(sys.argv)>1 else 'opengl'))
