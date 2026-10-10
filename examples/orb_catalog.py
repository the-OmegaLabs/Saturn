"""All 13 Orb presets. Upstream: https://github.com/LerSent001/orb.

Copyright (c) 2026 LerSent001. MIT License: .static/shaders/ORB-LICENSE.txt.
"""
import json
import argparse
from pathlib import Path
import saturn as st
if __package__:
    from .effects_demo_common import configure, caption, heading, primary, BACKGROUND
else:
    from effects_demo_common import configure, caption, heading, primary, BACKGROUND

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / '.static/shaders'
PRESETS = {item['id']: item for item in json.loads((ASSETS/'orb-presets.json').read_text(encoding='utf-8'))}
PARTICLES = st.ShaderBuffer(ASSETS/'orb-ribbons.vert', ASSETS/'orb-ribbons.frag', instances=384*96*6)
COMMON = [('speed',0,3), ('radius',.3,.95), ('zoom',0,2), ('warp',0,6),
          ('ridgeAmt',0,1), ('sharp',.2,6), ('shade',0,1.5), ('exposure',0,3),
          ('glassOpacity',0,1), ('shellMidAlpha',0,1), ('shellEdgeAlpha',0,1),
          ('gloss',0,2), ('sheen',0,2), ('edgeSoftness',.0005,.1), ('edgeGlow',0,1)]
EXTRA = {
    'particleRibbon': [('particleDensity',.2,1), ('ribbonCount',2,6), ('ribbonWidth',.1,1),
        ('ribbonTwist',0,3), ('ribbonFold',0,1.2), ('ribbonBreath',0,1), ('particleSize',.6,3), ('particleBloom',0,2)],
    'chromaticMetal': [('metalScale',.1,2), ('metalStretch',0,1), ('metalAngle',0,180),
        ('metalOffset',-2,2), ('metalPhase',0,6), ('metalEvolution',0,3), ('metalRoughness',0,1), ('metalDepth',0,1)],
    'voiceWave': [('contourDeform',0,1)], 'blueDrop': [('contourDeform',0,1)],
    'violetEmber': [('contourDeform',0,1)], 'refractiveBlob': [('contourDeform',0,1)],
    'spectrum': [('bandDensity',.2,6), ('chromaticShift',0,1)],
}
COLORS = ['colorA','colorB','colorC','colorD','highlightColor','shellInner','shellMid',
          'shellEdge','sheenColor','specColor','canvasColor','glowColor']


