"""Compare deterministic C++ animation samples with the actual Python controls."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from saturn.animation import ease
from saturn.control import Control
from saturn.widgets.inputs import Switch, Checkbox, Slider, TextField, Dropdown, Option
from saturn.widgets.scrolling import ListView
from saturn.widgets.containers import Container
from saturn.widgets.buttons import FilledButton
from saturn.widgets.dialogs import AlertDialog, SnackBar
from unittest.mock import MagicMock
import pygame

CURVES = ("linear", "materialStandard", "materialStandardAccelerate",
          "materialStandardDecelerate", "materialEmphasized",
          "materialEmphasizedAccelerate", "materialEmphasizedDecelerate",
          "materialSwitchOvershoot")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    args = parser.parse_args()
    data = json.loads(subprocess.check_output(
        [str(args.binary.resolve()), "--trace"], cwd=ROOT, text=True))
    for curve, t, actual in data["curves"]:
        expected = ease(CURVES[curve], t)
        if not math.isclose(actual, expected, abs_tol=1e-8):
            raise AssertionError((CURVES[curve], t, actual, expected))
    switch = Switch(value=False)
    with patch("time.perf_counter", return_value=10.0):
        switch.value = True
        switch._animate_value(True)
    for ms, x, radius, red, green, blue in data["switch"]:
        switch._tick_animations(10+ms/1000)
        expected_x = 16+20*switch._value_progress
        expected_radius = 8+4*switch._size_progress
        cp = switch._color_progress
        expected_color = tuple(round(a+(b-a)*cp) for a,b in
                               zip((54,52,59),(208,188,255)))
        if not math.isclose(x, expected_x, abs_tol=1e-5):
            raise AssertionError(("switch position", ms, x, expected_x))
        if not math.isclose(radius, expected_radius, abs_tol=1e-5):
            raise AssertionError(("switch radius", ms, radius, expected_radius))
        if (red, green, blue) != expected_color:
            raise AssertionError(("switch color", ms, (red,green,blue), expected_color))
    button = FilledButton("Filled")
    button._rect = (0,0,100,40)
    with patch("time.perf_counter", return_value=10.0):
        button._set_hover(True)
        button._pressed_hook(5,20)
    for ms, hover, press, x, y, radius in data["button"]:
        now = 10+ms/1000
        button._tick_animations(now)
        if ms == 200:
            with patch("time.perf_counter", return_value=now):
                button._released_hook(5,20)
        p = button._state_ripple_progress
        rx = 5+(50-5)*p
        ry = 20
        end = max(math.hypot(rx-px,ry-py) for px,py in
                  ((0,0),(100,0),(0,40),(100,40)))+10
        expected = (button._state_hover_alpha,button._state_press_alpha,
                    rx,ry,10+(end-10)*p)
        for actual, value in zip((hover,press,x,y,radius), expected):
            if not math.isclose(actual,value,abs_tol=2e-5):
                raise AssertionError(("button motion",ms,actual,value))
    dialog = AlertDialog(title="Confirm")
    snack = SnackBar("Saved!",action="Undo")
    with patch("time.perf_counter",return_value=10.0):
        dialog._shown()
        snack._shown()
    for ms,dy,card,content,actions,sy,sa in data["overlay"]:
        now = 10+ms/1000
        dialog._tick_animations(now); snack._tick_animations(now)
        if ms == 300:
            with patch("time.perf_counter",return_value=now), patch("threading.Timer",MagicMock()):
                dialog._begin_dismiss(None); snack._begin_dismiss(None)
        timeline = dialog._timeline
        dismissing = ms >= 300
        expected_content = (max(0,min(1,(timeline-1/3)/(2/3))) if dismissing
                            else max(0,min(1,(timeline-.1)/.4)))
        expected_actions = (expected_content if dismissing else max(0,min(1,(timeline-.3)/.3)))
        expected = (-50*(1-dialog._reveal), min(1,timeline*(3 if dismissing else 10)),
                    expected_content,expected_actions,(1-snack._reveal)*48,
                    min(1,snack._reveal*4))
        for actual,value in zip((dy,card,content,actions,sy,sa),expected):
            if not math.isclose(actual,value,abs_tol=2e-5):
                raise AssertionError(("overlay motion",ms,actual,value))
    def check(name,ms,actual,expected,tolerance=2e-5):
        for a,b in zip(actual,expected):
            if not math.isclose(a,b,abs_tol=tolerance):
                raise AssertionError((name,ms,a,b))
    checkbox = Checkbox()
    with patch("time.perf_counter",return_value=10.0):
        checkbox.value = True
        checkbox._animate_value(True)
    for ms,width,alpha,outline in data["checkbox"]:
        now = 10+ms/1000
        checkbox._tick_animations(now)
        if ms == 350:
            with patch("time.perf_counter",return_value=now):
                checkbox.value = False
                checkbox._animate_value(False)
        p = checkbox._value_progress
        check("checkbox",ms,(width,alpha,outline),
              (18*(.6+.4*p) if p > 0 else 0,round(255*min(1,p*3)) if p > 0 else 0,
               round(255*(1-p)) if p < 1 else 0),tolerance=.51)
    slider = Slider(min=0,max=100,divisions=10)
    slider._rect = (0,0,300,48)
    with patch("time.perf_counter",return_value=10.0):
        slider._pressed_hook(150,24)
        slider.value = 50
    for ms,width,alpha,radius in data["slider"]:
        now = 10+ms/1000
        slider._tick_animations(now)
        if ms == 150:
            with patch("time.perf_counter",return_value=now):
                slider._released_hook(150,24)
        p = slider._state_ripple_progress
        end = math.hypot(20,20)+10
        check("slider",ms,(width,alpha,radius),
              (4-2*slider._thumb_press_progress,slider._state_press_alpha,
               4+(end-4)*p if slider._state_press_alpha > 0 else 0))
    pygame.font.init()
    field = TextField(label="Name")
    with patch("time.perf_counter",return_value=10.0),patch("threading.Timer",MagicMock()):
        field._set_focused(True); field._set_hover(True)
    for ms,width,red,green,blue in data["field"]:
        now = 10+ms/1000
        field._tick_animations(now)
        if ms == 200:
            with patch("time.perf_counter",return_value=now):
                field._set_focused(False); field._set_hover(False)
        f,h = field._focus_progress,field._hover_progress
        inactive = tuple(round(a+(b-a)*.25*h) for a,b in zip((147,143,153),(230,224,233)))
        c = tuple(round(a+(b-a)*f) for a,b in zip(inactive,(208,188,255)))
        check("field",ms,(width,red,green,blue),(1+f,*c),tolerance=.51)
    menu = Dropdown(options=[Option("a",text="Alpha"),Option("b",text="Beta"),Option("g",text="Gamma")])
    with patch("time.perf_counter",return_value=10.0):
        menu._toggle_menu()
    for ms,height,alpha,*rows in data["menu"]:
        now = 10+ms/1000
        menu._tick_animations(now)
        if ms == 300:
            with patch("time.perf_counter",return_value=now):
                menu._close_menu()
        p,t = menu._menu_progress,menu._menu_timeline
        expected_rows = []
        for i in range(3):
            if i*48 > 144*p:
                expected_rows.append(0)
            elif ms >= 300:
                delay = 50+50*(2-i)/3
                expected_rows.append(1-max(0,min(1,((1-t)*150-delay)/50)))
            else:
                expected_rows.append(max(0,min(1,(t-.5*i/3)/.5)))
        check("menu",ms,(height,alpha,*rows),(144*p,min(1,t*(3 if ms >= 300 else 10)),*expected_rows))
    scroll = ListView(controls=[Container(height=30) for _ in range(30)],spacing=4,width=100,height=100)
    scroll._rect = (0,0,100,100); scroll._content_size = 1016
    with patch("time.perf_counter",return_value=10.0):
        scroll._show_scrollbar()
    for ms,width,alpha in data["scrollbar"]:
        now = 10+ms/1000
        scroll._tick_animations(now)
        with patch("time.perf_counter",return_value=now):
            if ms == 200: scroll._set_hover(True)
            if ms == 400: scroll._set_hover(False)
        check("scrollbar",ms,(width,alpha),
              (scroll._scrollbar_thickness,round(255*scroll._scrollbar_opacity)),tolerance=.51)
    for curve in range(8):
        control = Control()
        control._reveal = 0.0
        control._animate_internal("_reveal",1,300,CURVES[curve],now=10)
        for index,ms,actual in (row for row in data["interruption"] if row[0] == curve):
            now = 10+ms/1000
            control._tick_animations(now)
            if ms == 90: control._animate_internal("_reveal",0,150,CURVES[curve],now=now)
            if ms == 150: control._animate_internal("_reveal",1,300,CURVES[curve],now=now)
            check("interruption",ms,(actual,),(control._reveal,))
    print(f"PASS: {len(data['curves'])} easing samples and "
          f"{len(data['switch'])} Switch, {len(data['button'])} button, "
          f"{len(data['overlay'])} Dialog/SnackBar samples match Python; "
          f"Checkbox/Slider/field/menu/scrollbar: "
          f"{sum(len(data[k]) for k in ('checkbox','slider','field','menu','scrollbar'))} samples; "
          f"interrupted/reversed animations: {len(data['interruption'])} samples")

if __name__ == "__main__":
    main()
