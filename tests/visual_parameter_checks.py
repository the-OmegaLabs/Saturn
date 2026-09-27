"""Real layout and pixel checks for the native visual parameter adapters."""
from pathlib import Path
from types import SimpleNamespace
import io
import inspect
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
import flet
import saturn as st
from saturn.renderer.software import SoftwareRenderer


def pixel(renderer,x,y):
    return tuple(renderer.screenshot().get_at((x,y)))[:3]


def render(renderer,control,rect):
    renderer.clear("#000000")
    control._place(*rect,renderer.scale)
    control._draw_all(renderer)


def check_layout(renderer):
    # Proportional tight flex ignores differing intrinsic widths. Loose flex
    # may use less than its allocated maximum, leaving space for alignment.
    tight_children = [st.Container(width=10,height=10,expand=1),st.Container(width=60,height=10,expand=2)]
    tight = st.Row(controls=tight_children,spacing=0)
    tight._place(0,0,90,10,1)
    assert [c._rect[2] for c in tight_children] == [30,60]
    loose_children = [st.Container(width=10,height=10,expand=1,expand_loose=True),
                      st.Container(width=40,height=10,expand=1,expand_loose=True)]
    loose = st.Row(controls=loose_children,spacing=0,alignment=st.MainAxisAlignment.CENTER)
    loose._place(0,0,100,10,1)
    assert [c._rect[2] for c in loose_children] == [10,40]
    assert [c._rect[0] for c in loose_children] == [25,35]
    vertical = st.Column(controls=[st.Container(height=10,expand=1),st.Container(height=70,expand=1)],spacing=0)
    vertical._place(0,0,30,100,1)
    assert [c._rect[3] for c in vertical.controls] == [50,50]
    vertical.controls[0].expand_loose = True
    vertical._place(0,0,30,100,1)
    assert [c._rect[3] for c in vertical.controls] == [10,50]
    children = [st.Container(width=60,height=20) for _ in range(4)]
    row = st.Row(controls=children,wrap=True,spacing=10,run_spacing=7)
    assert row._intrinsic(130,None,1) == (130,47)
    row._place(0,0,130,47,1)
    assert [c._rect for c in children] == [(0,0,60,20),(70,0,60,20),(0,27,60,20),(70,27,60,20)]
    column = st.Column(controls=children,wrap=True,spacing=10,run_spacing=8)
    column._place(0,0,128,50,1)
    assert children[2]._rect[:2] == (68,0)
    row = st.Row(controls=[st.Container(width=10,height=10),st.Container(width=10,height=10)],
                 alignment=st.MainAxisAlignment.SPACE_AROUND,spacing=10)
    row._place(0,0,100,10,1)
    assert [c._rect[0] for c in row.controls] == [17.5,72.5]
    rtl = st.Row(controls=[st.Container(width=10,height=10)],rtl=True)
    rtl._place(0,0,100,10,1)
    assert rtl.controls[0]._rect[0] == 90
    scrolling = st.Column(controls=[st.Container(height=40,bgcolor="#ff0000") for _ in range(6)],scroll=st.ScrollMode.ALWAYS)
    scrolling._place(0,0,80,80,renderer.scale)
    scrolling.scroll_to(60)
    assert scrolling._scroll_view._offset == 60
    child = st.Container(width=30,height=30,bgcolor="#ff0000",left=35,top=0)
    stack = st.Stack(controls=[child])
    render(renderer,stack,(0,0,40,40))
    assert pixel(renderer,38,10)[0] > 150
    assert pixel(renderer,50,10) == (0,0,0)
    stretch = st.Container(left=5,right=7,top=3,bottom=9)
    st.Stack(controls=[stretch])._place(0,0,100,80,1)
    assert stretch._rect == (5,3,88,68)


