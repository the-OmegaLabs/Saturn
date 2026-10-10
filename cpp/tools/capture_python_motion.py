"""Render actual Python controls at fixed times for comparison with C++ OpenGL."""
from __future__ import annotations
import argparse
import ctypes
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    if sys.platform == "win32":
        ctypes.windll.shcore.SetProcessDpiAwareness(0)
    import pygame
    import saturn
    from saturn import colors
    from saturn.renderer.gl import GLRenderer
    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION,3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION,3)
    window = pygame.Window("Python animation verification",size=(640,480),opengl=True,hidden=True)
    renderer = GLRenderer(window,logical_size=(640,480),vsync=False)
    colors.theme_dark = True
    colors.apply_seed(None)
    page = SimpleNamespace(
        width=640,height=480,overlay=[],_active_animations=set(),
        _control_enabled=lambda c: c.visible and not c.disabled,
        update=lambda: None,repaint=lambda: None,
        _reconcile_branch=lambda control: None,
        _app=SimpleNamespace(renderer=renderer,mark_dirty=lambda: None,
                             call=lambda fn,*a,**kw: fn(*a,**kw),
                             post=lambda fn: None,set_text_input_rect=lambda rect: None))
    def save(name):
        pygame.image.save(renderer.screenshot(),str(out/name))
    def tick(control,time):
        control._tick_animations(time)
        for child in control._children():
            tick(child,time)
    try:
        with patch("time.perf_counter",return_value=10.0),patch("threading.Timer",MagicMock()):
            button = saturn.FilledButton("Filled")
            checkbox = saturn.Checkbox("agree")
            switch = saturn.Switch()
            slider = saturn.Slider(min=0,max=100,divisions=10)
            field = saturn.TextField(label="Name")
            menu = saturn.Dropdown(hint_text="dropdown...",width=180,
                options=[saturn.Option(k,text=t) for k,t in (("a","Alpha"),("b","Beta"),("g","Gamma"))])
            listing = saturn.ListView(controls=[
                saturn.Container(saturn.Text(f"list item {i}",size=13,color=colors.Colors.ON_SURFACE),
                    padding=8,border_radius=6,bgcolor=colors.Colors.SURFACE_CONTAINER_LOW if i%2 else colors.Colors.SURFACE_CONTAINER)
                for i in range(30)],spacing=4,width=180,height=180)
            controls = [button,checkbox,switch,slider,field,menu,listing]
            rects = [(24,24,120,40),(24,100,100,40),(200,100,52,40),
                     (24,164,300,48),(24,244,300,56),(360,244,180,56),(360,24,180,180)]
            for control,rect in zip(controls,rects):
                control._attach(page)
                control._place(*rect,renderer.scale)
            button._set_hover(True); button._pressed_hook(30,44)
            checkbox._pressed_hook(33,120); checkbox._released_hook(33,120); checkbox._toggle()
            switch.value = True; switch._animate_value(True)
            slider.value = 50; slider._pressed_hook(174,188)
            field._set_hover(True); field._set_focused(True)
            listing._wheel(80); menu._toggle_menu()
        for ms in (0,15,50,75,100,150,200,250,300,330,375,400,449,500,600,850):
            now = 10+ms/1000
            with patch("time.perf_counter",return_value=now),patch("threading.Timer",MagicMock()):
                for control in controls: tick(control,now)
                if ms == 300:
                    button._released_hook(30,44)
                    checkbox.value = False; checkbox._animate_value(False)
                    switch.value = False; switch._animate_value(False)
                    slider._released_hook(174,188)
                    field._set_focused(False); field._set_hover(False)
                    menu._close_menu()
                renderer.clear(colors.parse_color(colors.Colors.SURFACE))
                for control in controls: control._draw_all(renderer)
                for overlay in page.overlay: overlay._draw_all(renderer)
                save(f"controls-{ms}.png")
        for kind in ("dialog","snack"):
            page.overlay.clear()
            with patch("time.perf_counter",return_value=10.0),patch("threading.Timer",MagicMock()):
                if kind == "dialog":
                    overlay = saturn.AlertDialog(title="Confirm",
                        content=saturn.Text("Delete this item permanently?"),
                        actions=[saturn.TextButton("Cancel"),saturn.FilledButton("Delete")])
                else:
                    overlay = saturn.SnackBar("Saved!",action="Undo")
                overlay._attach(page)
                overlay._place(0,0,640,480,renderer.scale)
                overlay._shown()
            for ms in (0,30,75,150,225,300,330,375,450,500):
                now = 10+ms/1000
                with patch("time.perf_counter",return_value=now),patch("threading.Timer",MagicMock()):
                    tick(overlay,now)
                    if ms == 300: overlay._begin_dismiss(page)
                    renderer.clear(colors.parse_color(colors.Colors.SURFACE))
                    overlay._draw_all(renderer)
                    save(f"{kind}-{ms}.png")
        print(f"captured 36 Python OpenGL frames in {out}")
    finally:
        renderer.close()
        window.destroy()
        pygame.quit()

if __name__ == "__main__":
    main()
