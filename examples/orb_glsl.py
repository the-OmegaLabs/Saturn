"""Orb Aurora GLSL adaptation, with an owned native parameter editor.

Source: https://github.com/LerSent001/orb
Copyright (c) 2026 LerSent001. MIT License: .static/shaders/ORB-LICENSE.txt.

python examples/orb_glsl.py --backend opengl --screen editor
Vulkan custom GLSL requires glslangValidator on PATH, or SATURN_GLSLANG.
"""
from pathlib import Path
import saturn as st
if __package__:
    from .effects_demo_common import configure, caption, heading, primary, run_example, BACKGROUND
else:
    from effects_demo_common import configure, caption, heading, primary, run_example, BACKGROUND

ROOT=Path(__file__).resolve().parents[1]

def orb_uniforms():
    return dict(orb_radius=.83, zoom=1.0, warp=2.0, ridge=.45, shade=.35,
                exposure=1.1, refraction=.42, refraction_width=.15,
                gloss=.8, rim_width=.4, sheen=.7, glass=True,
                color_a=(.015,.03,.12), color_b=(.12,.7,.55),
                color_c=(.1,.4,.95), color_d=(.65,.18,.8))

def build(page):
    configure(page,"Saturn · Orb GLSL")
    error=st.Text("",color="#FFB4AB",size=12,max_lines=3)
    preview=st.Shader(shader=ROOT/".static/shaders/orb-aurora.glsl",uniforms=orb_uniforms(),
                      height=420,speed=.7,fallback_color="#1A304B",
                      on_error=lambda e: show_error(e.data))
    windows={}
    def show_error(message):
        error.value=message
        error.update()
    def editor(child):
        child.window.width,child.window.height=380,650
        child.padding=20
        child.bgcolor=BACKGROUND
        child.horizontal_alignment=st.CrossAxisAlignment.STRETCH
        def change(name):
            def handler(e):
                preview.uniforms[name]=e.control.value
                preview.update()
            return handler
        child.add(st.Text("Orb parameters",size=24),
                  st.Switch(label="Glass shell",value=True,on_change=change("glass")))
        for name,low,high in (("refraction",0,1),("refraction_width",0,1),
                              ("zoom",.2,2),("warp",0,5),("exposure",.2,2)):
            child.add(caption(name.replace("_"," ").title()),
                      st.Slider(value=preview.uniforms[name],min=low,max=high,on_change=change(name)))
        child.add(st.TextButton("Close",on_click=lambda e: child.close()))
    def open_screen(name="editor"):
        child=windows.get("editor")
        if child is None or child.closed:
            child=page.open_subpage(editor,title="Orb parameters",anchor="right",offset=(12,0))
            windows["editor"]=child
        else:
            child.show()
            child.to_front()
        return child
    page.add(heading(page,"Aurora glass orb","User GLSL / include"),preview,
             primary("Edit orb",lambda e: open_screen()),error,
             caption("Aurora and glass-shell adaptation of Orb · MIT · LerSent001. No particle ribbon."))
    return {"preview":preview,"windows":windows,"open_screen":open_screen}

if __name__=="__main__":
    run_example(build,"Orb Aurora GLSL adaptation",("home","editor"))