def check_buttons(renderer):
    style = st.ButtonStyle(bgcolor={st.ControlState.DEFAULT:"#ff0000",st.ControlState.DISABLED:"#0000ff"},
                           color="#ffffff",padding=st.Padding.all(4),
                           alignment=st.Alignment.CENTER_LEFT,
                           shape=st.RoundedRectangleBorder(radius=2),
                           side=st.BorderSide(2,"#00ff00"))
    button = st.FilledButton("Hello",style=style)
    render(renderer,button,(0,0,100,40))
    assert pixel(renderer,90,20)[0] > 200
    button.disabled = True
    render(renderer,button,(0,0,100,40))
    assert pixel(renderer,90,20)[2] > 200
    label = st.Container(width=12,height=8,bgcolor="#00ff00")
    icon = st.Container(width=10,height=10,bgcolor="#ff0000")
    button = st.Button(label,icon=icon,style=st.ButtonStyle(padding=4))
    render(renderer,button,(0,0,100,40))
    assert label._rect[0] > icon._rect[0]+icon._rect[2]
    assert pixel(renderer,round(icon._rect[0])+4,20)[0] > 150
    icon_button = st.IconButton(icon=icon,selected_icon=label,selected=True,padding=12,
                                size_constraints=st.BoxConstraints(min_width=56,min_height=56))
    assert icon_button._intrinsic(None,None,1) == (56,56)
    render(renderer,icon_button,(0,0,56,56))
    assert pixel(renderer,28,28)[1] > 150
    calls=[]
    button.page = SimpleNamespace(_app=SimpleNamespace(call=lambda fn,*args:fn(*args)))
    button.on_click = lambda event: calls.append(event.control)
    button._key(SimpleNamespace(key=pygame.K_SPACE))
    assert calls == [button]


def image_source():
    source = pygame.Surface((20,10),pygame.SRCALPHA)
    source.fill("red")
    source.fill("blue",(10,0,10,10))
    buffer=io.BytesIO()
    pygame.image.save(source,buffer,"fixture.png")
    return buffer.getvalue()


def check_images(renderer):
    source=image_source()
    image=st.Image(source,fit=st.BoxFit.CONTAIN)
    render(renderer,image,(0,0,20,20))
    assert pixel(renderer,5,2) == (0,0,0)
    assert pixel(renderer,5,10)[0] > 150
    image.fit=st.BoxFit.COVER
    render(renderer,image,(0,0,20,20))
    assert pixel(renderer,3,2)[0] > 150 and pixel(renderer,16,2)[2] > 150
    assert pixel(renderer,25,10) == (0,0,0)
    image=st.Image(source,fit=st.BoxFit.NONE,repeat=st.ImageRepeat.REPEAT,border_radius=6)
    render(renderer,image,(0,0,60,30))
    assert pixel(renderer,0,0) == (0,0,0)
    assert pixel(renderer,5,15) != (0,0,0)
    decorated=image._decorated_surface
    render(renderer,image,(0,0,60,30))
    assert image._decorated_surface is decorated
    fallback=st.Image("missing-visual-check-fixture.png",error_content=st.Container(bgcolor="#00ff00",width=20,height=20))
    render(renderer,fallback,(0,0,20,20))
    assert pixel(renderer,10,10)[1] > 150


def check_list(renderer):
    children=[st.Container(height=10+i,bgcolor="#ff0000") for i in range(12)]
    listing=st.ListView(controls=children,prototype_item=st.Container(height=24),divider_thickness=2,
                        reverse=True,cache_extent=40,scroll=st.ScrollMode.ALWAYS)
    render(renderer,listing,(0,0,100,70))
    assert all(c._rect[3] == 24 for c in children)
    assert listing._content_size == 12*26-2
    assert listing._offset == listing._max_offset()
    listing.scroll_to(10)
    assert listing._offset == listing._max_offset()-10
    listing.scroll_to(-1)
    assert listing._offset == 0
    listing.build_controls_on_demand=False
    listing._place(0,0,100,70,renderer.scale)
    assert len(listing._lazy_layout_version) == 12
    short=st.ListView(controls=[st.Container(height=20),st.Container(height=20)],reverse=True)
    short._place(0,0,100,100,renderer.scale)
    assert short.controls[0]._rect[1] == 80 and short.controls[1]._rect[1] == 60
    short._place(0,0,100,120,renderer.scale)
    assert short.controls[0]._rect[1] == 100 and short.controls[1]._rect[1] == 80


