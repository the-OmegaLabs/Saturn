"""Integrated transformed control rendering and pointer coordinate checks."""
from __future__ import annotations

import math

import pygame

import saturn as st
from saturn.renderer import create_renderer


def near(point, expected):
    assert all(abs(actual-target) < 1e-6 for actual, target in zip(point, expected)), (point,expected)


def check(renderer):
    box = st.Container(width=80,height=20,bgcolor="#FF0000",rotate=math.pi/2,
                       on_click=lambda event: None)
    box._place(20,30,80,20,renderer.scale)
    renderer.clear("white")
    box._draw_all(renderer)
    frame = renderer.screenshot()
    assert frame.get_at((60,10))[:3] == (255,0,0)
    assert frame.get_at((30,40))[:3] == (255,255,255)
    assert box._hit_test(60,10) is box
    assert box._hit_test(30,40) is None
    near(box._screen_point(30,40),(60,10))
    near(box._event_point(60,10),(30,40))

    # Separate scale/rotation pivots and nested controls compose parent * child.
    child = st.Container(bgcolor="#FF0000",on_click=lambda event: None,
                         scale=st.Scale(scale_x=2,scale_y=.5,alignment=st.Alignment.TOP_LEFT))
    parent = st.Container(child,bgcolor="#0000FF",rotate=math.pi/2)
    parent._rect = (20,20,180,140)
    child._rect = (40,50,60,20)
    parent._attach(None)
    renderer.clear("white")
    parent._draw_all(renderer)
    assert renderer.screenshot().get_at((145,80))[:3] == (255,0,0)
    assert parent._hit_test(145,80) is child
    near(child._screen_point(70,60),(145,80))
    near(child._event_point(145,80),(70,60))

    child.offset = st.Offset(.5,-.25)
    renderer.clear("white")
    parent._draw_all(renderer)
    assert renderer.screenshot().get_at((150,110))[:3] == (255,0,0)
    assert parent._hit_test(150,110) is child
    near(child._screen_point(70,60),(150,110))
    near(child._event_point(150,110),(70,60))

    box.rotate = None
    box.scale = st.Scale(scale=2,transform_hit_tests=False)
    renderer.clear("white")
    box._draw_all(renderer)
    assert renderer.screenshot().get_at((5,40))[:3] == (255,0,0)
    assert box._hit_test(5,40) is None
    assert box._hit_test(60,40) is box
    box.scale = 0
    assert box._hit_test(60,40) is None

    # A custom Container._draw_all must shift its transform pivot by the same
    # scroll displacement as its geometry. Pointer round trips use layout space.
    rows = [st.Container(height=20) for _ in range(20)]
    row = rows[8]
    row.bgcolor = "#FF0000"
    row.rotate = math.pi/2
    row.on_click = lambda event: None
    listing = st.ListView(controls=rows,item_extent=20,width=160,height=100,scroll="none")
    listing._attach(None)
    listing._place(20,20,160,100,renderer.scale)
    listing._offset = 140
    renderer.clear("white")
    listing._draw_all(renderer)
    assert renderer.screenshot().get_at((100,60))[:3] == (255,0,0)
    assert listing._hit_test(100,60) is row
    near(row._screen_point(100,190),(100,50))
    near(row._event_point(100,60),(110,190))
    print(type(renderer).__name__, "control transforms, hit flags, scroll pivots, coordinate round trips: PASS")


def main():
    pygame.init()
    try:
        for backend in (st.Renderer.OPENGL,st.Renderer.VULKAN,st.Renderer.SOFTWARE):
            window = pygame.Window("Control transform checks",size=(360,240),hidden=True,
                                   opengl=backend is st.Renderer.OPENGL,
                                   vulkan=backend is st.Renderer.VULKAN)
            renderer = create_renderer(backend,window,vsync=False)
            try:
                check(renderer)
            finally:
                renderer.close()
                window.destroy()
        print("CONTROL TRANSFORM CHECKS PASS")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