def run_orb(builder, description, screens=('home',)):
    """Keep Orb's backend selection local to its two entry points."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--backend',choices=('opengl','vulkan','software'),default='opengl')
    parser.add_argument('--screen',choices=screens,default='home')
    args = parser.parse_args()
    def main(page):
        demo = builder(page)
        if args.screen != 'home':
            demo['open_screen'](args.screen)
    st.run(main,backend=st.Renderer(args.backend))


def rgba(hex_color):
    return tuple(int(hex_color[i:i+2],16)/255 for i in (1,3,5))+(1.,)


def orb_uniforms(preset='aurora'):
    """Fresh uniforms with upstream defaults; parameter names mirror Orb."""
    return {'orb_'+name: rgba(value) if isinstance(value,str) else float(value)
            for name,value in PRESETS[preset]['uniforms'].items()}


def apply_preset(shader, preset):
    shader.shader = ASSETS/('orb-particles.glsl' if preset=='particleRibbon' else 'orb-presets.glsl')
    shader.buffer = PARTICLES if preset=='particleRibbon' else None
    shader.uniforms = orb_uniforms(preset)


def build(page):
    configure(page, 'Saturn · Orb GLSL')
    error = st.Text('',color='#FFB4AB',size=12,max_lines=3)
    def show_error(message):
        error.value = message
        error.update()
    preview = st.Shader(shader=ASSETS/'orb-presets.glsl',uniforms=orb_uniforms(),
        height=390,fallback_color='#1A304B',on_error=lambda e:show_error(e.data))
    frame = st.Container(preview,bgcolor=PRESETS['aurora']['uniforms']['canvasColor'],height=390,border_radius=16)
    windows, saved = {}, {}
    current = ['aurora']
    preset = st.Dropdown(label='Orb preset',value='aurora',expand=True,
        options=[st.DropdownOption(key=key,text=item['name']) for key,item in PRESETS.items()])

    def editor(child):
        child.window.width, child.window.height = 390, 680
        child.padding = 20
        child.bgcolor = BACKGROUND
        child.horizontal_alignment = st.CrossAxisAlignment.STRETCH
        build_editor_controls(child)

    def build_editor_controls(child):
        key = current[0]
        def change(name):
            def handler(e):
                preview.uniforms['orb_'+name] = float(bool(e.control.value))
                preview.update()
            return handler
        controls = [st.Text(PRESETS[key]['name'],size=24),
            st.Switch(label='Glass shell',value=bool(preview.uniforms['orb_glassEnabled']),
                      on_change=change('glassEnabled'))]
        for name,low,high in COMMON+EXTRA.get(key,[]):
            label = caption(name)
            def handler(e, name=name, label=label):
                value = round(e.control.value) if name=='ribbonCount' else e.control.value
                preview.uniforms['orb_'+name] = float(value)
                label.value = f'{name} · {value:.3g}'
                label.update()
                preview.update()
            value = preview.uniforms['orb_'+name]
            label.value = f'{name} · {value:.3g}'
            controls += [label,st.Slider(value=value,min=low,max=high,on_change=handler)]
        for name in COLORS:
            value = preview.uniforms['orb_'+name]
            def color_change(e, name=name):
                text = e.control.value.strip()
                if len(text)==7 and text.startswith('#'):
                    try:
                        value = rgba(text)
                    except ValueError:
                        return
                    preview.uniforms['orb_'+name] = value
                    if name=='canvasColor':
                        frame.bgcolor = text
                        frame.update()
                    preview.update()
            controls.append(st.TextField(label=name,value='#'+''.join(f'{round(v*255):02X}' for v in value[:3]),
                                         on_change=color_change))
        child.add(st.ListView(controls=controls,spacing=8,expand=True),
                  st.TextButton('Close',on_click=lambda e:child.close()))

    def refresh_editor(child):
        if not child or child.closed:
            return
        child.clean()
        build_editor_controls(child)

    def select_preset(key):
        if key not in PRESETS:
            raise ValueError(f'Unknown Orb preset: {key}')
        saved[current[0]] = dict(preview.uniforms)
        current[0] = preset.value = key
        apply_preset(preview,key)
        if key in saved:
            preview.uniforms = dict(saved[key])
        frame.bgcolor = '#'+''.join(f'{round(v*255):02X}' for v in preview.uniforms['orb_canvasColor'][:3])
        error.value = ''
        page.update()
        child = windows.get('editor')
        if child and child.ready and not child.closed:
            refresh_editor(child)

    def reset():
        preview.uniforms = orb_uniforms(current[0])
        saved.pop(current[0],None)
        frame.bgcolor = PRESETS[current[0]]['uniforms']['canvasColor']
        page.update()
        child = windows.get('editor')
        if child and child.ready and not child.closed:
            refresh_editor(child)

    preset.on_select = lambda e:select_preset(e.control.value)
    def open_screen(name='editor'):
        child = windows.get('editor')
        if child is None or child.closed:
            child = page.open_subpage(editor,title='Orb parameters',anchor='right',offset=(12,0))
            windows['editor'] = child
        else:
            child.show()
            child.to_front()
        return child

    page.add(heading(page,'Orb GLSL','13 effects / GPU'),
        st.Row(preset,primary('Edit orb',lambda e:open_screen()),st.TextButton('Reset',on_click=lambda e:reset()),spacing=12),
        frame,error,caption('Orb · MIT · LerSent001. Particle Ribbons uses instanced GPU particles and glass refraction.'))
    return {'preview':preview,'windows':windows,'open_screen':open_screen,
            'preset':preset,'select_preset':select_preset,'reset':reset}
