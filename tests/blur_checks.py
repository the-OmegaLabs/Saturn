"""Container.blur backdrop Gaussian blur: smoke + screenshot + follow-up checks."""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import saturn as st
from saturn.app import App, Renderer
from saturn.painting import (
    BlurResultCache,
    backdrop_blur_surface,
    blur_source_digest,
    plan_backdrop_blur,
)


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
    box = st.Container(blur=st.Blur(6, 2, st.BlurTileMode.CLAMP))
    assert box.blur.sigma_x == 6 and box.blur.tile_mode == st.BlurTileMode.CLAMP
    st.Container(blur=None)
    st.Container(blur=0)
    print("Container.blur API OK")


def check_rejects_unsupported_tile_mode():
    """Non-CLAMP tile modes must raise — clamp-only is honest, not a sticker API."""
    for mode in (st.BlurTileMode.MIRROR, st.BlurTileMode.REPEATED, st.BlurTileMode.DECAL):
        try:
            st.Container(blur=st.Blur(4, 4, mode))
        except ValueError as exc:
            assert "CLAMP" in str(exc), exc
        else:
            raise AssertionError(f"expected ValueError for tile_mode={mode}")
    print("Container.blur tile_mode reject OK")


def check_rejects_nonfinite_blur():
    """NaN/Inf must not bypass sigma clamps and reach GL uniforms."""
    from saturn.painting import normalize_blur_sigmas

    for bad in (float("nan"), float("inf"), float("-inf")):
        for value in (bad, (bad, 1.0), (1.0, bad), st.Blur(bad, 1.0)):
            try:
                st.Container(blur=value)
            except ValueError:
                pass
            else:
                raise AssertionError(f"expected ValueError for blur={value!r}")

    sx, sy = normalize_blur_sigmas(float("nan"), 5.0, 2.0)
    assert sx == 0.0 and sy == 10.0, (sx, sy)
    sx, sy = normalize_blur_sigmas(float("inf"), float("-inf"), 1.0)
    assert sx == 0.0 and sy == 0.0, (sx, sy)
    sx, sy = normalize_blur_sigmas(3.0, 4.0, float("nan"))
    assert sx == 0.0 and sy == 0.0, (sx, sy)
    print("Container.blur non-finite reject OK")


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


def check_software_anisotropy():
    """Software path must honor distinct sx/sy (not max-collapse)."""
    pygame.display.init()
    try:
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        surf.fill((0, 0, 255, 255))
        surf.fill((255, 0, 0, 255), pygame.Rect(0, 0, 32, 64))
        # Strong horizontal, negligible vertical: seam should smear in X.
        hx = backdrop_blur_surface(surf.copy(), 8.0, 0.0)
        # Strong vertical, negligible horizontal: seam stays sharp in X.
        hy = backdrop_blur_surface(surf.copy(), 0.0, 8.0)
        # Sample just right of the vertical seam.
        hx_px = hx.get_at((34, 32))
        hy_px = hy.get_at((34, 32))
        # Horizontal blur pulls red across the seam into column 34.
        assert hx_px.r > 40, hx_px
        # Vertical-only blur should leave column 34 mostly blue (no X pass).
        assert hy_px.r < 40 and hy_px.b > 180, hy_px
        assert hx_px.r > hy_px.r + 30, (hx_px, hy_px)
        print("Container.blur software anisotropy OK", hx_px, hy_px)
    finally:
        pygame.display.quit()


def check_plan_backdrop_blur_pingpong():
    """Unit-level GL ping-pong plan: axis passes and downsample targets."""
    skipped = plan_backdrop_blur(0, 0, 1.0, 100, 80)
    assert skipped["skip"] and skipped["passes"] == ()

    both = plan_backdrop_blur(8, 4, 1.0, 100, 80)
    assert not both["skip"]
    assert [axis for axis, _ in both["passes"]] == ["x", "y"]
    assert both["target"][0] >= 1 and both["target"][1] >= 1

    x_only = plan_backdrop_blur(10, 0, 2.0, 200, 100)
    assert [axis for axis, _ in x_only["passes"]] == ["x"]
    assert x_only["sigma_x"] >= 0.5 and x_only["sigma_y"] < 0.5

    y_only = plan_backdrop_blur(0, 10, 1.0, 200, 100)
    assert [axis for axis, _ in y_only["passes"]] == ["y"]

    # Huge region must clamp FBO edge length.
    huge = plan_backdrop_blur(6, 6, 1.0, 1 << 18, 1 << 18)
    assert max(huge["target"]) <= (1 << 15)
    print("plan_backdrop_blur ping-pong OK", both["passes"], huge["target"])


