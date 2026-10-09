"""Container.blur backdrop Gaussian blur: smoke + screenshot checks."""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import saturn as st
from saturn.app import App, Renderer


def pump(app, timeout=5.0):
    deadline = time.perf_counter() + timeout
    while True:
        app._pump_once()
        if app.page is not None and app.renderer is not None:
            return
        assert time.perf_counter() < deadline, "window operation timed out"
        time.sleep(0.01)


def check_accepts_blur_api():
    box = st.Container(width=40, height=40, blur=10, bgcolor="#88FFFFFF")
    assert box.blur.sigma_x == 10 and box.blur.sigma_y == 10
    box = st.Container(blur=(4, 8))
    assert box.blur.sigma_x == 4 and box.blur.sigma_y == 8
    box = st.Container(blur=st.Blur(6, 2, st.BlurTileMode.MIRROR))
    assert box.blur.sigma_x == 6 and box.blur.tile_mode == st.BlurTileMode.MIRROR
    st.Container(blur=None)
    st.Container(blur=0)
    print("Container.blur API OK")


def check_software_screenshot():
    def main(page):
        page.bgcolor = "#000000"
        page.padding = 0
        page.add(
            st.Stack(
                st.Row(
                    st.Container(width=80, height=120, bgcolor="#FF0000"),
                    st.Container(width=80, height=120, bgcolor="#0000FF"),
                    spacing=0,
                ),
                st.Container(
                    width=60,
                    height=60,
                    left=50,
                    top=30,
                    blur=12,
                    bgcolor="#00000000",
                ),
                width=160,
                height=120,
            )
        )

    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app)
        app.page.draw()
        shot = app.renderer.screenshot()
        # Center of the blur overlay sits on the red/blue seam and must mix.
        cx, cy = 80, 60
        mixed = shot.get_at((cx, cy))[:3]
        assert mixed[0] > 40 and mixed[2] > 40, mixed
        assert abs(mixed[0] - mixed[2]) < 80, mixed
        # Far left stays pure red, far right pure blue.
        left = shot.get_at((10, 60))[:3]
        right = shot.get_at((150, 60))[:3]
        assert left[0] > 200 and left[2] < 40, left
        assert right[2] > 200 and right[0] < 40, right
        print("Container.blur software screenshot OK", mixed)
    finally:
        app.close()
        app.run_until_closed()


def check_blur_none_and_zero_skip():
    def main(page):
        page.bgcolor = "#112233"
        page.add(st.Container(width=40, height=40, blur=0, bgcolor="#FF0000"))
        page.add(st.Container(width=40, height=40, bgcolor="#00FF00"))

    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app)
        app.page.draw()
        shot = app.renderer.screenshot()
        assert shot.get_width() > 0
        print("Container.blur zero/None smoke OK")
    finally:
        app.close()
        app.run_until_closed()


if __name__ == "__main__":
    check_accepts_blur_api()
    check_blur_none_and_zero_skip()
    check_software_screenshot()
    print("ALL BLUR CHECKS PASS")
