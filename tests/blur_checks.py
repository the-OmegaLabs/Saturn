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
    normalize_blur_radius,
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
    """Only CLAMP exists on the enum; unknown / Flet sticker names must raise."""
    for name in ("MIRROR", "REPEATED", "DECAL"):
        assert not hasattr(st.BlurTileMode, name), name
    for raw in ("mirror", "repeated", "decal", "Mirror"):
        try:
            st.Container(blur=st.Blur(4, 4, raw))
        except ValueError as exc:
            assert "CLAMP" in str(exc), exc
        else:
            raise AssertionError(f"expected ValueError for tile_mode={raw!r}")
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


def check_convolve_axis_vectorized():
    """Convolve must match the tap-loop reference; large buffers use FFT."""
    import time
    import numpy as np
    from saturn.painting import _convolve_axis, _gaussian_kernel_1d

    def reference(img, sigma, axis):
        if sigma < 0.5:
            return img
        radius, ker = _gaussian_kernel_1d(sigma)
        pad_width = [(0, 0), (0, 0), (0, 0)]
        pad_width[axis] = (radius, radius)
        padded = np.pad(img, pad_width, mode="edge")
        out = np.zeros_like(img)
        height, width = img.shape[:2]
        if axis == 1:
            for offset, weight in enumerate(ker):
                out += padded[:, offset:offset + width, :] * weight
        else:
            for offset, weight in enumerate(ker):
                out += padded[offset:offset + height, :, :] * weight
        return out

    rng = np.random.default_rng(0)
    for shape in ((48, 64, 4), (240, 320, 4)):
        img = rng.integers(0, 255, shape, dtype=np.uint8).astype(np.float32)
        for axis in (0, 1):
            for sigma in (0.25, 2.0, 8.0, 12.0):
                got = _convolve_axis(img, sigma, axis)
                exp = reference(img, sigma, axis)
                max_diff = float(np.max(np.abs(got - exp)))
                assert max_diff < 1e-3, (shape, axis, sigma, max_diff)
    # Large-buffer path (FFT) should not regress past the tap loop.
    big = rng.integers(0, 255, (360, 480, 4), dtype=np.uint8).astype(np.float32)
    t0 = time.perf_counter()
    for _ in range(4):
        reference(big, 10.0, 1)
        reference(big, 10.0, 0)
    ref_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    for _ in range(4):
        _convolve_axis(big, 10.0, 1)
        _convolve_axis(big, 10.0, 0)
    vec_s = time.perf_counter() - t0
    assert vec_s < ref_s * 1.5 + 0.05, (vec_s, ref_s)
    print("Container.blur convolve vectorized OK",
          f"max_checked_diff<1e-3 vec={vec_s:.4f}s ref={ref_s:.4f}s")


def check_software_anisotropy():
    """Software path must run true H-then-V separable (not scale+isotropic)."""
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

        # Horizontal seam: red on top half, blue on bottom — Y-only should smear.
        both = pygame.Surface((64, 64), pygame.SRCALPHA)
        both.fill((0, 0, 255, 255))
        both.fill((255, 0, 0, 255), pygame.Rect(0, 0, 64, 32))
        vy = backdrop_blur_surface(both.copy(), 0.0, 8.0)
        vx = backdrop_blur_surface(both.copy(), 8.0, 0.0)
        vy_px = vy.get_at((32, 34))
        vx_px = vx.get_at((32, 34))
        assert vy_px.r > 40, vy_px
        assert vx_px.r < 40 and vx_px.b > 180, vx_px
        assert vy_px.r > vx_px.r + 30, (vy_px, vx_px)
        print("Container.blur software anisotropy OK", hx_px, hy_px, vy_px)
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
    # Forced hit/miss without GL: second get with same digest hits again.
    assert cache.get(key, digest_a) is payload_a
    assert cache.hits == 2
    print("BlurResultCache OK", cache.hits, cache.misses)


def check_blur_source_digest_detects_sparse_change():
    """Full-buffer digest must not false-hit when only a skipped byte changes.

    The old stepped sampler (every len//1024 bytes) missed odd offsets on a
    4096-byte buffer (step=4). Full blake2b must distinguish them.
    """
    raw_a = bytearray(4096)
    raw_b = bytearray(4096)
    raw_b[1] = 1  # offset that step=4 sampling previously skipped
    assert blur_source_digest(bytes(raw_a)) != blur_source_digest(bytes(raw_b))
    # Geometry is part of the fingerprint.
    assert (blur_source_digest(b"abcd", width=2, height=2)
            != blur_source_digest(b"abcd", width=4, height=1))
    print("blur_source_digest sparse-change OK")


def check_normalize_blur_radius():
    """Non-finite compose radius must zero out like sigmas."""
    assert normalize_blur_radius(4) == 4.0
    assert normalize_blur_radius(0) == 0.0
    assert normalize_blur_radius(-1) == 0.0
    for bad in (float("nan"), float("inf"), float("-inf")):
        assert normalize_blur_radius(bad) == 0.0, bad
    assert normalize_blur_radius((float("nan"), 3, -2)) == (0.0, 3.0, 0.0)
    print("normalize_blur_radius OK")


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
        before_misses = renderer._blur_cache.misses
        renderer.backdrop_blur(40, 30, 80, 60, 10, 6)
        plan = plan_backdrop_blur(10, 6, renderer.scale, 80, 60)
        assert not plan["skip"] and len(plan["passes"]) == 2
        # Identical redraw must hit the digest cache (no new miss).
        assert renderer._blur_cache.hits > before_hits, (
            renderer._blur_cache.hits, before_hits)
        assert renderer._blur_cache.misses == before_misses, (
            renderer._blur_cache.misses, before_misses)
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
    check_normalize_blur_radius()
    check_plan_backdrop_blur_pingpong()
    check_blur_result_cache()
    check_blur_source_digest_detects_sparse_change()
    check_convolve_axis_vectorized()
    check_software_anisotropy()
    check_blur_none_and_zero_skip()
    check_software_screenshot()
    check_software_stack_blur_cache()
    check_opengl_backdrop_blur_smoke()
    print("ALL BLUR CHECKS PASS")
