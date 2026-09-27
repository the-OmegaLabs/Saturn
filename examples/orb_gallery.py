"""Display all 13 MIT-licensed Orb GLSL effects together."""
import saturn as st
if __package__:
    from .orb_catalog import ASSETS, PRESETS, PARTICLES, orb_uniforms, run_orb
    from .effects_demo_common import configure, heading, caption
else:
    from orb_catalog import ASSETS, PRESETS, PARTICLES, orb_uniforms, run_orb
    from effects_demo_common import configure, heading, caption


def build(page):
    configure(page,'Saturn · All Orb effects')
    page.window.width,page.window.height=1120,1020
    shaders, tiles = [], []
    for key,item in PRESETS.items():
        particle=key=='particleRibbon'
        shader=st.Shader(shader=ASSETS/('orb-particles.glsl' if particle else 'orb-presets.glsl'),
            uniforms=orb_uniforms(key),buffer=PARTICLES if particle else None,height=160)
        shaders.append(shader)
        tiles.append(st.Container(st.Column(shader,caption(item['name']),spacing=6,
            horizontal_alignment=st.CrossAxisAlignment.STRETCH),expand=True,
            bgcolor=item['uniforms']['canvasColor'],padding=10,border_radius=12))
    rows=[]
    for start in range(0,len(tiles),4):
        group=tiles[start:start+4]
        group += [st.Container(expand=True) for _ in range(4-len(group))]
        rows.append(st.Row(*group,height=204,spacing=12))
    page.add(heading(page,'All Orb effects','13 GLSL presets / GPU'),
        st.ListView(controls=rows,spacing=12,expand=True),
        caption('Orb · Copyright (c) 2026 LerSent001 · MIT. Open orb_glsl.py to edit individual parameters.'))
    return {'shaders':shaders}


if __name__=='__main__':
    run_orb(build,'All 13 Orb effects',('home',))