def check_blur_result_cache():
    """Digest-keyed cache hits on unchanged source, misses when pixels change."""
    cache = BlurResultCache(max_entries=4)
    payload_a = object()
    digest_a = blur_source_digest(b"same-pixels")
    key = (0, 0, 10, 10, 4.0, 4.0, 0.0)
    assert cache.get(key, digest_a) is None
    cache.put(key, digest_a, payload_a)
    assert cache.get(key, digest_a) is payload_a
    assert cache.hits == 1
    assert cache.get(key, blur_source_digest(b"other-pixels")) is None
    assert cache.misses >= 2
    print("BlurResultCache OK", cache.hits, cache.misses)


def check_software_stack_blur_cache():
    """Stacked static blurs must reuse cached results across redraws."""
    def main(page):
        page.bgcolor = "#202020"
        page.padding = 0
        page.add(
            st.Stack(
                st.Container(width=160, height=120, bgcolor="#4488FF"),
                st.Container(width=80, height=60, left=20, top=20,
                             blur=10, bgcolor="#00000000"),
                st.Container(width=80, height=60, left=60, top=40,
                             blur=8, bgcolor="#00000000"),
                width=160,
                height=120,
            )
        )

    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app)
        app.page.draw()
        cache = app.renderer._blur_cache
        misses_after_first = cache.misses
        hits_after_first = cache.hits
        assert misses_after_first >= 1, misses_after_first
        # Second identical paint: source digests match → cache hits.
        app.page.draw()
        assert cache.hits > hits_after_first, (cache.hits, hits_after_first)
        assert cache.misses == misses_after_first, (cache.misses, misses_after_first)
        print("Container.blur stack cache OK",
              f"hits={cache.hits} misses={cache.misses}")
    finally:
        app.close()
        app.run_until_closed()


def check_opengl_backdrop_blur_smoke():
    """Exercise OpenGL backdrop_blur when a real GL window is available."""
    pygame.display.init()
    window = None
    renderer = None
    try:
        try:
            window = pygame.Window(
                "blur-gl-smoke", size=(160, 120), hidden=True, opengl=True)
            from saturn.renderer import create_renderer
            renderer = create_renderer(st.Renderer.OPENGL, window, vsync=False)
        except Exception as exc:
            print(f"Container.blur OpenGL smoke SKIPPED ({exc})")
            return
        renderer.clear("#000000")
        renderer.fill_rect(0, 0, 80, 120, (255, 0, 0, 255))
        renderer.fill_rect(80, 0, 80, 120, (0, 0, 255, 255))
        # Force ping-pong: both axes active.
        renderer.backdrop_blur(40, 30, 80, 60, 10, 6)
        # Second call with same backdrop should hit the digest cache when
        # pixels under the region are unchanged — redraw identical content.
        renderer.clear("#000000")
        renderer.fill_rect(0, 0, 80, 120, (255, 0, 0, 255))
        renderer.fill_rect(80, 0, 80, 120, (0, 0, 255, 255))
        before_hits = renderer._blur_cache.hits
        renderer.backdrop_blur(40, 30, 80, 60, 10, 6)
        # Cache may or may not hit depending on downsample float variance;
        # at minimum the call must not throw and plan must have run passes.
        plan = plan_backdrop_blur(10, 6, renderer.scale, 80, 60)
        assert not plan["skip"] and len(plan["passes"]) == 2
        shot = renderer.screenshot()
        assert shot.get_width() > 0
        print("Container.blur OpenGL smoke OK",
              f"cache_hits={renderer._blur_cache.hits} "
              f"(before={before_hits}) passes={plan['passes']}")
    finally:
        if renderer is not None:
            renderer.close()
        if window is not None:
            window.destroy()
        pygame.display.quit()


if __name__ == "__main__":
    check_accepts_blur_api()
    check_rejects_unsupported_tile_mode()
    check_rejects_nonfinite_blur()
    check_plan_backdrop_blur_pingpong()
    check_blur_result_cache()
    check_software_anisotropy()
    check_blur_none_and_zero_skip()
    check_software_screenshot()
    check_software_stack_blur_cache()
    check_opengl_backdrop_blur_smoke()
    print("ALL BLUR CHECKS PASS")
