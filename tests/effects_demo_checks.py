"""Run native-window demos and actual GLSL previews on each renderer."""
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
import saturn as st
from saturn.event import fire
from examples import subpage_settings, shader_gallery, shader_playground, orb_glsl


def run(backend,module):
    app=st.App(lambda p:None,backend)
    app.start()
    app._window.hide()
    app.call=lambda fn,*args:fn(*args)
    app.configure_renderer(vsync=False)
    def pump(predicate=lambda:True):
        deadline=time.perf_counter()+5
        while True:
            app._pump_once()
            if predicate(): return
            assert time.perf_counter()<deadline
            time.sleep(.01)
    try:
        demo=module.build(app.page)
        pump()
        if module is subpage_settings:
            demo["open_screen"]("settings")
            pump(lambda:demo["windows"]["settings"].ready and bool(demo["windows"]["settings"].controls))
            child=demo["windows"]["settings"]
            field=next(c for c in child.controls if isinstance(c,st.TextField))
            field.value="Test workspace"
            fire(field,"change")
            pump(lambda:demo["state"]["name"]=="Test workspace")
            assert demo["state"]["name"]=="Test workspace"
            demo["open_screen"]("appearance")
            pump(lambda:demo["windows"]["appearance"].ready)
            assert demo["windows"]["appearance"].parent_page is child
            child.hide()
            pump()
            demo["open_screen"]("settings")
            pump()
            assert child.window.visible and field.value=="Test workspace"
        elif module is shader_gallery:
            demo["palette"].value="violet"
            fire(demo["palette"],"select")
            assert all(s.color=="#392554" for s in demo["shaders"])
            demo["reset"]()
        else:
            child=demo["open_screen"]("editor")
            pump(lambda:child.ready and bool(child.controls))
            shader=demo["preview"]
            if module is orb_glsl:
                assert shader.error is None,shader.error
                app._activate()
                app.page.draw()
                shot=app.renderer.screenshot()
                if backend is not st.Renderer.SOFTWARE:
                    x,y,w,h=shader._rect
                    center=shot.get_at((round(x+w/2),round(y+h/2)))
                    assert max(center[:3])-min(center[:3])>20,center
                    shader.uniforms["glass"]=False
                    shader.update()
                    pump()
                    app._activate()
                    app.page.draw()
                    other=app.renderer.screenshot()
                    assert pygame.image.tobytes(shot,"RGB")!=pygame.image.tobytes(other,"RGB")
                    shader.uniforms["glass"]=True
                    shader.update()
            else:
                slider=next(c for c in child.controls if isinstance(c,st.Slider))
                slider.value=1.8
                fire(slider,"change")
                pump(lambda:shader.speed==1.8)
                assert shader.speed==1.8
        pump()
        if backend is st.Renderer.VULKAN:
            directory=Path('.static/shots')
            directory.mkdir(parents=True,exist_ok=True)
            for target,suffix in ((app,"main"), *((c, f"child-{i}") for i,c in enumerate(app._children))):
                target._activate()
                target.page.draw()
                pygame.image.save(target.renderer.screenshot(),str(directory/f'{module.__name__.split(".")[-1]}-{suffix}-vulkan.png'))
        print(backend.value,module.__name__,"PASS")
    finally:
        app.close()
        app.run_until_closed()


if __name__=="__main__":
    backend=st.Renderer(sys.argv[1] if len(sys.argv)>1 else 'opengl')
    for module in (subpage_settings,shader_gallery,shader_playground,orb_glsl):
        run(backend,module)