def check_decorations(renderer):
    gradient=st.LinearGradient(begin=st.Alignment.CENTER_LEFT,end=st.Alignment.CENTER_RIGHT,colors=["#ff0000","#0000ff"])
    box=st.Container(gradient=gradient,border_radius=6)
    render(renderer,box,(0,0,80,40))
    assert pixel(renderer,10,20)[0] > 150 and pixel(renderer,70,20)[2] > 150
    surface=box._gradient_surface
    render(renderer,box,(0,0,80,40))
    assert box._gradient_surface is surface
    dialog=st.AlertDialog(title="Title",content=st.Text("Body"),icon=st.Icons.SETTINGS,
                          actions=[st.TextButton("OK")],title_padding=8,content_padding=8,
                          actions_padding=8,inset_padding=10,barrier_color="#660000ff")
    dialog._reveal=dialog._timeline=1
    render(renderer,dialog,(0,0,320,200))
    assert dialog._card_rect[3] <= 180
    assert dialog.actions[0]._rect[0] > dialog._card_rect[0]+100
    events=[]
    snack=st.SnackBar("Saved",action="Undo",show_close_icon=True,behavior="floating",padding=8,on_visible=lambda _:events.append("visible"))
    snack.page=SimpleNamespace(_app=SimpleNamespace(call=lambda fn,*args:fn(*args),mark_dirty=lambda:None))
    snack._place(0,0,320,200,renderer.scale)
    action=snack._action_btn
    snack._place(0,0,320,200,renderer.scale)
    assert snack._action_btn is action
    snack._shown()
    assert events == ["visible"]
    snack._reveal=1
    renderer.clear("#000000")
    snack._draw_all(renderer)
    bar=st.ProgressBar(.5,track_gap=8,stop_indicator_color="#ff0000",stop_indicator_radius=2)
    render(renderer,bar,(0,0,100,8))
    assert pixel(renderer,53,4) == (0,0,0)
    assert pixel(renderer,98,4)[0] > 150
    ring=st.ProgressRing(.4,stroke_align=-1,stroke_cap=st.StrokeCap.BUTT,padding=4,
                         size_constraints=st.BoxConstraints(min_width=50))
    assert ring._intrinsic(None,None,1) == (50,48)
    render(renderer,ring,(0,0,50,50))


def check_gestures_and_fab(renderer):
    events=[]
    stub=SimpleNamespace(_app=SimpleNamespace(call=lambda fn,*args:fn(*args),mark_dirty=lambda:None),
                         _pointer_pos=(20,20),_click_count=1)
    gesture=st.GestureDetector(on_pan_start=lambda e:events.append((e.name,e.local_position.x)),
                              on_pan_update=lambda e:events.append((e.name,e.delta_x)),
                              on_pan_end=lambda e:events.append((e.name,e.velocity.x)),
                              on_scroll=lambda e:events.append((e.name,e.scroll_delta.y)),
                              on_hover=lambda e:events.append((e.name,e.global_position.x)))
    gesture.page=stub
    gesture._place(10,10,100,100,renderer.scale)
    gesture._pressed=True
    gesture._pressed_hook(20,20)
    gesture._drag_start(20,20)
    gesture._drag(30,22)
    gesture._drag_end()
    gesture._hover_move(30,22)
    gesture._wheel(40)
    assert [item[0] for item in events] == ["pan_start","pan_update","pan_end","hover","scroll"]
    assert events[1][1] == 10 and events[4][1] == 40
    assert gesture._consume_click
    body=st.Container(width=15,height=10,bgcolor="#ff0000")
    fab=st.FloatingActionButton(content=body,icon=st.Icons.ADD,
                                shape=st.RoundedRectangleBorder(radius=2),hover_elevation=8,
                                focus_elevation=10,disabled_elevation=0,clip_behavior=st.ClipBehavior.HARD_EDGE)
    render(renderer,fab,(0,0,100,56))
    assert pixel(renderer,round(body._rect[0])+7,28)[0] > 150


def check():
    pygame.init()
    window=pygame.Window("Visual parameter checks",size=(340,240),hidden=True)
    renderer=SoftwareRenderer(window,anti_aliasing=True)
    try:
        check_layout(renderer)
        check_buttons(renderer)
        check_images(renderer)
        check_list(renderer)
        check_decorations(renderer)
        check_gestures_and_fab(renderer)
        for name in ("Row","Column","Stack","ListView","Image","Card","IconButton","AlertDialog","SnackBar","ProgressBar","ProgressRing"):
            actual=inspect.signature(getattr(st,name)).parameters
            shared=inspect.signature(getattr(flet,name)).parameters
            assert any(key in actual for key in shared)
        print("VISUAL PARAMETER CHECKS PASS: wrapping, scrolling, state styles, image fits, prototypes, clipping, dialogs, progress pixels")
    finally:
        renderer.close()
        window.destroy()
        pygame.quit()


if __name__ == "__main__":
    check()
