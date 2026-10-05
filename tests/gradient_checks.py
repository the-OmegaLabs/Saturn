"""Container gradient decoration: radial (flet-compatible) and linear."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saturn as st
from saturn import colors
from saturn.app import App, Renderer

BG = (25, 48, 71)  # #193047
GOLD = (255, 215, 0)


def pump(app, predicate=lambda: True, timeout=5.0):
    import time
    deadline = time.perf_counter() + timeout
    while True:
        app._pump_once()
        if predicate():
            return
        assert time.perf_counter() < deadline, "window operation timed out"
        time.sleep(0.01)


def blend(base, top, alpha):
    return tuple(round(b*(1-alpha) + t*alpha) for b, t in zip(base, top))


def check_radial():
    def main(page):
        page.bgcolor = "#193047"
        page.add(st.Container(width=200, height=120, gradient=st.RadialGradient(
            colors=[st.Colors.with_opacity(0.15, "#FFD700"), st.Colors.TRANSPARENT])))
    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app)
        app.page.draw()
        shot = app.renderer.screenshot()
        bx, by, bw, bh = app.page.controls[0]._rect
        alpha = round(0.15*255)/255
        expect_center = blend(BG, GOLD, alpha)
        center = shot.get_at((round(bx+bw/2), round(by+bh/2)))[:3]
        corner = shot.get_at((bx+2, by+2))[:3]
        assert all(abs(c-e) <= 2 for c, e in zip(center, expect_center)), \
            (center, expect_center)
        assert corner == BG, (corner, BG)
        print("RadialGradient draw OK")
    finally:
        app.close()
        app.run_until_closed()


def check_linear():
    def main(page):
        page.bgcolor = "#193047"
        page.add(st.Container(width=120, height=60, gradient=st.LinearGradient(
            colors=["#FF0000", "#0000FF"], begin=st.Alignment.CENTER_LEFT,
            end=st.Alignment.CENTER_RIGHT)))
    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app)
        app.page.draw()
        shot = app.renderer.screenshot()
        bx, by, bw, bh = app.page.controls[0]._rect
        left = shot.get_at((bx+2, round(by+bh/2)))[:3]
        right = shot.get_at((bx+bw-3, round(by+bh/2)))[:3]
        assert all(abs(c-e) <= 10 for c, e in zip(left, (255, 0, 0))), left
        assert all(abs(c-e) <= 10 for c, e in zip(right, (0, 0, 255))), right
        print("LinearGradient draw OK")
    finally:
        app.close()
        app.run_until_closed()


if __name__ == "__main__":
    check_radial()
    check_linear()
    print("ALL GRADIENT CHECKS PASS")
