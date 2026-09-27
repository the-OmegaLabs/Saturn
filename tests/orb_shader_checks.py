"""Render every Orb preset on actual GPUs, including the particle buffer."""
import hashlib
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
import saturn as st
from saturn.renderer import create_renderer
from examples.orb_catalog import ASSETS, PRESETS, apply_preset, orb_uniforms


def main(backend):
    pygame.init()
    window = pygame.Window('Orb checks',size=(320,320),hidden=True,
        opengl=backend is st.Renderer.OPENGL,vulkan=backend is st.Renderer.VULKAN)
    renderer = create_renderer(backend,window,vsync=False)
    try:
        shader = st.Shader(shader=ASSETS/'orb-presets.glsl',uniforms=orb_uniforms(),animate=False)
        shader._place(20,20,280,280,renderer.scale)
        def draw():
            renderer.clear('#000000')
            with patch('pygame.Surface',side_effect=AssertionError('CPU effect bitmap')), \
                 patch('pygame.image.tobytes',side_effect=AssertionError('CPU texture upload')):
                shader._draw_all(renderer)
                renderer.fill_rect(0,0,12,12,'#00FF00')
            assert shader.error is None, shader.error
            shot = renderer.screenshot()
            assert shot.get_at((5,5))[:3]==(0,255,0), 'Painter order changed'
            return shot
        hashes = set()
        directory=Path('.build-probe/orb-shots')
        directory.mkdir(parents=True,exist_ok=True)
        for key,item in PRESETS.items():
            apply_preset(shader,key)
            shader.time = 2.25
            first = draw()
            pixels = pygame.image.tobytes(first,'RGB')
            digest = hashlib.sha256(pixels).hexdigest()
            assert digest not in hashes, f'{key}: duplicated preset output'
            hashes.add(digest)
            # Require meaningful nonblack content inside the effect, not just a glass rim.
            energy = sum(sum(first.get_at((x,y))[:3]) for x in range(80,240,8) for y in range(80,240,8))
            assert energy>1500,(key,energy)
            shader.time = 3.25
            assert pixels!=pygame.image.tobytes(draw(),'RGB'), f'{key}: animation frozen'
            shader.time = 2.25
            shader.uniforms['orb_glassEnabled']=0.
            assert pixels!=pygame.image.tobytes(draw(),'RGB'), f'{key}: glass toggle has no effect'
            shader.uniforms['orb_glassEnabled']=1.
            if key=='particleRibbon':
                assert renderer._shader_buffers, 'No GPU particle target'
                target=next(iter(renderer._shader_buffers.values()))
                draw()
                assert next(iter(renderer._shader_buffers.values())) is target, 'Target reallocated every frame'
                shader.uniforms['orb_particleDensity']=.2
                assert pixels!=pygame.image.tobytes(draw(),'RGB'), 'Particle density ignored'
                shader.uniforms['orb_particleDensity']=1.
                shader._place(20,20,220,220,renderer.scale)
                draw()
                assert next(iter(renderer._shader_buffers.values()))[0] != target[0], 'Buffer resize ignored'
                shader._place(20,20,280,280,renderer.scale)
            pygame.image.save(first,str(directory/f'orb-{key}-{backend.value}.png'))
            print(f'{backend.value}: {item["name"]} PASS',flush=True)
        assert len(hashes)==13
        # Switching out of Particle Ribbons clears the buffer and returns to one pass.
        apply_preset(shader,'aurora')
        assert shader.buffer is None
        draw()
        print('All 13 unique presets, animation, glass, particle density, target reuse/resize and GPU-only draw PASS')
    finally:
        renderer.close()
        window.destroy()
        pygame.quit()


if __name__=='__main__':
    main(st.Renderer(sys.argv[1] if len(sys.argv)>1 else 'opengl'))
